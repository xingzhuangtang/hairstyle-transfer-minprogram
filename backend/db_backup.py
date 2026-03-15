#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库备份脚本
支持自动备份、压缩、加密和保留策略
"""

import os
import sys
import subprocess
import datetime
import logging
import tarfile
import gzip
import json
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional, List
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# 导入配置
from config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/hairstyle_db_backup.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """数据库备份管理器"""

    def __init__(self):
        self.config = get_config()
        self.backup_dir = Path("/opt/backups/mysql")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 加密密钥（应该从环境变量获取）
        self.encryption_key = os.getenv("BACKUP_ENCRYPTION_KEY")
        if self.encryption_key:
            self.cipher = Fernet(self.encryption_key.encode())

        # 邮件通知配置
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")

    def create_backup(self) -> Optional[Path]:
        """创建数据库备份"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"hairstyle_transfer_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename

            # 构建mysqldump命令
            mysqldump_cmd = [
                "mysqldump",
                "--single-transaction",
                "--routines",
                "--triggers",
                "--all-databases" if self.config.MYSQL_DATABASE == "all" else "",
                f"--host={self.config.MYSQL_HOST}",
                f"--port={self.config.MYSQL_PORT}",
                f"--user={self.config.MYSQL_USER}",
                f"--password={self.config.MYSQL_PASSWORD}",
            ]

            if self.config.MYSQL_DATABASE != "all":
                mysqldump_cmd.append(self.config.MYSQL_DATABASE)

            # 移除空参数
            mysqldump_cmd = [arg for arg in mysqldump_cmd if arg]

            logger.info(f"开始创建数据库备份: {backup_filename}")

            # 执行备份
            with open(backup_path, "w") as f:
                process = subprocess.run(
                    mysqldump_cmd, stdout=f, stderr=subprocess.PIPE, text=True
                )

                if process.returncode != 0:
                    raise Exception(f"mysqldump失败: {process.stderr}")

            logger.info(f"数据库备份完成: {backup_path}")

            # 压缩和加密
            return self._compress_and_encrypt(backup_path)

        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            self._send_notification(f"数据库备份失败: {str(e)}", is_error=True)
            return None

    def _compress_and_encrypt(self, backup_path: Path) -> Path:
        """压缩和加密备份文件"""
        try:
            # 压缩
            compressed_path = backup_path.with_suffix(".sql.gz")
            with open(backup_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    f_out.writelines(f_in)

            # 删除原始文件
            backup_path.unlink()

            # 加密（如果配置了密钥）
            if self.encryption_key and hasattr(self, "cipher"):
                encrypted_path = compressed_path.with_suffix(".gz.enc")
                with open(compressed_path, "rb") as f_in:
                    encrypted_data = self.cipher.encrypt(f_in.read())

                with open(encrypted_path, "wb") as f_out:
                    f_out.write(encrypted_data)

                # 删除压缩文件
                compressed_path.unlink()
                final_path = encrypted_path
                logger.info(f"备份文件已压缩和加密: {final_path}")
            else:
                final_path = compressed_path
                logger.info(f"备份文件已压缩: {final_path}")

            return final_path

        except Exception as e:
            logger.error(f"压缩和加密失败: {str(e)}")
            raise

    def cleanup_old_backups(self, retain_days: int = 30):
        """清理过期备份文件"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retain_days)
            deleted_count = 0

            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file():
                    file_time = datetime.datetime.fromtimestamp(
                        backup_file.stat().st_mtime
                    )
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.info(f"删除过期备份: {backup_file}")

            logger.info(f"清理完成，删除 {deleted_count} 个过期备份文件")

        except Exception as e:
            logger.error(f"清理备份失败: {str(e)}")

    def verify_backup(self, backup_path: Path) -> bool:
        """验证备份文件完整性"""
        try:
            if backup_path.suffix == ".enc":
                # 解密并验证
                if not hasattr(self, "cipher"):
                    logger.error("无法验证加密文件：缺少解密密钥")
                    return False

                with open(backup_path, "rb") as f:
                    encrypted_data = f.read()

                # 尝试解密
                decrypted_data = self.cipher.decrypt(encrypted_data)

                # 验证是否为有效的gzip文件
                import io

                try:
                    with gzip.open(io.BytesIO(decrypted_data), "rb") as f:
                        # 读取前几行验证
                        lines = [f.readline() for _ in range(5)]
                        if any(
                            b"INSERT" in line or b"CREATE" in line for line in lines
                        ):
                            logger.info(f"备份文件验证成功: {backup_path}")
                            return True
                except:
                    pass

            elif backup_path.suffix == ".gz":
                # 验证压缩文件
                try:
                    with gzip.open(backup_path, "rb") as f:
                        lines = [f.readline() for _ in range(5)]
                        if any(
                            b"INSERT" in line or b"CREATE" in line for line in lines
                        ):
                            logger.info(f"备份文件验证成功: {backup_path}")
                            return True
                except:
                    pass

            logger.error(f"备份文件验证失败: {backup_path}")
            return False

        except Exception as e:
            logger.error(f"验证备份失败: {str(e)}")
            return False

    def _send_notification(self, message: str, is_error: bool = False):
        """发送通知邮件"""
        try:
            if not self.smtp_user or not self.smtp_password or not self.admin_emails:
                return

            subject = "数据库备份错误" if is_error else "数据库备份通知"

            msg = MimeMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(filter(None, self.admin_emails))
            msg["Subject"] = subject

            body = f"""
            时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            主机: {os.uname().nodename}
            消息: {message}
            """

            msg.attach(MimeText(body, "plain", "utf-8"))

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

            logger.info("通知邮件发送成功")

        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}")

    def get_backup_list(self) -> List[dict]:
        """获取备份文件列表"""
        backups = []
        for backup_file in self.backup_dir.glob("*"):
            if backup_file.is_file():
                stat = backup_file.stat()
                backups.append(
                    {
                        "name": backup_file.name,
                        "path": str(backup_file),
                        "size": stat.st_size,
                        "created": datetime.datetime.fromtimestamp(stat.st_ctime),
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime),
                    }
                )

        return sorted(backups, key=lambda x: x["created"], reverse=True)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库备份工具")
    parser.add_argument("--create", action="store_true", help="创建备份")
    parser.add_argument(
        "--cleanup", type=int, default=30, help="清理超过指定天数的备份"
    )
    parser.add_argument("--verify", type=str, help="验证指定备份文件")
    parser.add_argument("--list", action="store_true", help="列出所有备份文件")

    args = parser.parse_args()

    backup_manager = DatabaseBackup()

    try:
        if args.create:
            backup_path = backup_manager.create_backup()
            if backup_path:
                # 验证备份
                if backup_manager.verify_backup(backup_path):
                    logger.info("备份创建并验证成功")
                    # 清理旧备份
                    backup_manager.cleanup_old_backups(args.cleanup)
                else:
                    logger.error("备份验证失败")
                    sys.exit(1)
            else:
                logger.error("备份创建失败")
                sys.exit(1)

        elif args.verify:
            backup_path = Path(args.verify)
            if backup_manager.verify_backup(backup_path):
                logger.info("备份验证成功")
            else:
                logger.error("备份验证失败")
                sys.exit(1)

        elif args.list:
            backups = backup_manager.get_backup_list()
            print(f"{'文件名':<40} {'大小':<10} {'创建时间':<20}")
            print("-" * 70)
            for backup in backups:
                size_str = f"{backup['size'] / 1024 / 1024:.1f}MB"
                created_str = backup["created"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"{backup['name']:<40} {size_str:<10} {created_str:<20}")

        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.info("备份过程被中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"备份过程出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
