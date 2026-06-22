#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审批流管理
内部审批 + 企微通知（不依赖企微审批 API）
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('self_healing')


class ApprovalManager:
    """审批流管理器"""

    def __init__(self, app, config, db=None, wecom_bot=None, fixer=None):
        self.app = app
        self.config = config
        self.db = db
        self.wecom_bot = wecom_bot
        self.fixer = fixer

    def set_fixer(self, fixer):
        self.fixer = fixer

    def create_approval(self, fix_id, fix_name, alert_id, risk_level, fix_description):
        """创建审批记录"""
        if not self.db:
            logger.warning('数据库未配置，无法创建审批记录')
            return None

        try:
            from .models import ApprovalRecord

            expires_hours = self.config.get('APPROVAL_EXPIRES_HOURS', 24)
            approval = ApprovalRecord(
                fix_id=fix_id,
                fix_name=fix_name,
                alert_id=alert_id,
                risk_level=risk_level,
                fix_description=fix_description,
                status='pending',
                requested_by='system',
                expires_at=datetime.now() + timedelta(hours=expires_hours),
            )
            self.db.session.add(approval)
            self.db.session.commit()

            if self.wecom_bot:
                self.wecom_bot.send_approval_request(approval)

            logger.info(f'审批记录已创建: #{approval.id} [{fix_name}] 风险={risk_level}')
            return approval

        except Exception as e:
            logger.error(f'创建审批记录失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return None

    def approve(self, approval_id, approved_by='developer'):
        """批准并执行修复"""
        if not self.db:
            return {'success': False, 'error': '数据库未配置'}

        try:
            from .models import ApprovalRecord

            approval = self.db.session.query(ApprovalRecord).get(approval_id)
            if not approval:
                return {'success': False, 'error': '审批记录不存在'}

            if approval.status != 'pending':
                return {'success': False, 'error': f'审批状态为 {approval.status}，无法操作'}

            if approval.expires_at and datetime.now() > approval.expires_at:
                approval.status = 'expired'
                self.db.session.commit()
                return {'success': False, 'error': '审批已过期'}

            if not self.fixer:
                return {'success': False, 'error': '修复引擎未初始化'}

            result = self.fixer.execute_fix(
                fix_id=approval.fix_id,
                alert_id=approval.alert_id,
                fix_type='approved',
                executed_by=approved_by,
            )

            approval.status = 'approved'
            approval.approved_by = approved_by
            approval.approved_at = datetime.now()
            approval.fix_result = json.dumps(result, ensure_ascii=False)
            approval.executed_at = datetime.now()
            self.db.session.commit()

            return {'success': True, 'result': result, 'approval': approval.to_dict()}

        except Exception as e:
            logger.error(f'审批执行失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return {'success': False, 'error': str(e)}

    def reject(self, approval_id, rejected_by='developer'):
        """拒绝修复"""
        if not self.db:
            return {'success': False, 'error': '数据库未配置'}

        try:
            from .models import ApprovalRecord

            approval = self.db.session.query(ApprovalRecord).get(approval_id)
            if not approval:
                return {'success': False, 'error': '审批记录不存在'}

            if approval.status != 'pending':
                return {'success': False, 'error': f'审批状态为 {approval.status}，无法操作'}

            approval.status = 'rejected'
            approval.approved_by = rejected_by
            approval.approved_at = datetime.now()
            self.db.session.commit()

            return {'success': True, 'approval': approval.to_dict()}

        except Exception as e:
            logger.error(f'拒绝操作失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return {'success': False, 'error': str(e)}

    def get_pending_approvals(self):
        """获取待审批列表"""
        if not self.db:
            return []

        try:
            from .models import ApprovalRecord

            return self.db.session.query(ApprovalRecord) \
                .filter(ApprovalRecord.status == 'pending') \
                .order_by(ApprovalRecord.created_at.desc()) \
                .all()
        except Exception as e:
            logger.error(f'查询待审批列表失败: {e}')
            return []

    def get_approval_history(self, page=1, page_size=20, status=None):
        """获取审批历史"""
        if not self.db:
            return [], 0

        try:
            from .models import ApprovalRecord

            query = self.db.session.query(ApprovalRecord)
            if status:
                query = query.filter(ApprovalRecord.status == status)

            total = query.count()
            items = query.order_by(ApprovalRecord.created_at.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return items, total
        except Exception as e:
            logger.error(f'查询审批历史失败: {e}')
            return [], 0

    def expire_stale_approvals(self):
        """清理过期审批"""
        if not self.db:
            return 0

        try:
            from .models import ApprovalRecord

            stale = self.db.session.query(ApprovalRecord) \
                .filter(
                    ApprovalRecord.status == 'pending',
                    ApprovalRecord.expires_at < datetime.now()
                ).all()

            count = 0
            for a in stale:
                a.status = 'expired'
                count += 1

            if count > 0:
                self.db.session.commit()

            return count
        except Exception as e:
            logger.error(f'清理过期审批失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return 0
