#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控配置模块
提供系统监控、健康检查、性能指标收集功能
"""

import os
import time
import psutil
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, g
from functools import wraps
import logging


class SystemMonitor:
    """系统监控器"""

    def __init__(self, app=None):
        self.app = app
        self.metrics = {}
        self.alerts = []
        self.monitoring_thread = None
        self.monitoring_active = False

        if app:
            self.init_app(app)

    def init_app(self, app):
        """初始化Flask应用的监控"""
        self.app = app

        # 启动监控线程
        self.start_monitoring()

        # 注册监控端点
        self.register_endpoints()

    def start_monitoring(self):
        """启动后台监控线程"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitoring_thread.start()
            print("✅ 系统监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("⏹️ 系统监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                self._collect_metrics()
                self._check_alerts()
                time.sleep(30)  # 每30秒收集一次指标
            except Exception as e:
                logging.error(f"监控循环错误: {e}")
                time.sleep(60)

    def _collect_metrics(self):
        """收集系统指标"""
        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # 内存指标
            memory = psutil.virtual_memory()

            # 磁盘指标
            disk = psutil.disk_usage("/")

            # 网络指标
            network = psutil.net_io_counters()

            # 进程指标
            process = psutil.Process()
            process_memory = process.memory_info()

            # 存储指标
            self.metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency": cpu_freq.current if cpu_freq else None,
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
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
                    "num_threads": process.num_threads(),
                    "create_time": process.create_time(),
                },
            }

        except Exception as e:
            logging.error(f"收集系统指标失败: {e}")

    def _check_alerts(self):
        """检查告警条件"""
        if not self.metrics:
            return

        alerts = []

        # CPU告警
        if self.metrics["cpu"]["percent"] > 80:
            alerts.append(
                {
                    "type": "cpu_high",
                    "message": f"CPU使用率过高: {self.metrics['cpu']['percent']:.1f}%",
                    "level": "warning"
                    if self.metrics["cpu"]["percent"] < 90
                    else "critical",
                }
            )

        # 内存告警
        if self.metrics["memory"]["percent"] > 85:
            alerts.append(
                {
                    "type": "memory_high",
                    "message": f"内存使用率过高: {self.metrics['memory']['percent']:.1f}%",
                    "level": "warning"
                    if self.metrics["memory"]["percent"] < 95
                    else "critical",
                }
            )

        # 磁盘告警
        if self.metrics["disk"]["percent"] > 90:
            alerts.append(
                {
                    "type": "disk_high",
                    "message": f"磁盘使用率过高: {self.metrics['disk']['percent']:.1f}%",
                    "level": "warning"
                    if self.metrics["disk"]["percent"] < 95
                    else "critical",
                }
            )

        # 更新告警列表
        if alerts:
            self.alerts.extend(alerts)
            # 只保留最近100条告警
            self.alerts = self.alerts[-100:]

            # 记录告警日志
            for alert in alerts:
                if alert["level"] == "critical":
                    logging.critical(f"系统告警: {alert['message']}")
                else:
                    logging.warning(f"系统告警: {alert['message']}")

    def register_endpoints(self):
        """注册监控端点"""

        @self.app.route("/api/monitoring/metrics")
        def get_metrics():
            """获取系统指标"""
            return jsonify(
                {
                    "status": "ok",
                    "metrics": self.metrics,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        @self.app.route("/api/monitoring/health")
        def detailed_health():
            """详细健康检查"""
            health_status = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "checks": {},
            }

            # 检查系统资源
            if self.metrics:
                health_status["checks"]["system"] = {
                    "cpu": "ok" if self.metrics["cpu"]["percent"] < 80 else "warning",
                    "memory": "ok"
                    if self.metrics["memory"]["percent"] < 85
                    else "warning",
                    "disk": "ok" if self.metrics["disk"]["percent"] < 90 else "warning",
                }

            # 检查数据库连接
            try:
                from models import db

                db.session.execute("SELECT 1")
                health_status["checks"]["database"] = "ok"
            except Exception as e:
                health_status["checks"]["database"] = f"error: {str(e)}"
                health_status["status"] = "error"

            # 检查Redis连接
            try:
                import redis
                from config import get_config

                config = get_config()
                r = redis.Redis(
                    host=config.REDIS_HOST,
                    port=config.REDIS_PORT,
                    password=config.REDIS_PASSWORD,
                    socket_timeout=5,
                )
                r.ping()
                health_status["checks"]["redis"] = "ok"
            except Exception as e:
                health_status["checks"]["redis"] = f"error: {str(e)}"
                health_status["status"] = "error"

            # 检查阿里云服务
            try:
                access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
                access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
                if access_key_id and access_key_secret:
                    health_status["checks"]["aliyun"] = "ok"
                else:
                    health_status["checks"]["aliyun"] = "missing_credentials"
                    health_status["status"] = "warning"
            except Exception as e:
                health_status["checks"]["aliyun"] = f"error: {str(e)}"
                health_status["status"] = "error"

            return jsonify(health_status)

        @self.app.route("/api/monitoring/alerts")
        def get_alerts():
            """获取告警信息"""
            return jsonify(
                {
                    "status": "ok",
                    "alerts": self.alerts[-20:],  # 返回最近20条告警
                    "total": len(self.alerts),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        @self.app.route("/api/monitoring/status")
        def monitoring_status():
            """监控状态"""
            return jsonify(
                {
                    "status": "ok",
                    "monitoring_active": self.monitoring_active,
                    "last_update": self.metrics.get("timestamp")
                    if self.metrics
                    else None,
                    "thread_alive": self.monitoring_thread.is_alive()
                    if self.monitoring_thread
                    else False,
                }
            )


def monitor_performance(func):
    """性能监控装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # 毫秒

            # 记录性能日志
            performance_logger = logging.getLogger("performance")

            log_data = {
                "function": func.__name__,
                "duration_ms": round(duration, 2),
                "success": success,
                "request_id": getattr(g, "request_id", None),
                "user_id": getattr(g, "user_id", None),
            }

            if error:
                log_data["error"] = error

            if duration > 1000:  # 超过1秒
                performance_logger.error(f"Slow function: {log_data}")
            elif duration > 500:  # 超过500ms
                performance_logger.warning(f"Moderate function: {log_data}")
            else:
                performance_logger.info(f"Function performance: {log_data}")

        return result

    return wrapper


class HealthChecker:
    """健康检查器"""

    def __init__(self, app=None):
        self.app = app
        self.checks = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """初始化健康检查"""
        self.app = app
        self.register_default_checks()

    def register_default_checks(self):
        """注册默认检查项"""

        # 数据库检查
        self.add_check("database", self._check_database)

        # Redis检查
        self.add_check("redis", self._check_redis)

        # 阿里云服务检查
        self.add_check("aliyun", self._check_aliyun)

        # 磁盘空间检查
        self.add_check("disk_space", self._check_disk_space)

    def add_check(self, name, check_func):
        """添加检查项"""
        self.checks[name] = check_func

    def run_checks(self):
        """运行所有检查"""
        results = {}
        overall_status = "ok"

        for name, check_func in self.checks.items():
            try:
                result = check_func()
                results[name] = {
                    "status": result.get("status", "ok"),
                    "message": result.get("message", ""),
                    "details": result.get("details", {}),
                    "timestamp": datetime.now().isoformat(),
                }

                if result.get("status") == "error":
                    overall_status = "error"
                elif result.get("status") == "warning" and overall_status == "ok":
                    overall_status = "warning"

            except Exception as e:
                results[name] = {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
                overall_status = "error"

        return {
            "overall_status": overall_status,
            "checks": results,
            "timestamp": datetime.now().isoformat(),
        }

    def _check_database(self):
        """检查数据库连接"""
        try:
            from models import db

            start_time = time.time()
            db.session.execute("SELECT 1")
            duration = (time.time() - start_time) * 1000

            return {
                "status": "ok" if duration < 1000 else "warning",
                "message": f"数据库响应正常 ({duration:.2f}ms)",
                "details": {"response_time_ms": duration},
            }
        except Exception as e:
            return {"status": "error", "message": f"数据库连接失败: {str(e)}"}

    def _check_redis(self):
        """检查Redis连接"""
        try:
            import redis
            from config import get_config

            config = get_config()

            start_time = time.time()
            r = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD,
                socket_timeout=5,
            )
            r.ping()
            duration = (time.time() - start_time) * 1000

            return {
                "status": "ok" if duration < 500 else "warning",
                "message": f"Redis响应正常 ({duration:.2f}ms)",
                "details": {"response_time_ms": duration},
            }
        except Exception as e:
            return {"status": "error", "message": f"Redis连接失败: {str(e)}"}

    def _check_aliyun(self):
        """检查阿里云服务"""
        try:
            access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
            access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

            if not access_key_id or not access_key_secret:
                return {"status": "warning", "message": "阿里云凭证未配置"}

            # 简单检查凭证格式
            if len(access_key_id) < 16 or len(access_key_secret) < 16:
                return {"status": "warning", "message": "阿里云凭证格式可能不正确"}

            return {"status": "ok", "message": "阿里云凭证已配置"}
        except Exception as e:
            return {"status": "error", "message": f"阿里云服务检查失败: {str(e)}"}

    def _check_disk_space(self):
        """检查磁盘空间"""
        try:
            disk = psutil.disk_usage("/")
            percent_used = (disk.used / disk.total) * 100

            if percent_used > 95:
                status = "error"
            elif percent_used > 90:
                status = "warning"
            else:
                status = "ok"

            return {
                "status": status,
                "message": f"磁盘使用率 {percent_used:.1f}%",
                "details": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": percent_used,
                },
            }
        except Exception as e:
            return {"status": "error", "message": f"磁盘空间检查失败: {str(e)}"}


# 全局监控实例
system_monitor = None
health_checker = None


def init_monitoring(app):
    """初始化监控系统"""
    global system_monitor, health_checker

    system_monitor = SystemMonitor(app)
    health_checker = HealthChecker(app)

    print("✅ 监控系统初始化完成")
    return system_monitor, health_checker
