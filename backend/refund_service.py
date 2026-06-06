#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
退款业务服务
处理退款申请创建、审批、token 生成/验证、退款执行
"""

import hmac
import hashlib
import base64
import time
import uuid
from datetime import datetime

from app import db
from config import get_config


class RefundService:
    """退款业务服务"""

    def __init__(self):
        self.config = get_config()

    @staticmethod
    def generate_approval_token(application_id):
        """
        生成 HMAC-SHA256 签名的审批 token

        Args:
            application_id: 退款申请 ID

        Returns:
            str: URL-safe base64 编码的 token
        """
        config = get_config()
        secret_key = config.JWT_SECRET_KEY
        timestamp = str(int(time.time()))
        message = f"{application_id}:{timestamp}"

        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        raw = f"{application_id}:{timestamp}:{signature}"
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def verify_approval_token(token, max_age=86400):
        """
        验证审批 token

        Args:
            token: 审批 token
            max_age: 最大有效时间（秒），默认 24 小时

        Returns:
            tuple: (application_id, error)
        """
        try:
            config = get_config()
            secret_key = config.JWT_SECRET_KEY

            raw = base64.urlsafe_b64decode(token.encode()).decode()
            parts = raw.split(':')
            if len(parts) != 3:
                return None, 'Invalid token format'

            application_id, timestamp, signature = parts

            # 检查过期
            if int(time.time()) - int(timestamp) > max_age:
                return None, 'Token expired'

            # 验证签名
            message = f"{application_id}:{timestamp}"
            expected = hmac.new(
                secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            if signature != expected:
                return None, 'Invalid signature'

            return int(application_id), None
        except Exception as e:
            return None, f'Token decode failed: {str(e)}'

    def generate_consumption_summary(self, user):
        """
        自动生成消费使用摘要

        Args:
            user: User 对象

        Returns:
            dict: 消费摘要
        """
        from models import ConsumptionRecord

        total_spent = float(user.total_recharge or 0)
        total_consumed = user.total_consumed_hairs or 0
        remaining_hairs = (user.scissor_hairs or 0) + (user.comb_hairs or 0)

        # 获取最近 10 条消费记录
        recent = ConsumptionRecord.query.filter_by(user_id=user.id)\
            .order_by(ConsumptionRecord.created_at.desc()).limit(10).all()

        usage_history = [{
            'service_type': r.service_type,
            'hairs': r.hairs_consumed,
            'date': r.created_at.isoformat()
        } for r in recent]

        return {
            'total_spent': total_spent,
            'remaining_hairs': remaining_hairs,
            'scissor_hairs': user.scissor_hairs,
            'comb_hairs': user.comb_hairs,
            'total_consumed': total_consumed,
            'recent_usage': usage_history
        }

    def create_application(self, user, refund_type, refund_amount, reason,
                           applicant_name, applicant_phone, suggestions=None):
        """
        创建退款申请并发送企业微信通知

        Args:
            user: User 对象
            refund_type: 'recharge' 或 'membership'
            refund_amount: 申请退款金额
            reason: 退款原因
            applicant_name: 申请人姓名
            applicant_phone: 申请人电话
            suggestions: 建议（可选）

        Returns:
            dict: {success, application_id, error}
        """
        from models import RefundApplication, RechargeRecord, MemberOrder

        # 验证退款金额
        if refund_amount <= 0:
            return {'success': False, 'error': '退款金额必须大于 0'}

        if refund_type == 'membership':
            # 会员退款最多 99 元
            if refund_amount > 99:
                return {'success': False, 'error': '会员退款金额不能超过 99 元'}

            # 检查用户是否是会员
            if user.member_level != 'vip' or not user.member_expire_at:
                return {'success': False, 'error': '当前非会员状态，无法申请会员退款'}

            # 检查会员是否已过期
            if user.member_expire_at < datetime.now():
                return {'success': False, 'error': '会员已过期，无法申请退款'}

        elif refund_type == 'recharge':
            # 检查是否有成功的充值订单
            order = RechargeRecord.query.filter_by(
                user_id=user.id, payment_status='success'
            ).first()
            if not order:
                return {'success': False, 'error': '没有可退款的充值订单'}

        # 检查是否有待处理的申请
        pending = RefundApplication.query.filter_by(
            user_id=user.id, status='pending'
        ).first()
        if pending:
            return {'success': False, 'error': '您已有待处理的退款申请，请耐心等待审批'}

        # 生成消费摘要
        consumption_summary = self.generate_consumption_summary(user)

        # 创建申请
        application = RefundApplication(
            user_id=user.id,
            applicant_name=applicant_name,
            applicant_phone=applicant_phone,
            applicant_wechat_id=user.openid or '',
            refund_type=refund_type,
            refund_amount=refund_amount,
            reason=reason,
            consumption_summary=consumption_summary,
            suggestions=suggestions
        )
        db.session.add(application)
        db.session.commit()

        # 发送企业微信通知
        try:
            approval_token = self.generate_approval_token(application.id)
            from refund_notifier import RefundNotifier
            notifier = RefundNotifier()
            notifier.send_refund_application_notification(application, approval_token)
        except Exception as e:
            print(f"⚠️  发送企业微信通知失败: {e}")
            # 通知失败不影响申请创建

        return {'success': True, 'application_id': application.id}

    def approve_application(self, application_id, admin_user_id=0, rejection_reason=None):
        """
        审批退款申请（同意或拒绝）

        Args:
            application_id: 退款申请 ID
            admin_user_id: 审批人 ID（0 表示系统管理员）
            rejection_reason: 拒绝原因（拒绝时必填）

        Returns:
            dict: {success, status, error}
        """
        from models import RefundApplication, RechargeRecord, MemberOrder, User
        from payment_service import WeChatPayService, PaymentService

        application = RefundApplication.query.get(application_id)
        if not application:
            return {'success': False, 'error': '申请不存在'}

        if application.status != 'pending':
            return {'success': False, 'error': f'申请状态已为 {application.status}，无法重复审批'}

        user = User.query.get(application.user_id)
        if not user:
            return {'success': False, 'error': '用户不存在'}

        if rejection_reason:
            # 拒绝
            application.status = 'rejected'
            application.rejection_reason = rejection_reason
            application.approved_by = admin_user_id
            application.approved_at = datetime.now()
            db.session.commit()

            return {'success': True, 'status': 'rejected'}

        # 同意 - 执行退款
        if application.refund_type == 'recharge':
            return self._process_recharge_refund(application, user)
        elif application.refund_type == 'membership':
            return self._process_membership_refund(application, user)
        else:
            return {'success': False, 'error': f'未知退款类型: {application.refund_type}'}

    def _process_recharge_refund(self, application, user):
        """处理充值退款"""
        from models import RechargeRecord
        from payment_service import WeChatPayService

        # 找到最近的成功充值订单
        order = RechargeRecord.query.filter_by(
            user_id=user.id, payment_status='success'
        ).order_by(RechargeRecord.created_at.desc()).first()

        if not order:
            return {'success': False, 'error': '找不到可退款的充值订单'}

        # 发起微信退款
        refund_no = f"RF{int(time.time())}{uuid.uuid4().hex[:8]}"
        wechat_service = WeChatPayService()
        refund_result = wechat_service.refund_order(
            order_no=order.order_no,
            refund_no=refund_no,
            amount=float(application.refund_amount),
            reason=f"用户退款申请 #{application.id}"
        )

        if not refund_result['success']:
            return {'success': False, 'error': f'微信退款发起失败: {refund_result.get("error", "未知错误")}'}

        # 更新申请状态
        application.status = 'approved'
        application.approved_at = datetime.now()
        db.session.commit()

        # 注意：实际扣回发丝在微信退款回调中处理（process_refund_success）

        return {
            'success': True,
            'status': 'approved',
            'refund_no': refund_no,
            'wechat_refund_id': refund_result.get('refund_id')
        }

    def _process_membership_refund(self, application, user):
        """处理会员退款"""
        from models import MemberOrder
        from payment_service import WeChatPayService

        # 计算剩余天数
        remaining_days = (user.member_expire_at - datetime.now()).days
        if remaining_days <= 0:
            return {'success': False, 'error': '会员已过期，无法退款'}

        # 计算应退金额：99 × (剩余天数 / 365)，向下取整到分
        calculated_refund = int(99 * remaining_days / 365 * 100) / 100

        # 找到会员订单
        order = MemberOrder.query.filter_by(
            user_id=user.id, payment_status='success'
        ).order_by(MemberOrder.created_at.desc()).first()

        if not order:
            return {'success': False, 'error': '找不到会员订单'}

        # 发起微信退款
        refund_no = f"RF{int(time.time())}{uuid.uuid4().hex[:8]}"
        wechat_service = WeChatPayService()
        refund_result = wechat_service.refund_order(
            order_no=order.order_no,
            refund_no=refund_no,
            amount=calculated_refund,
            reason=f"会员退款申请 #{application.id}"
        )

        if not refund_result['success']:
            return {'success': False, 'error': f'微信退款发起失败: {refund_result.get("error", "未知错误")}'}

        # 更新申请状态和会员订单
        application.status = 'approved'
        application.approved_at = datetime.now()

        order.payment_status = 'refunded'
        order.refund_amount = calculated_refund
        order.refunded_at = datetime.now()
        order.refund_days = remaining_days

        # 降级为普通用户
        user.member_level = 'normal'
        user.member_expire_at = None

        # 记录财务流水
        from financial_service import FinancialService
        FinancialService.record_refund(
            user_id=user.id,
            refund_amount=calculated_refund,
            refund_type='membership',
            related_id=order.id
        )

        # 注意：会员赠送的 1000 发丝不扣回（已确认策略）

        db.session.commit()

        return {
            'success': True,
            'status': 'approved',
            'refund_amount': calculated_refund,
            'refund_no': refund_no,
            'remaining_days': remaining_days,
            'wechat_refund_id': refund_result.get('refund_id')
        }
