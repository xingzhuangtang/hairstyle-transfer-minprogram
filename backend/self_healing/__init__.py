#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自愈与智能进化系统 - Phase 1 感知层基建

独立可复用 Python 包，可嫁接任何 Flask 项目。

使用方法:
    from self_healing import init_self_healing

    # 在 Flask app 创建后调用
    alert_manager, collector = init_self_healing(
        app=app,
        db=db,                          # SQLAlchemy db 对象
        is_developer_func=is_developer, # 开发者判断函数
        redis_client=redis_client,      # Redis 客户端（可选）
    )

配置（通过环境变量）:
    ALERT_WORKER_ENABLED=true
    REDIS_HOST=localhost
    REDIS_PORT=6379
    WECOM_BOT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
    ALERT_DEDUP_WINDOW=300
    ALERT_NOTIFY_COOLDOWN=60
"""

import logging
import time

logger = logging.getLogger('self_healing')

_alert_manager = None
_collector = None


def init_self_healing(app, db=None, is_developer_func=None, redis_client=None):
    """
    初始化自愈系统（一行接入任何 Flask 项目）

    Args:
        app: Flask 应用实例
        db: SQLAlchemy db 对象（可选，不提供则仅日志不写DB）
        is_developer_func: 开发者权限判断函数（可选，不提供则所有用户可访问监控面板）
        redis_client: Redis 客户端（可选，不提供则降级内存模式）

    Returns:
        (alert_manager, collector) 元组
    """
    global _alert_manager, _collector

    from .config import get_config
    config = get_config()

    # 1. 企业微信机器人
    wecom_bot = None
    webhook_url = config.get('WECOM_BOT_WEBHOOK_URL', '')
    corp_id = config.get('WECHAT_CORP_ID', '')
    corp_secret = config.get('WECHAT_CORP_SECRET', '')
    agent_id = config.get('WECHAT_AGENT_ID', '')

    if webhook_url or (corp_id and corp_secret and agent_id):
        try:
            from .wecom_bot import WeComBot
            wecom_bot = WeComBot(
                webhook_url=webhook_url,
                corp_id=corp_id,
                corp_secret=corp_secret,
                agent_id=agent_id,
            )
            mode = 'Webhook' if webhook_url else '应用消息'
            logger.info(f'企业微信机器人已初始化（{mode}模式）')
        except Exception as e:
            logger.warning(f'企业微信机器人初始化失败: {e}')

    # 2. 告警管理器
    from .alert_manager import AlertManager
    _alert_manager = AlertManager(app, config, db=db, redis_client=redis_client, wecom_bot=wecom_bot)
    _alert_manager.start()

    # 3. 指标采集器
    from .collector import MetricsCollector
    _collector = MetricsCollector(app, config, db=db, redis_client=redis_client)
    _collector.set_start_time(time.time())
    _collector.start()

    # 4. 异常捕获探针
    from .probe import init_probe
    init_probe(app, _alert_manager, _collector)

    # 5. 注册监控面板 API
    from .api import monitor_bp, _init_api

    def _default_is_developer():
        return True

    _init_api(app, _alert_manager, _collector, db, is_developer_func or _default_is_developer)
    app.register_blueprint(monitor_bp)

    # 保存引用到 app 上（供装饰器使用）
    app._alert_manager = _alert_manager
    app._collector = _collector

    logger.info('自愈系统 Phase 1 初始化完成')
    return _alert_manager, _collector


def get_alert_manager():
    """获取告警管理器实例"""
    return _alert_manager


def get_collector():
    """获取指标采集器实例"""
    return _collector


def monitor_business(source_module=None):
    """业务函数监控装饰器（快捷导入）"""
    from .probe import monitor_business as _mb
    return _mb(source_module)
