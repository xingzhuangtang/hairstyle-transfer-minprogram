#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份自动化配置脚本
设置定时任务、监控告警和备份策略
"""

import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/hairstyle_backup_setup.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class BackupAutomation:
    """备份自动化管理器"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backup_dir = Path("/opt/backups/mysql")
        self.log_dir = Path("/var/log")

        # 确保目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def install_cron_jobs(self) -> bool:
        """安装定时任务"""
        try:
            # 当前脚本路径
            backup_script = str(self.project_root / "db_backup.py")

            # 定时任务配置
            cron_jobs = [
                # 每日凌晨2点执行数据库备份
                f"0 2 * * * /usr/bin/python3 {backup_script} --create >> /var/log/hairstyle_db_backup.log 2>&1",
                # 每周日凌晨3点执行完整备份验证
                f"0 3 * * 0 /usr/bin/python3 {backup_script} --list >> /var/log/hairstyle_backup_check.log 2>&1",
                # 每小时检查备份状态
                f"0 * * * * /usr/bin/python3 {self.project_root}/monitor_backup.py >> /var/log/hairstyle_backup_monitor.log 2>&1",
                # 每天凌晨4点清理过期备份
                f"0 4 * * * /usr/bin/python3 {backup_script} --cleanup 30 >> /var/log/hairstyle_backup_cleanup.log 2>&1",
            ]

            # 创建临时cron文件
            temp_cron = "/tmp/hairstyle_backup_cron"
            with open(temp_cron, "w") as f:
                # 添加头部注释
                f.write("# Hairstyle Transfer App Backup Automation\n")
                f.write(
                    f"# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )

                # 添加任务
                for job in cron_jobs:
                    f.write(f"{job}\n")

            # 安装cron任务
            try:
                # 获取当前用户的crontab
                result = subprocess.run(
                    ["crontab", "-l"], capture_output=True, text=True
                )
                existing_cron = result.stdout if result.returncode == 0 else ""

                # 检查是否已存在我们的任务
                if "hairstyle_backup_cron" in existing_cron:
                    logger.info("检测到现有备份任务，将进行更新")

                # 合并新的cron任务
                with open(temp_cron, "r") as f:
                    new_jobs = f.read()

                # 移除旧的备份任务
                lines = existing_cron.split("\n")
                filtered_lines = [
                    line
                    for line in lines
                    if not any(
                        keyword in line for keyword in ["hairstyle", "db_backup.py"]
                    )
                ]

                # 写入新的crontab
                final_cron = "\n".join(filtered_lines) + "\n" + new_jobs

                with open(temp_cron, "w") as f:
                    f.write(final_cron)

                # 安装新的crontab
                result = subprocess.run(
                    ["crontab", temp_cron], capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise Exception(f"安装crontab失败: {result.stderr}")

                logger.info("定时任务安装成功")

                # 清理临时文件
                os.unlink(temp_cron)

                return True

            except Exception as e:
                logger.error(f"安装定时任务失败: {str(e)}")
                if os.path.exists(temp_cron):
                    os.unlink(temp_cron)
                return False

        except Exception as e:
            logger.error(f"配置定时任务失败: {str(e)}")
            return False

    def create_backup_monitor(self) -> bool:
        """创建备份监控脚本"""
        try:
            monitor_script = self.project_root / "monitor_backup.py"

            script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份监控脚本
检查备份状态、磁盘空间和系统健康
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from db_backup import DatabaseBackup
from config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/hairstyle_backup_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackupMonitor:
    """备份监控器"""
    
    def __init__(self):
        self.backup_manager = DatabaseBackup()
        self.config = get_config()
        
        # 监控阈值
        self.disk_space_threshold = 20  # 剩余空间百分比
        self.backup_age_threshold = 48   # 最旧备份年龄（小时）
    
    def check_disk_space(self) -> bool:
        """检查磁盘空间"""
        try:
            total, used, free = shutil.disk_usage(self.backup_manager.backup_dir)
            free_percent = (free / total) * 100
            
            logger.info(f"磁盘空间检查: {free/1024/1024/1024:.1f}GB 可用 ({free_percent:.1f}%)")
            
            if free_percent < self.disk_space_threshold:
                logger.warning(f"磁盘空间不足: {free_percent:.1f}% 可用")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查磁盘空间失败: {str(e)}")
            return False
    
    def check_backup_status(self) -> bool:
        """检查备份状态"""
        try:
            backups = self.backup_manager.get_backup_list()
            
            if not backups:
                logger.error("没有找到任何备份文件")
                return False
            
            # 检查最新备份时间
            latest_backup = backups[0]
            backup_age = datetime.now() - latest_backup['created']
            
            if backup_age > timedelta(hours=self.backup_age_threshold):
                logger.warning(f"最新备份过期: {backup_age.total_seconds()/3600:.1f} 小时前")
                return False
            
            logger.info(f"备份状态正常: 最新备份 {backup_age.total_seconds()/3600:.1f} 小时前")
            
            # 验证最新备份
            latest_backup_path = Path(latest_backup['path'])
            if self.backup_manager.verify_backup(latest_backup_path):
                logger.info("最新备份验证成功")
                return True
            else:
                logger.error("最新备份验证失败")
                return False
                
        except Exception as e:
            logger.error(f"检查备份状态失败: {str(e)}")
            return False
    
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=self.config.MYSQL_HOST,
                port=self.config.MYSQL_PORT,
                user=self.config.MYSQL_USER,
                password=self.config.MYSQL_PASSWORD,
                database=self.config.MYSQL_DATABASE,
                connect_timeout=10
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            connection.close()
            
            if result and result[0] == 1:
                logger.info("数据库连接正常")
                return True
            else:
                logger.error("数据库连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return False
    
    def run_health_check(self) -> bool:
        """运行健康检查"""
        logger.info("开始系统健康检查")
        
        checks = [
            ("磁盘空间", self.check_disk_space),
            ("备份状态", self.check_backup_status),
            ("数据库连接", self.check_database_connection)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                if check_func():
                    logger.info(f"✓ {check_name} 检查通过")
                else:
                    logger.error(f"✗ {check_name} 检查失败")
                    all_passed = False
            except Exception as e:
                logger.error(f"✗ {check_name} 检查出错: {str(e)}")
                all_passed = False
        
        if all_passed:
            logger.info("所有健康检查通过")
        else:
            logger.error("健康检查发现问题")
        
        return all_passed

def main():
    """主函数"""
    monitor = BackupMonitor()
    
    # 运行健康检查
    monitor.run_health_check()

if __name__ == "__main__":
    main()
'''

            with open(monitor_script, "w", encoding="utf-8") as f:
                f.write(script_content)

            # 设置执行权限
            os.chmod(monitor_script, 0o755)

            logger.info(f"备份监控脚本创建成功: {monitor_script}")
            return True

        except Exception as e:
            logger.error(f"创建备份监控脚本失败: {str(e)}")
            return False

    def setup_log_rotation(self) -> bool:
        """配置日志轮转"""
        try:
            logrotate_config = """# Hairstyle Transfer App Log Rotation
/var/log/hairstyle_*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        # 重启相关服务（如果需要）
        systemctl reload rsyslog >/dev/null 2>&1 || true
    endscript
}

/opt/backups/mysql/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
}
"""

            config_path = "/etc/logrotate.d/hairstyle-transfer"

            with open(config_path, "w") as f:
                f.write(logrotate_config)

            logger.info(f"日志轮转配置创建成功: {config_path}")
            return True

        except Exception as e:
            logger.error(f"配置日志轮转失败: {str(e)}")
            return False

    def create_backup_dirs(self) -> bool:
        """创建备份相关目录"""
        try:
            dirs_to_create = [
                "/opt/backups/mysql",
                "/opt/backups/mysql/archive",
                "/var/log/backup",
                "/etc/hairstyle-transfer",
            ]

            for dir_path in dirs_to_create:
                path = Path(dir_path)
                path.mkdir(parents=True, exist_ok=True)
                os.chmod(path, 0o755)
                logger.info(f"目录创建成功: {dir_path}")

            return True

        except Exception as e:
            logger.error(f"创建备份目录失败: {str(e)}")
            return False

    def install_dependencies(self) -> bool:
        """安装必要的依赖包"""
        try:
            # 检查并安装Python包
            required_packages = ["cryptography", "pymysql", "psutil"]

            for package in required_packages:
                try:
                    __import__(package)
                    logger.info(f"包 {package} 已安装")
                except ImportError:
                    logger.info(f"安装包: {package}")
                    subprocess.run(["pip3", "install", package], check=True)

            return True

        except Exception as e:
            logger.error(f"安装依赖包失败: {str(e)}")
            return False


def main():
    """主函数"""
    automation = BackupAutomation()

    logger.info("开始配置备份自动化系统")

    tasks = [
        ("创建备份目录", automation.create_backup_dirs),
        ("安装依赖包", automation.install_dependencies),
        ("创建备份监控脚本", automation.create_backup_monitor),
        ("配置日志轮转", automation.setup_log_rotation),
        ("安装定时任务", automation.install_cron_jobs),
    ]

    success_count = 0

    for task_name, task_func in tasks:
        logger.info(f"执行任务: {task_name}")
        try:
            if task_func():
                logger.info(f"✓ {task_name} 完成")
                success_count += 1
            else:
                logger.error(f"✗ {task_name} 失败")
        except Exception as e:
            logger.error(f"✗ {task_name} 出错: {str(e)}")

    total_tasks = len(tasks)
    logger.info(f"配置完成: {success_count}/{total_tasks} 个任务成功")

    if success_count == total_tasks:
        logger.info("备份自动化系统配置成功！")
        print("\n🎉 备份自动化系统配置完成！")
        print("\n已配置以下功能：")
        print("- 每日凌晨2点自动数据库备份")
        print("- 每小时备份状态监控")
        print("- 每周备份验证")
        print("- 磁盘空间监控")
        print("- 自动日志轮转")
        print("\n日志位置：")
        print("- /var/log/hairstyle_db_backup.log")
        print("- /var/log/hairstyle_backup_monitor.log")
    else:
        logger.error("备份自动化系统配置失败！")


if __name__ == "__main__":
    main()
