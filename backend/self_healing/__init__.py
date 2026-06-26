#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自愈与智能进化系统 - Phase 1/2/3

独立可复用 Python 包，可嫁接任何 Flask 项目。

Phase 1: 感知层（监控打点、异常捕捉、企微通知）
Phase 2: 自愈层（自动修复、审批流）
Phase 3: 进化层（防御规则、趋势分析、健康评分）

使用方法:
    from self_healing import init_self_healing

    alert_manager, collector = init_self_healing(
        app=app,
        db=db,
        is_developer_func=is_developer,
        redis_client=redis_client,
    )
"""

import logging
import threading
import time

logger = logging.getLogger('self_healing')

_alert_manager = None
_collector = None
_fixer = None
_approval_manager = None
_rule_engine = None
_evolution_analyzer = None


def init_self_healing(app, db=None, is_developer_func=None, redis_client=None):
    """
    初始化自愈系统（一行接入任何 Flask 项目）
    """
    global _alert_manager, _collector, _fixer, _approval_manager, _rule_engine, _evolution_analyzer

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

    # 2. Phase 2: 自动修复引擎
    _fixer = None
    if config.get('AUTO_FIX_ENABLED', True):
        try:
            from .fixer import AutoFixer
            _fixer = AutoFixer(app, config, db=db, redis_client=redis_client, wecom_bot=wecom_bot)
            logger.info('Phase 2: 自动修复引擎已初始化')
        except Exception as e:
            logger.warning(f'自动修复引擎初始化失败: {e}')

    # 3. Phase 2: 审批流管理
    _approval_manager = None
    if _fixer:
        try:
            from .approval import ApprovalManager
            _approval_manager = ApprovalManager(app, config, db=db, wecom_bot=wecom_bot)
            _fixer.set_approval_manager(_approval_manager)
            _approval_manager.set_fixer(_fixer)
            logger.info('Phase 2: 审批流管理已初始化')
        except Exception as e:
            logger.warning(f'审批流管理初始化失败: {e}')

    # 4. Phase 3: 防御规则引擎
    _rule_engine = None
    if config.get('DEFENSE_RULE_ENABLED', True):
        try:
            from .defense_rule import RuleEngine
            _rule_engine = RuleEngine(app, config, db=db, fixer=_fixer)
            logger.info('Phase 3: 防御规则引擎已初始化')
        except Exception as e:
            logger.warning(f'防御规则引擎初始化失败: {e}')

    # 5. 告警管理器（集成 fixer 和 rule_engine）
    from .alert_manager import AlertManager
    _alert_manager = AlertManager(
        app, config, db=db, redis_client=redis_client, wecom_bot=wecom_bot,
        fixer=_fixer, rule_engine=_rule_engine,
    )
    _alert_manager.start()

    # 6. 指标采集器
    from .collector import MetricsCollector
    _collector = MetricsCollector(app, config, db=db, redis_client=redis_client)
    _collector.set_start_time(time.time())
    _collector.start()

    # 7. Phase 3: 进化分析引擎
    _evolution_analyzer = None
    try:
        from .evolution import EvolutionAnalyzer
        _evolution_analyzer = EvolutionAnalyzer(app, config, db=db, collector=_collector)
        logger.info('Phase 3: 进化分析引擎已初始化')
    except Exception as e:
        logger.warning(f'进化分析引擎初始化失败: {e}')

    # 8. 异常捕获探针
    from .probe import init_probe
    init_probe(app, _alert_manager, _collector)

    # 9. 注册监控面板 API
    from .api import monitor_bp, _init_api

    def _default_is_developer():
        return False

    _init_api(
        app, _alert_manager, _collector, db,
        is_developer_func or _default_is_developer,
        fixer=_fixer,
        approval_manager=_approval_manager,
        rule_engine=_rule_engine,
        evolution_analyzer=_evolution_analyzer,
    )
    app.register_blueprint(monitor_bp)

    # 保存引用到 app 上
    app._alert_manager = _alert_manager
    app._collector = _collector
    app._fixer = _fixer
    app._approval_manager = _approval_manager
    app._rule_engine = _rule_engine
    app._evolution_analyzer = _evolution_analyzer

    # 10. 后台初始化：默认防御规则 + 清理过期审批 + 启动健康检查
    def _post_init():
        try:
            if _rule_engine and db:
                with app.app_context():
                    _rule_engine.init_default_rules()
        except Exception as e:
            logger.debug(f'默认规则初始化: {e}')

        try:
            if _approval_manager:
                with app.app_context():
                    _approval_manager.expire_stale_approvals()
        except Exception as e:
            logger.debug(f'过期审批清理: {e}')

        # 启动时主动检查域名配置
        _startup_health_check()

    def _startup_health_check():
        """启动时主动检查关键配置"""
        try:
            if _fixer:
                result = _fixer._fix_domain_config_check()
                if result.get('success') and 'issues' in result.get('detail', '{}'):
                    import json
                    detail = json.loads(result['detail'])
                    issues = detail.get('issues', [])
                    if issues:
                        logger.warning(f'启动健康检查发现 {len(issues)} 个域名配置问题: {json.dumps(issues, ensure_ascii=False)}')
                    else:
                        logger.info('启动健康检查: 所有域名配置正常')
        except Exception as e:
            logger.debug(f'启动健康检查: {e}')

    threading.Thread(target=_post_init, daemon=True, name='sh_post_init').start()

    phases = ['Phase 1 感知层']
    if _fixer:
        phases.append('Phase 2 自愈层')
    if _rule_engine or _evolution_analyzer:
        phases.append('Phase 3 进化层')
    logger.info(f'自愈系统初始化完成: {" + ".join(phases)}')

    return _alert_manager, _collector


def get_alert_manager():
    return _alert_manager


def get_collector():
    return _collector


def get_fixer():
    return _fixer


def get_approval_manager():
    return _approval_manager


def get_rule_engine():
    return _rule_engine


def get_evolution_analyzer():
    return _evolution_analyzer


def monitor_business(source_module=None):
    """业务函数监控装饰器（快捷导入）"""
    from .probe import monitor_business as _mb
    return _mb(source_module)
