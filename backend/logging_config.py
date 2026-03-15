#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细日志配置模块
提供结构化、分级别的日志记录功能
"""

import os
import logging
import logging.handlers
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class JSONFormatter(logging.Formatter):
    """JSON格式化器，用于结构化日志"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "ip_address"):
            log_entry["ip_address"] = record.ip_address
        if hasattr(record, "execution_time"):
            log_entry["execution_time"] = record.execution_time

        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """控制台彩色格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",  # 重置
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # 格式化消息
        formatted = super().format(record)
        return f"{log_color}{formatted}{reset}"


def setup_logging(app=None, env="development"):
    """
    设置完整的日志配置

    Args:
        app: Flask应用实例
        env: 环境类型 ('development' 或 'production')
    """
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if env == "production" else logging.DEBUG)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 1. 控制台处理器（带颜色）
    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # 2. 应用主日志文件（按大小轮转）
    app_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding="utf-8",
    )
    app_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    app_handler.setFormatter(app_formatter)
    app_handler.setLevel(logging.INFO)
    root_logger.addHandler(app_handler)

    # 3. 错误日志文件（按时间轮转）
    error_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "error.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.addFilter(lambda record: record.levelno >= logging.ERROR)
    error_handler.setFormatter(app_formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

    # 4. JSON结构化日志（用于日志分析）
    json_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "structured.log"),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=7,
        encoding="utf-8",
    )
    json_handler.setFormatter(JSONFormatter())
    json_handler.setLevel(logging.INFO)
    root_logger.addHandler(json_handler)

    # 5. 访问日志（专门记录API访问）
    access_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "access.log"),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=7,
        encoding="utf-8",
    )
    access_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    access_handler.setFormatter(access_formatter)
    access_handler.setLevel(logging.INFO)

    # 创建专门的访问日志器
    access_logger = logging.getLogger("access")
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False  # 不传播到根日志器

    # 6. 安全日志（记录认证、授权等安全事件）
    security_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "security.log"),
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=30,
        encoding="utf-8",
    )
    security_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    security_handler.setFormatter(security_formatter)
    security_handler.setLevel(logging.INFO)

    # 创建专门的安全日志器
    security_logger = logging.getLogger("security")
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False

    # 7. 性能日志（记录API响应时间等）
    performance_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "performance.log"),
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=7,
        encoding="utf-8",
    )
    performance_formatter = logging.Formatter("%(asctime)s - %(message)s")
    performance_handler.setFormatter(performance_formatter)
    performance_handler.setLevel(logging.INFO)

    # 创建专门的性能日志器
    performance_logger = logging.getLogger("performance")
    performance_logger.addHandler(performance_handler)
    performance_logger.setLevel(logging.INFO)
    performance_logger.propagate = False

    # 8. 第三方库日志级别控制
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("oss2").setLevel(logging.WARNING)

    # 如果是Flask应用，配置应用日志
    if app:
        app.logger.setLevel(logging.INFO if env == "production" else logging.DEBUG)

        # 生产环境额外配置
        if env == "production":
            # 禁用调试模式
            app.debug = False

            # 配置错误邮件通知（如果配置了SMTP）
            if app.config.get("MAIL_SERVER"):
                from logging.handlers import SMTPHandler

                secure = None
                if app.config.get("MAIL_USE_TLS"):
                    secure = ()
                mail_handler = SMTPHandler(
                    mailhost=(
                        app.config["MAIL_SERVER"],
                        app.config.get("MAIL_PORT", 587),
                    ),
                    fromaddr=app.config.get("MAIL_FROM"),
                    toaddrs=app.config.get("ADMINS", []),
                    subject="发型迁移系统错误报告",
                    credentials=app.config.get("MAIL_CREDENTIALS"),
                    secure=secure,
                )
                mail_handler.setLevel(logging.ERROR)
                app.logger.addHandler(mail_handler)

    print(f"✅ 日志系统已配置 (环境: {env})")
    print(f"   📁 日志目录: {os.path.abspath(log_dir)}")
    print(
        f"   📊 日志文件: app.log, error.log, access.log, security.log, performance.log, structured.log"
    )


class RequestLogger:
    """请求日志记录器"""

    def __init__(self, app=None):
        self.app = app
        self.access_logger = logging.getLogger("access")
        self.performance_logger = logging.getLogger("performance")

        if app:
            self.init_app(app)

    def init_app(self, app):
        """初始化Flask应用的请求日志"""

        @app.before_request
        def before_request():
            import time
            import uuid

            g.start_time = time.time()
            g.request_id = str(uuid.uuid4())[:8]

            # 记录请求开始
            self.access_logger.info(
                f"Request started: {request.method} {request.path} "
                f"- ID: {g.request_id} - IP: {request.remote_addr}"
            )

        @app.after_request
        def after_request(response):
            import time

            if hasattr(g, "start_time"):
                execution_time = round((time.time() - g.start_time) * 1000, 2)  # 毫秒

                # 记录访问日志
                self.access_logger.info(
                    f"Request completed: {request.method} {request.path} "
                    f"- Status: {response.status_code} "
                    f"- Time: {execution_time}ms "
                    f"- ID: {g.request_id} "
                    f"- IP: {request.remote_addr} "
                    f"- Size: {len(response.get_data())} bytes"
                )

                # 记录性能日志（超过100ms的请求）
                if execution_time > 100:
                    self.performance_logger.warning(
                        f"Slow request: {request.method} {request.path} "
                        f"- Time: {execution_time}ms "
                        f"- ID: {g.request_id} "
                        f"- IP: {request.remote_addr}"
                    )

                # 记录错误响应
                if response.status_code >= 400:
                    self.access_logger.error(
                        f"Error response: {request.method} {request.path} "
                        f"- Status: {response.status_code} "
                        f"- ID: {g.request_id} "
                        f"- IP: {request.remote_addr}"
                    )

            return response

        @app.errorhandler(Exception)
        def handle_exception(e):
            import traceback

            request_id = getattr(g, "request_id", "unknown")

            # 记录未捕获的异常
            app.logger.error(
                f"Unhandled exception: {str(e)} "
                f"- Request: {request.method} {request.path} "
                f"- ID: {request_id} "
                f"- IP: {request.remote_addr}",
                exc_info=True,
            )

            return {"error": "Internal server error"}, 500


def log_security_event(event_type, details, user_id=None, ip_address=None):
    """记录安全事件"""
    security_logger = logging.getLogger("security")

    message = f"Security event: {event_type} - {details}"
    if user_id:
        message += f" - User: {user_id}"
    if ip_address:
        message += f" - IP: {ip_address}"

    if event_type in ["LOGIN_FAILED", "UNAUTHORIZED_ACCESS", "SUSPICIOUS_ACTIVITY"]:
        security_logger.warning(message)
    else:
        security_logger.info(message)


def log_performance(operation, duration, details=None):
    """记录性能指标"""
    performance_logger = logging.getLogger("performance")

    message = f"Operation: {operation} - Duration: {duration:.2f}ms"
    if details:
        message += f" - Details: {details}"

    if duration > 1000:  # 超过1秒
        performance_logger.error(message)
    elif duration > 500:  # 超过500ms
        performance_logger.warning(message)
    else:
        performance_logger.info(message)
