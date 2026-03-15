#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库恢复脚本
支持从加密/压缩备份文件恢复数据库
"""

import os
import sys
import subprocess
import logging
import gzip
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional
import datetime

# 导入配置
from config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/hairstyle_db_restore.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class DatabaseRestore:
    """数据库恢复管理器"""

    def __init__(self):
        self.config = get_config()
        self.backup_dir = Path("/opt/backups/mysql")

        # 加密密钥
        self.encryption_key = os.getenv("BACKUP_ENCRYPTION_KEY")
        if self.encryption_key:
            self.cipher = Fernet(self.encryption_key.encode())

    def list_backups(self):
        """列出所有可用的备份文件"""
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
                        "type": "encrypted"
                        if backup_file.suffix == ".enc"
                        else "compressed",
                    }
                )

        return sorted(backups, key=lambda x: x["created"], reverse=True)

    def restore_from_backup(
        self, backup_path: str, target_database: Optional[str] = None
    ) -> bool:
        """从备份文件恢复数据库"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"备份文件不存在: {backup_path}")
                return False

            # 如果未指定目标数据库，使用配置中的数据库
            target_db = target_database or self.config.MYSQL_DATABASE

            logger.info(f"开始从备份恢复数据库: {backup_path} -> {target_db}")

            # 解密和解压缩备份文件
            sql_content = self._decrypt_and_decompress(backup_file)
            if sql_content is None:
                return False

            # 创建临时文件
            temp_sql_file = (
                self.backup_dir
                / f"temp_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            )
            with open(temp_sql_file, "w", encoding="utf-8") as f:
                f.write(sql_content)

            try:
                # 删除现有数据库（如果不是系统数据库）
                if target_db not in [
                    "information_schema",
                    "performance_schema",
                    "mysql",
                    "sys",
                ]:
                    drop_cmd = [
                        "mysql",
                        f"--host={self.config.MYSQL_HOST}",
                        f"--port={self.config.MYSQL_PORT}",
                        f"--user={self.config.MYSQL_USER}",
                        f"--password={self.config.MYSQL_PASSWORD}",
                        "-e",
                        f"DROP DATABASE IF EXISTS `{target_db}`",
                    ]

                    result = subprocess.run(drop_cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.warning(f"删除数据库警告: {result.stderr}")

                # 创建新数据库
                create_cmd = [
                    "mysql",
                    f"--host={self.config.MYSQL_HOST}",
                    f"--port={self.config.MYSQL_PORT}",
                    f"--user={self.config.MYSQL_USER}",
                    f"--password={self.config.MYSQL_PASSWORD}",
                    "-e",
                    f"CREATE DATABASE `{target_db}`",
                ]

                result = subprocess.run(create_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"创建数据库失败: {result.stderr}")
                    return False

                # 导入数据
                import_cmd = [
                    "mysql",
                    f"--host={self.config.MYSQL_HOST}",
                    f"--port={self.config.MYSQL_PORT}",
                    f"--user={self.config.MYSQL_USER}",
                    f"--password={self.config.MYSQL_PASSWORD}",
                    target_db,
                ]

                logger.info(f"正在导入数据到数据库: {target_db}")

                with open(temp_sql_file, "r", encoding="utf-8") as f:
                    process = subprocess.run(
                        import_cmd, stdin=f, capture_output=True, text=True
                    )

                    if process.returncode != 0:
                        logger.error(f"导入数据失败: {process.stderr}")
                        return False

                logger.info(f"数据库恢复成功: {target_db}")
                return True

            finally:
                # 清理临时文件
                if temp_sql_file.exists():
                    temp_sql_file.unlink()

        except Exception as e:
            logger.error(f"数据库恢复失败: {str(e)}")
            return False

    def _decrypt_and_decompress(self, backup_file: Path) -> Optional[str]:
        """解密和解压缩备份文件"""
        try:
            if backup_file.suffix == ".enc":
                # 加密文件
                if not hasattr(self, "cipher"):
                    logger.error("无法解密文件：缺少解密密钥")
                    return None

                with open(backup_file, "rb") as f:
                    encrypted_data = f.read()

                decrypted_data = self.cipher.decrypt(encrypted_data)

                # 解压缩
                import io

                with gzip.open(io.BytesIO(decrypted_data), "rt", encoding="utf-8") as f:
                    return f.read()

            elif backup_file.suffix == ".gz":
                # 仅压缩文件
                with gzip.open(backup_file, "rt", encoding="utf-8") as f:
                    return f.read()

            elif backup_file.suffix == ".sql":
                # 原始SQL文件
                with open(backup_file, "r", encoding="utf-8") as f:
                    return f.read()

            else:
                logger.error(f"不支持的备份文件格式: {backup_file.suffix}")
                return None

        except Exception as e:
            logger.error(f"解密/解压缩失败: {str(e)}")
            return None

    def backup_current_database(
        self, backup_name: Optional[str] = None
    ) -> Optional[str]:
        """在恢复前备份当前数据库"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"pre_restore_backup_{timestamp}"
            backup_path = self.backup_dir / f"{backup_name}.sql"

            # 构建mysqldump命令
            mysqldump_cmd = [
                "mysqldump",
                "--single-transaction",
                "--routines",
                "--triggers",
                f"--host={self.config.MYSQL_HOST}",
                f"--port={self.config.MYSQL_PORT}",
                f"--user={self.config.MYSQL_USER}",
                f"--password={self.config.MYSQL_PASSWORD}",
                self.config.MYSQL_DATABASE,
            ]

            logger.info(f"创建当前数据库备份: {backup_path}")

            with open(backup_path, "w", encoding="utf-8") as f:
                process = subprocess.run(
                    mysqldump_cmd, stdout=f, stderr=subprocess.PIPE, text=True
                )

                if process.returncode != 0:
                    raise Exception(f"mysqldump失败: {process.stderr}")

            logger.info(f"当前数据库备份完成: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"备份当前数据库失败: {str(e)}")
            return None


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库恢复工具")
    parser.add_argument("--list", action="store_true", help="列出所有可用备份")
    parser.add_argument("--restore", type=str, help="从指定备份文件恢复")
    parser.add_argument("--target-db", type=str, help="目标数据库名称")
    parser.add_argument(
        "--backup-current", action="store_true", help="恢复前备份当前数据库"
    )
    parser.add_argument("--verify", type=str, help="验证指定备份文件")

    args = parser.parse_args()

    restore_manager = DatabaseRestore()

    try:
        if args.list:
            backups = restore_manager.list_backups()
            print(f"{'文件名':<50} {'大小':<10} {'类型':<10} {'创建时间':<20}")
            print("-" * 90)
            for backup in backups:
                size_str = f"{backup['size'] / 1024 / 1024:.1f}MB"
                created_str = backup["created"].strftime("%Y-%m-%d %H:%M:%S")
                print(
                    f"{backup['name']:<50} {size_str:<10} {backup['type']:<10} {created_str:<20}"
                )

        elif args.restore:
            backup_path = args.restore
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                sys.exit(1)

            # 可选：恢复前备份当前数据库
            if args.backup_current:
                pre_backup = restore_manager.backup_current_database()
                if pre_backup:
                    logger.info(f"已创建恢复前备份: {pre_backup}")
                else:
                    logger.warning("创建恢复前备份失败，但继续恢复过程")

            # 执行恢复
            if restore_manager.restore_from_backup(backup_path, args.target_db):
                logger.info("数据库恢复成功")
            else:
                logger.error("数据库恢复失败")
                sys.exit(1)

        elif args.verify:
            backup_path = args.verify
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                sys.exit(1)

            # 尝试解密和解压缩以验证文件
            backup_file = Path(backup_path)
            sql_content = restore_manager._decrypt_and_decompress(backup_file)

            if sql_content:
                # 简单验证内容
                if "CREATE TABLE" in sql_content or "INSERT INTO" in sql_content:
                    file_size = os.path.getsize(backup_path) / 1024 / 1024
                    logger.info(f"备份文件验证成功，大小: {file_size:.1f}MB")
                else:
                    logger.error("备份文件内容验证失败")
                    sys.exit(1)
            else:
                logger.error("备份文件验证失败")
                sys.exit(1)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.info("恢复过程被中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"恢复过程出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
