#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复验证器
验证已解决的告警是否真正修复 — 检查同类告警是否复发
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger('self_healing')


class AlertVerifier:
    """修复验证器 — 定期扫描待验证告警，检查修复是否真实生效"""

    def __init__(self, app, db=None, config=None):
        self.app = app
        self.db = db
        self.config = config or {}
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._verification_loop,
            daemon=True,
            name='sh_alert_verifier',
        )
        self._thread.start()
        logger.info('修复验证器已启动')

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _verification_loop(self):
        interval = self.config.get('VERIFIER_INTERVAL', 6 * 3600)
        while self._running:
            try:
                with self.app.app_context():
                    self.verify_pending_alerts()
            except Exception as e:
                logger.error(f'修复验证循环异常: {e}')
            time.sleep(interval)

    def verify_pending_alerts(self):
        """扫描所有待验证且超过验证窗口的告警"""
        if not self.db:
            return

        from .models import SystemAlert

        window_hours = self.config.get('VERIFICATION_WINDOW_HOURS', 24)
        cutoff = datetime.now() - timedelta(hours=window_hours)

        pending = self.db.session.query(SystemAlert).filter(
            SystemAlert.status == 'resolved',
            SystemAlert.verification_status == 'pending',
            SystemAlert.resolved_at <= cutoff,
        ).all()

        if not pending:
            return

        logger.info(f'修复验证器: 发现 {len(pending)} 条待验证告警')

        for alert in pending:
            try:
                self.verify_resolution(alert.id)
            except Exception as e:
                logger.error(f'验证告警 {alert.id} 失败: {e}')

    def verify_resolution(self, alert_id):
        """
        验证单个告警的修复是否生效

        逻辑：检查该告警解决后，同 source_module + 同 alert_type 是否有新告警
        """
        if not self.db:
            return {'error': '数据库未配置'}

        from .models import SystemAlert, BugKnowledge

        alert = self.db.session.query(SystemAlert).get(alert_id)
        if not alert:
            return {'error': '告警不存在'}

        if alert.status != 'resolved' or alert.verification_status != 'pending':
            return {'error': '告警状态不符合验证条件'}

        resolved_at = alert.resolved_at
        if not resolved_at:
            return {'error': '缺少解决时间'}

        same_type_alerts = self.db.session.query(SystemAlert).filter(
            SystemAlert.id != alert_id,
            SystemAlert.alert_type == alert.alert_type,
            SystemAlert.created_at > resolved_at,
        )

        if alert.source_module:
            same_type_alerts = same_type_alerts.filter(
                SystemAlert.source_module == alert.source_module
            )

        recurrence_count = same_type_alerts.count()

        if recurrence_count == 0:
            alert.verification_status = 'verified'
            alert.verified_at = datetime.now()

            if alert.bug_knowledge_id:
                bug = self.db.session.query(BugKnowledge).filter_by(
                    bug_id=alert.bug_knowledge_id
                ).first()
                if bug:
                    bug.verification_count = (bug.verification_count or 0) + 1
                    bug.success_count = (bug.success_count or 0) + 1
                    bug.confidence = round(
                        bug.success_count / bug.verification_count, 2
                    ) if bug.verification_count > 0 else 0

            self.db.session.commit()
            logger.info(f'告警 {alert_id} 验证通过: 解决后无同类告警复发')
            return {
                'success': True,
                'verification_status': 'verified',
                'recurrence_count': 0,
            }
        else:
            alert.verification_status = 'failed'
            alert.verified_at = datetime.now()
            alert.status = 'new'
            alert.resolved_at = None
            alert.resolved_by = None
            alert.resolve_note = (alert.resolve_note or '') + f'\n[自动验证] 修复后 {recurrence_count} 条同类告警复发，已重新打开'

            if alert.bug_knowledge_id:
                bug = self.db.session.query(BugKnowledge).filter_by(
                    bug_id=alert.bug_knowledge_id
                ).first()
                if bug:
                    bug.verification_count = (bug.verification_count or 0) + 1
                    bug.confidence = round(
                        bug.success_count / bug.verification_count, 2
                    ) if bug.verification_count > 0 else 0

            self.db.session.commit()
            logger.warning(
                f'告警 {alert_id} 验证失败: 解决后出现 {recurrence_count} 条同类告警，已重新打开'
            )
            return {
                'success': False,
                'verification_status': 'failed',
                'recurrence_count': recurrence_count,
            }


def init_verifier(app, db=None, config=None):
    verifier = AlertVerifier(app, db, config)
    verifier.start()
    return verifier
