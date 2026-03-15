#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控脚本
监控系统资源、应用性能和业务指标
"""

import os
import sys
import time
import json
import logging
import psutil
import requests
import pymysql
import redis
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import deque

# 导入配置
from config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/hairstyle_system_monitor.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """告警配置"""

    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    disk_threshold: float = 20.0
    response_time_threshold: float = 5.0
    error_rate_threshold: float = 5.0
    redis_memory_threshold: float = 90.0


class SystemMonitor:
    """系统监控器"""

    def __init__(self):
        self.config = get_config()
        self.alert_config = AlertConfig()

        # 监控数据缓存
        self.response_times = deque(maxlen=100)  # 最近100次响应时间
        self.error_count = 0
        self.total_requests = 0
        self.last_check = datetime.now()

        # 告警历史（避免重复告警）
        self.alert_history = deque(maxlen=1000)

        # 数据库连接
        self.db_connection = None

        # Redis连接
        self.redis_client = None

    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_per_core = psutil.cpu_percent(percpu=True)

            # 内存使用情况
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # 磁盘使用情况
            disk = psutil.disk_usage("/")
            disk_partitions = psutil.disk_partitions()

            # 网络IO
            network = psutil.net_io_counters()

            # 进程信息
            process = psutil.Process()
            process_memory = process.memory_info()

            # 系统负载
            load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "per_core": cpu_per_core,
                    "count": psutil.cpu_count(),
                    "load_avg": list(load_avg),
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
                "process": {
                    "pid": process.pid,
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent(),
                },
            }

            # 添加多个分区信息
            partitions_info = []
            for partition in disk_partitions:
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    partitions_info.append(
                        {
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype,
                            "total": partition_usage.total,
                            "used": partition_usage.used,
                            "free": partition_usage.free,
                            "percent": (partition_usage.used / partition_usage.total)
                            * 100,
                        }
                    )
                except PermissionError:
                    continue

            metrics["disk_partitions"] = partitions_info

            return metrics

        except Exception as e:
            logger.error(f"获取系统指标失败: {str(e)}")
            return {}

    def get_database_metrics(self) -> Dict[str, Any]:
        """获取数据库指标"""
        try:
            if not self.db_connection:
                self.db_connection = pymysql.connect(
                    host=self.config.MYSQL_HOST,
                    port=self.config.MYSQL_PORT,
                    user=self.config.MYSQL_USER,
                    password=self.config.MYSQL_PASSWORD,
                    database=self.config.MYSQL_DATABASE,
                    connect_timeout=5,
                )

            with self.db_connection.cursor() as cursor:
                # 数据库连接数
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                threads_connected = cursor.fetchone()[1]

                # 数据库大小
                cursor.execute(
                    f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS 'DB Size in MB' FROM information_schema.tables WHERE table_schema='{self.config.MYSQL_DATABASE}'"
                )
                db_size = cursor.fetchone()[0]

                # 慢查询数量
                cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries'")
                slow_queries = cursor.fetchone()[1]

                # 查询缓存命中率
                cursor.execute("SHOW GLOBAL STATUS LIKE 'Qcache_hits'")
                qcache_hits = cursor.fetchone()[1] if cursor.fetchone() else 0

                cursor.execute("SHOW GLOBAL STATUS LIKE 'Com_select'")
                com_select = cursor.fetchone()[1] if cursor.fetchone() else 1

                qcache_hit_rate = (
                    (qcache_hits / com_select * 100) if com_select > 0 else 0
                )

                # 表锁等待
                cursor.execute("SHOW GLOBAL STATUS LIKE 'Table_locks_waited'")
                table_locks_waited = cursor.fetchone()[1]

                return {
                    "timestamp": datetime.now().isoformat(),
                    "threads_connected": int(threads_connected),
                    "database_size_mb": float(db_size),
                    "slow_queries": int(slow_queries),
                    "query_cache_hit_rate": qcache_hit_rate,
                    "table_locks_waited": int(table_locks_waited),
                }

        except Exception as e:
            logger.error(f"获取数据库指标失败: {str(e)}")
            return {"error": str(e)}

    def get_redis_metrics(self) -> Dict[str, Any]:
        """获取Redis指标"""
        try:
            if not self.redis_client:
                self.redis_client = redis.Redis(
                    host=self.config.REDIS_HOST,
                    port=self.config.REDIS_PORT,
                    db=self.config.REDIS_DB,
                    password=self.config.REDIS_PASSWORD or None,
                    decode_responses=True,
                    socket_timeout=5,
                )

            info = self.redis_client.info()

            return {
                "timestamp": datetime.now().isoformat(),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_rss": info.get("used_memory_rss", 0),
                "maxmemory": info.get("maxmemory", 0),
                "memory_usage_percent": (
                    info.get("used_memory", 0) / info.get("maxmemory", 1)
                )
                * 100
                if info.get("maxmemory", 0) > 0
                else 0,
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                )
                * 100,
            }

        except Exception as e:
            logger.error(f"获取Redis指标失败: {str(e)}")
            return {"error": str(e)}

    def get_application_metrics(self) -> Dict[str, Any]:
        """获取应用指标"""
        try:
            # 这里应该连接应用API获取指标，现在模拟一些数据
            # 实际实现中，可以从Flask应用获取请求数据

            # 计算平均响应时间
            avg_response_time = (
                sum(self.response_times) / len(self.response_times)
                if self.response_times
                else 0
            )

            # 计算错误率
            error_rate = (
                (self.error_count / self.total_requests * 100)
                if self.total_requests > 0
                else 0
            )

            # 检查应用健康状态
            health_status = self._check_app_health()

            return {
                "timestamp": datetime.now().isoformat(),
                "avg_response_time": avg_response_time,
                "total_requests": self.total_requests,
                "error_count": self.error_count,
                "error_rate": error_rate,
                "health_status": health_status,
                "uptime": time.time() - psutil.boot_time(),
            }

        except Exception as e:
            logger.error(f"获取应用指标失败: {str(e)}")
            return {"error": str(e)}

    def _check_app_health(self) -> str:
        """检查应用健康状态"""
        try:
            # 尝试连接应用健康检查端点
            app_url = f"http://{self.config.SERVER_HOST}/api/health"
            response = requests.get(app_url, timeout=5)

            if response.status_code == 200:
                return "healthy"
            else:
                return f"unhealthy_{response.status_code}"

        except requests.exceptions.Timeout:
            return "timeout"
        except requests.exceptions.ConnectionError:
            return "connection_error"
        except Exception as e:
            return f"error_{str(e)[:50]}"

    def get_business_metrics(self) -> Dict[str, Any]:
        """获取业务指标"""
        try:
            if not self.db_connection:
                self.db_connection = pymysql.connect(
                    host=self.config.MYSQL_HOST,
                    port=self.config.MYSQL_PORT,
                    user=self.config.MYSQL_USER,
                    password=self.config.MYSQL_PASSWORD,
                    database=self.config.MYSQL_DATABASE,
                    connect_timeout=5,
                )

            with self.db_connection.cursor() as cursor:
                metrics = {}

                # 用户统计
                cursor.execute("SELECT COUNT(*) FROM user")
                total_users = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM user WHERE member_level = 'premium'"
                )
                premium_users = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM user WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                )
                new_users_today = cursor.fetchone()[0]

                # 消费统计
                cursor.execute(
                    "SELECT COUNT(*) FROM consumption_record WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                )
                consumptions_today = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT SUM(amount) FROM consumption_record WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                )
                total_consumption_today = cursor.fetchone()[0] or 0

                # 支付统计
                cursor.execute(
                    "SELECT COUNT(*) FROM recharge_record WHERE status = 'completed' AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                )
                payments_today = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT SUM(amount) FROM recharge_record WHERE status = 'completed' AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                )
                total_revenue_today = cursor.fetchone()[0] or 0

                # 会员统计
                cursor.execute(
                    "SELECT COUNT(*) FROM member_order WHERE status = 'completed' AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                )
                new_memberships_today = cursor.fetchone()[0]

                metrics.update(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "users": {
                            "total": total_users,
                            "premium": premium_users,
                            "new_today": new_users_today,
                        },
                        "consumption": {
                            "count_today": consumptions_today,
                            "amount_today": total_consumption_today,
                        },
                        "payments": {
                            "count_today": payments_today,
                            "revenue_today": total_revenue_today,
                        },
                        "memberships": {"new_today": new_memberships_today},
                    }
                )

                return metrics

        except Exception as e:
            logger.error(f"获取业务指标失败: {str(e)}")
            return {"error": str(e)}

    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查告警条件"""
        alerts = []
        current_time = datetime.now()

        try:
            # 系统资源告警
            system_metrics = metrics.get("system", {})

            # CPU告警
            cpu_percent = system_metrics.get("cpu", {}).get("percent", 0)
            if cpu_percent > self.alert_config.cpu_threshold:
                alert = {
                    "timestamp": current_time.isoformat(),
                    "type": "system",
                    "metric": "cpu",
                    "severity": "warning",
                    "message": f"CPU使用率过高: {cpu_percent:.1f}%",
                    "value": cpu_percent,
                    "threshold": self.alert_config.cpu_threshold,
                }
                alerts.append(alert)

            # 内存告警
            memory_percent = system_metrics.get("memory", {}).get("percent", 0)
            if memory_percent > self.alert_config.memory_threshold:
                alert = {
                    "timestamp": current_time.isoformat(),
                    "type": "system",
                    "metric": "memory",
                    "severity": "warning",
                    "message": f"内存使用率过高: {memory_percent:.1f}%",
                    "value": memory_percent,
                    "threshold": self.alert_config.memory_threshold,
                }
                alerts.append(alert)

            # 磁盘告警
            disk_percent = system_metrics.get("disk", {}).get("percent", 0)
            if disk_percent > (100 - self.alert_config.disk_threshold):
                alert = {
                    "timestamp": current_time.isoformat(),
                    "type": "system",
                    "metric": "disk",
                    "severity": "critical",
                    "message": f"磁盘空间不足: {disk_percent:.1f}% 使用",
                    "value": disk_percent,
                    "threshold": 100 - self.alert_config.disk_threshold,
                }
                alerts.append(alert)

            # 应用性能告警
            app_metrics = metrics.get("application", {})

            response_time = app_metrics.get("avg_response_time", 0)
            if response_time > self.alert_config.response_time_threshold:
                alert = {
                    "timestamp": current_time.isoformat(),
                    "type": "application",
                    "metric": "response_time",
                    "severity": "warning",
                    "message": f"响应时间过长: {response_time:.2f}秒",
                    "value": response_time,
                    "threshold": self.alert_config.response_time_threshold,
                }
                alerts.append(alert)

            error_rate = app_metrics.get("error_rate", 0)
            if error_rate > self.alert_config.error_rate_threshold:
                alert = {
                    "timestamp": current_time.isoformat(),
                    "type": "application",
                    "metric": "error_rate",
                    "severity": "critical",
                    "message": f"错误率过高: {error_rate:.1f}%",
                    "value": error_rate,
                    "threshold": self.alert_config.error_rate_threshold,
                }
                alerts.append(alert)

            # 数据库告警
            db_metrics = metrics.get("database", {})
            if "error" not in db_metrics:
                threads_connected = db_metrics.get("threads_connected", 0)
                if threads_connected > 100:  # 简单阈值
                    alert = {
                        "timestamp": current_time.isoformat(),
                        "type": "database",
                        "metric": "connections",
                        "severity": "warning",
                        "message": f"数据库连接数过多: {threads_connected}",
                        "value": threads_connected,
                        "threshold": 100,
                    }
                    alerts.append(alert)

            # Redis告警
            redis_metrics = metrics.get("redis", {})
            if "error" not in redis_metrics:
                memory_usage = redis_metrics.get("memory_usage_percent", 0)
                if memory_usage > self.alert_config.redis_memory_threshold:
                    alert = {
                        "timestamp": current_time.isoformat(),
                        "type": "redis",
                        "metric": "memory",
                        "severity": "warning",
                        "message": f"Redis内存使用率过高: {memory_usage:.1f}%",
                        "value": memory_usage,
                        "threshold": self.alert_config.redis_memory_threshold,
                    }
                    alerts.append(alert)

            # 过滤重复告警（最近1小时内相同类型不重复发送）
            filtered_alerts = []
            for alert in alerts:
                alert_key = f"{alert['type']}_{alert['metric']}"

                # 检查是否有相同的最近告警
                recent_similar = [
                    h
                    for h in self.alert_history
                    if h["type"] == alert["type"]
                    and h["metric"] == alert["metric"]
                    and (current_time - datetime.fromisoformat(h["timestamp"])).seconds
                    < 3600
                ]

                if not recent_similar:
                    filtered_alerts.append(alert)
                    self.alert_history.append(alert)

            return filtered_alerts

        except Exception as e:
            logger.error(f"检查告警失败: {str(e)}")
            return []

    def collect_all_metrics(self) -> Dict[str, Any]:
        """收集所有指标"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": self.get_system_metrics(),
            "database": self.get_database_metrics(),
            "redis": self.get_redis_metrics(),
            "application": self.get_application_metrics(),
            "business": self.get_business_metrics(),
        }

        return metrics

    def send_alerts(self, alerts: List[Dict[str, Any]]) -> bool:
        """发送告警"""
        if not alerts:
            return True

        try:
            # 这里应该实现实际的告警发送逻辑
            # 可以是邮件、短信、微信等

            for alert in alerts:
                logger.warning(f"告警: {alert['message']}")

                # 这里可以调用具体的告警发送方法
                # self.send_email_alert(alert)
                # self.send_sms_alert(alert)
                # self.send_wechat_alert(alert)

            return True

        except Exception as e:
            logger.error(f"发送告警失败: {str(e)}")
            return False

    def run_monitoring_cycle(self) -> bool:
        """运行一个监控周期"""
        try:
            logger.info("开始监控周期")

            # 收集所有指标
            metrics = self.collect_all_metrics()

            # 保存指标到文件
            self._save_metrics(metrics)

            # 检查告警
            alerts = self.check_alerts(metrics)

            # 发送告警
            if alerts:
                self.send_alerts(alerts)

            logger.info("监控周期完成")
            return True

        except Exception as e:
            logger.error(f"监控周期失败: {str(e)}")
            return False

    def _save_metrics(self, metrics: Dict[str, Any]):
        """保存指标到文件"""
        try:
            metrics_dir = Path("/var/log/hairstyle-metrics")
            metrics_dir.mkdir(exist_ok=True)

            # 按日期保存指标
            date_str = datetime.now().strftime("%Y-%m-%d")
            metrics_file = metrics_dir / f"metrics_{date_str}.json"

            # 读取现有指标
            existing_metrics = []
            if metrics_file.exists():
                try:
                    with open(metrics_file, "r", encoding="utf-8") as f:
                        existing_metrics = json.load(f)
                except json.JSONDecodeError:
                    existing_metrics = []

            # 添加新指标
            existing_metrics.append(metrics)

            # 保留最近1000条记录
            if len(existing_metrics) > 1000:
                existing_metrics = existing_metrics[-1000:]

            # 写入文件
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(existing_metrics, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存指标失败: {str(e)}")


def main():
    """主函数"""
    monitor = SystemMonitor()

    # 运行监控
    success = monitor.run_monitoring_cycle()

    if success:
        logger.info("监控执行成功")
        sys.exit(0)
    else:
        logger.error("监控执行失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
