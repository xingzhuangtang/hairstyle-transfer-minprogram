#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自愈系统配置模块
从环境变量读取配置，支持任何 Flask 项目即插即用
"""

import os


def get_config():
    """获取自愈系统配置（从环境变量）"""
    return {
        # 告警 Worker 开关
        'ALERT_WORKER_ENABLED': os.getenv('ALERT_WORKER_ENABLED', 'true').lower() == 'true',

        # Redis 配置（可选，不可用时降级内存模式）
        'REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
        'REDIS_PORT': int(os.getenv('REDIS_PORT', '6379')),
        'REDIS_PASSWORD': os.getenv('REDIS_PASSWORD', ''),
        'REDIS_DB': int(os.getenv('REDIS_DB', '0')),

        # 企业微信机器人 Webhook（可选，未配置时仅写DB不推送）
        'WECOM_BOT_WEBHOOK_URL': os.getenv('WECOM_BOT_WEBHOOK_URL', ''),

        # 企业微信应用消息 API（可选，与 Webhook 二选一）
        'WECHAT_CORP_ID': os.getenv('WECHAT_CORP_ID', ''),
        'WECHAT_CORP_SECRET': os.getenv('WECHAT_CORP_SECRET', ''),
        'WECHAT_AGENT_ID': os.getenv('WECHAT_AGENT_ID', ''),

        # 限流配置
        'ALERT_DEDUP_WINDOW': int(os.getenv('ALERT_DEDUP_WINDOW', '300')),       # 同类型告警合并窗口（秒）
        'ALERT_NOTIFY_COOLDOWN': int(os.getenv('ALERT_NOTIFY_COOLDOWN', '60')),  # 通知冷却时间（秒）
        'ALERT_NOTIFY_MAX_PER_MIN': int(os.getenv('ALERT_NOTIFY_MAX_PER_MIN', '10')),
        'ALERT_NOTIFY_MAX_PER_HOUR': int(os.getenv('ALERT_NOTIFY_MAX_PER_HOUR', '50')),

        # 数据截断
        'MAX_STACK_TRACE_LEN': int(os.getenv('MAX_STACK_TRACE_LEN', '4096')),
        'MAX_REQUEST_PARAMS_LEN': int(os.getenv('MAX_REQUEST_PARAMS_LEN', '2048')),
        'MAX_RESPONSE_DATA_LEN': int(os.getenv('MAX_RESPONSE_DATA_LEN', '2048')),

        # 队列配置
        'ALERT_QUEUE_MAXSIZE': int(os.getenv('ALERT_QUEUE_MAXSIZE', '1000')),

        # 指标采集间隔（秒）
        'METRICS_COLLECT_INTERVAL': int(os.getenv('METRICS_COLLECT_INTERVAL', '30')),

        # 健康检查缓存（秒）
        'HEALTH_CACHE_TTL': int(os.getenv('HEALTH_CACHE_TTL', '10')),

        # Phase 2: 自动修复配置
        'AUTO_FIX_ENABLED': os.getenv('AUTO_FIX_ENABLED', 'true').lower() == 'true',
        'AUTO_FIX_LOW_RISK': os.getenv('AUTO_FIX_LOW_RISK', 'true').lower() == 'true',
        'APPROVAL_EXPIRES_HOURS': int(os.getenv('APPROVAL_EXPIRES_HOURS', '24')),

        # Phase 3: 防御规则 & 进化分析
        'DEFENSE_RULE_ENABLED': os.getenv('DEFENSE_RULE_ENABLED', 'true').lower() == 'true',
        'EVOLUTION_ANALYSIS_INTERVAL': int(os.getenv('EVOLUTION_ANALYSIS_INTERVAL', '3600')),
    }
