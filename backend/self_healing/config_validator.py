#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置校验探针
启动时和定期校验关键配置，发现配置类问题自动告警
"""

import json
import logging
import os
import threading
import time
from datetime import datetime

logger = logging.getLogger('self_healing')


class ConfigValidator:
    """配置校验探针"""

    def __init__(self, app, db=None, alert_manager=None, bug_recorder=None):
        self.app = app
        self.db = db
        self.alert_manager = alert_manager
        self.bug_recorder = bug_recorder
        self._thread = None
        self._running = False

    def start(self):
        """启动后台校验线程"""
        self._running = True
        self._thread = threading.Thread(
            target=self._validation_loop,
            daemon=True,
            name='self_healing_config_validator'
        )
        self._thread.start()
        logger.info('配置校验探针已启动')

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _validation_loop(self):
        """后台校验循环（每 6 小时执行一次）"""
        # 启动时立即执行一次
        self.validate_all()

        interval = 6 * 3600  # 6 小时
        while self._running:
            time.sleep(interval)
            if self._running:
                self.validate_all()

    def validate_all(self):
        """执行所有配置校验"""
        try:
            with self.app.app_context():
                self._validate_developer_accounts()
                self._validate_critical_env_vars()
                self._validate_database_config()
        except Exception as e:
            logger.error(f'配置校验失败: {e}')

    def _validate_developer_accounts(self):
        """校验 DEVELOPER_ACCOUNTS 中的用户 ID 是否存在"""
        try:
            from config import DEVELOPER_MODE_ENABLED, DEVELOPER_ACCOUNTS

            if not DEVELOPER_MODE_ENABLED:
                return

            if not DEVELOPER_ACCOUNTS:
                self._record_config_alert(
                    title='配置告警: DEVELOPER_MODE_ENABLED=true 但未配置 DEVELOPER_ACCOUNTS',
                    description='开发者模式已开启，但 DEVELOPER_ACCOUNTS 为空，所有用户都无法访问开发者功能',
                    severity='high',
                    category='configuration',
                    fix_suggestion='在 .env 中设置 DEVELOPER_ACCOUNTS=用户ID列表（如 DEVELOPER_ACCOUNTS=2,88）',
                )
                return

            # 检查每个用户 ID 是否存在
            if not self.db:
                return

            from models import User

            for user_id in DEVELOPER_ACCOUNTS:
                user = self.db.session.query(User).filter_by(id=user_id).first()
                if not user:
                    self._record_config_alert(
                        title=f'配置告警: DEVELOPER_ACCOUNTS 中的用户 ID {user_id} 不存在',
                        description=f'DEVELOPER_ACCOUNTS={DEVELOPER_ACCOUNTS}，但用户 ID {user_id} 在数据库中不存在',
                        severity='medium',
                        category='configuration',
                        fix_suggestion=f'从 DEVELOPER_ACCOUNTS 中移除不存在的用户 ID {user_id}，或创建该用户',
                    )
                else:
                    logger.debug(f'配置校验通过: 用户 ID {user_id} ({user.phone}) 存在于 DEVELOPER_ACCOUNTS')

        except Exception as e:
            logger.error(f'开发者账号校验失败: {e}')

    def _validate_critical_env_vars(self):
        """校验关键环境变量是否配置"""
        critical_vars = [
            ('MYSQL_HOST', '数据库主机'),
            ('MYSQL_DATABASE', '数据库名称'),
            ('ALIBABA_CLOUD_ACCESS_KEY_ID', '阿里云 AccessKey ID'),
            ('JWT_SECRET_KEY', 'JWT 密钥'),
        ]

        for var_name, var_desc in critical_vars:
            value = os.getenv(var_name, '')
            if not value:
                self._record_config_alert(
                    title=f'配置告警: 关键环境变量 {var_name} 未配置',
                    description=f'{var_desc}（{var_name}）未设置，可能导致相关功能不可用',
                    severity='high',
                    category='configuration',
                    fix_suggestion=f'在 .env 中设置 {var_name}',
                )

    def _validate_database_config(self):
        """校验数据库连接配置"""
        try:
            if not self.db:
                return

            # 检查数据库连接
            self.db.session.execute(self.db.text('SELECT 1'))

            # 检查关键表是否存在
            from sqlalchemy import inspect
            inspector = inspect(self.db.engine)
            required_tables = ['users', 'recharge_records', 'member_orders']

            existing_tables = inspector.get_table_names()
            for table in required_tables:
                if table not in existing_tables:
                    self._record_config_alert(
                        title=f'配置告警: 数据库表 {table} 不存在',
                        description=f'关键表 {table} 未在数据库中找到，可能导致功能异常',
                        severity='critical',
                        category='configuration',
                        fix_suggestion=f'运行 python init_db.py 或 python migrate_*.py 创建表',
                    )

        except Exception as e:
            self._record_config_alert(
                title='配置告警: 数据库连接失败',
                description=f'无法连接到数据库: {str(e)}',
                severity='critical',
                category='configuration',
                fix_suggestion='检查 .env 中的 MYSQL_* 配置是否正确',
            )

    def _record_config_alert(self, title, description, severity, category, fix_suggestion):
        """记录配置告警"""
        # 记录到告警系统
        if self.alert_manager:
            self.alert_manager.record_alert(
                alert_type='warning',
                severity=severity,
                title=title,
                description=description,
                source_module='config_validator',
                environment_info={
                    'category': category,
                    'fix_suggestion': fix_suggestion,
                    'timestamp': datetime.now().isoformat(),
                },
            )

        # 记录到 Bug 知识库
        if self.bug_recorder:
            import hashlib
            bug_id = f'CFG-{hashlib.md5(title.encode()).hexdigest()[:8].upper()}'

            self.bug_recorder.record_bug(
                bug_id=bug_id,
                title=title,
                category=category,
                severity=severity,
                root_cause=description,
                fix_description=fix_suggestion,
                prevention='配置校验探针会在启动时和每 6 小时自动检查配置问题',
            )

        logger.warning(f'配置告警: {title}')


def init_config_validator(app, db=None, alert_manager=None, bug_recorder=None):
    """初始化配置校验探针"""
    validator = ConfigValidator(app, db, alert_manager, bug_recorder)
    validator.start()
    return validator
