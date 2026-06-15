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
import logging
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

        # 发送企业微信通知（附带核算清单）
        try:
            approval_token = self.generate_approval_token(application.id)
            from refund_notifier import RefundNotifier
            notifier = RefundNotifier()
            
            # 计算核算清单
            calculation = self._calculate_refund_detail(user, refund_type, refund_amount)
            
            # 发送带核算清单的审批通知
            notifier.send_approval_notification_with_calculation(application, approval_token, calculation)
        except Exception as e:
            print(f"⚠️  发送企业微信通知失败: {e}")
            # 通知失败不影响申请创建

        return {'success': True, 'application_id': application.id}

    def _calculate_refund_detail(self, user, refund_type, refund_amount):
        """
        计算退款核算详情（内部方法）
        
        Args:
            user: User 对象
            refund_type: 退款类型
            refund_amount: 退款金额
            
        Returns:
            dict: 核算清单数据
        """
        from models import RechargeRecord
        
        total_hairs = (user.scissor_hairs or 0) + (user.comb_hairs or 0)
        calculation = {
            'refund_type': refund_type,
            'total_hairs': total_hairs,
            'scissor_hairs': user.scissor_hairs or 0,
            'comb_hairs': user.comb_hairs or 0
        }
        
        if refund_type == 'recharge':
            order = RechargeRecord.query.filter_by(
                user_id=user.id, payment_status='success'
            ).order_by(RechargeRecord.created_at.desc()).first()

            if order:
                # 梳子卡槽发丝是赠送的，退款时只扣回剪刀卡槽发丝
                refund_ratio = float(refund_amount) / float(order.amount)
                need_scissor = int(order.scissor_hairs * refund_ratio)
                hairs_to_deduct = need_scissor

                scissor_hairs = user.scissor_hairs or 0
                cash_deduction = 0.0
                actual_refund = float(refund_amount)

                if scissor_hairs < hairs_to_deduct:
                    missing_hairs = hairs_to_deduct - scissor_hairs
                    cash_deduction = round(missing_hairs * 0.01, 2)
                    actual_refund = max(0, float(refund_amount) - cash_deduction)

                calculation.update({
                    'charge_amount': float(order.amount),
                    'charge_hairs': order.scissor_hairs + order.comb_hairs,
                    'refund_amount_requested': float(refund_amount),
                    'hairs_to_deduct': hairs_to_deduct,
                    'hairs_sufficient': scissor_hairs >= hairs_to_deduct,
                    'missing_hairs': max(0, hairs_to_deduct - scissor_hairs),
                    'cash_deduction': cash_deduction,
                    'actual_refund': actual_refund
                })
                
        elif refund_type == 'membership':
            remaining_days = (user.member_expire_at - datetime.now()).days
            calculated_refund = int(99 * remaining_days / 365 * 100) / 100
            hairs_to_deduct = 1000
            
            cash_deduction = 0.0
            actual_refund = calculated_refund
            
            if total_hairs < hairs_to_deduct:
                missing_hairs = hairs_to_deduct - total_hairs
                cash_deduction = round(missing_hairs * 0.01, 2)
                actual_refund = max(0, calculated_refund - cash_deduction)
            
            calculation.update({
                'member_price': 99,
                'remaining_days': remaining_days,
                'refund_amount_requested': calculated_refund,
                'hairs_to_deduct': hairs_to_deduct,
                'hairs_sufficient': total_hairs >= hairs_to_deduct,
                'missing_hairs': max(0, hairs_to_deduct - total_hairs),
                'cash_deduction': cash_deduction,
                'actual_refund': actual_refund
            })
        
        return calculation

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
        """处理充值退款（带重试机制）"""
        from models import RechargeRecord
        from payment_service import WeChatPayService

        refund_logger = logging.getLogger('refund')

        # 找到最近的成功充值订单
        order = RechargeRecord.query.filter_by(
            user_id=user.id, payment_status='success'
        ).order_by(RechargeRecord.created_at.desc()).first()

        if not order:
            return {'success': False, 'error': '找不到可退款的充值订单'}

        # 检查是否是手动修复的订单（没有真实微信支付）
        is_manual_order = order.transaction_id and order.transaction_id.startswith('MANUAL_FIX')

        if is_manual_order:
            # 手动订单：跳过微信退款，直接在系统内标记
            refund_logger.info(
                f"[REFUND] 手动订单跳过微信退款: order_no={order.order_no}, "
                f"transaction_id={order.transaction_id}"
            )

            # 更新订单状态
            order.payment_status = 'refunded'
            order.refund_amount = float(application.refund_amount)
            order.refunded_at = datetime.now()

            # 更新申请状态
            application.status = 'approved'
            application.approved_at = datetime.now()
            db.session.commit()

            # 扣回发丝
            self._deduct_hairs_on_refund(user, application)

            refund_logger.info(
                f"[REFUND] 手动订单退款完成: application_id={application.id}, "
                f"user_id={user.id}, amount={application.refund_amount}"
            )

            return {
                'success': True,
                'status': 'approved',
                'refund_no': 'MANUAL',
                'wechat_refund_id': None
            }

        # 发起微信退款（带重试，最多3次）
        refund_no = f"RF{int(time.time())}{uuid.uuid4().hex[:8]}"
        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            wechat_service = WeChatPayService()
            refund_result = wechat_service.refund_order(
                order_no=order.order_no,
                refund_no=refund_no,
                amount=float(application.refund_amount),
                reason=f"用户退款申请 #{application.id}"
            )

            if refund_result['success']:
                break

            last_error = refund_result.get('error', '未知错误')
            refund_logger.warning(
                f"[REFUND] 充值退款失败 (attempt {attempt}/{max_retries}): "
                f"order_no={order.order_no}, error={last_error}"
            )

            # 如果是商户余额不足，直接失败，不重试
            if '余额不足' in last_error:
                refund_logger.error(
                    f"[REFUND] 商户号余额不足，终止重试: order_no={order.order_no}"
                )
                return {'success': False, 'error': last_error}

            # 如果是已退款，认为是成功
            if '已退款' in last_error or '重复' in last_error:
                refund_logger.info(f"[REFUND] 订单已退款（重复操作）: order_no={order.order_no}")
                break

            # 其他错误，等待后重试
            if attempt < max_retries:
                wait_seconds = 2 * attempt  # 2s, 4s, 8s
                refund_logger.info(f"[REFUND] {wait_seconds}s 后重试...")
                time.sleep(wait_seconds)

        if not refund_result.get('success'):
            return {'success': False, 'error': f'微信退款发起失败: {last_error}'}

        # 更新订单状态
        order.payment_status = 'refunded'
        order.refund_amount = float(application.refund_amount)
        order.refunded_at = datetime.now()

        # 更新申请状态
        application.status = 'approved'
        application.approved_at = datetime.now()
        db.session.commit()

        # 立即扣回发丝（不依赖回调）
        self._deduct_hairs_on_refund(user, application)

        refund_logger.info(
            f"[REFUND] 充值退款成功: application_id={application.id}, "
            f"user_id={user.id}, amount={application.refund_amount}, "
            f"refund_no={refund_no}"
        )

        return {
            'success': True,
            'status': 'approved',
            'refund_no': refund_no,
            'wechat_refund_id': refund_result.get('refund_id')
        }

    def _process_membership_refund(self, application, user):
        """处理会员退款（带重试机制）"""
        from models import MemberOrder
        from payment_service import WeChatPayService

        refund_logger = logging.getLogger('refund')

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

        # 发起微信退款（带重试，最多3次）
        refund_no = f"RF{int(time.time())}{uuid.uuid4().hex[:8]}"
        max_retries = 3
        last_error = None
        refund_result = {'success': False}

        for attempt in range(1, max_retries + 1):
            wechat_service = WeChatPayService()
            refund_result = wechat_service.refund_order(
                order_no=order.order_no,
                refund_no=refund_no,
                amount=calculated_refund,
                reason=f"会员退款申请 #{application.id}"
            )

            if refund_result['success']:
                break

            last_error = refund_result.get('error', '未知错误')
            refund_logger.warning(
                f"[REFUND] 会员退款失败 (attempt {attempt}/{max_retries}): "
                f"order_no={order.order_no}, error={last_error}"
            )

            # 如果是商户余额不足，直接失败，不重试
            if '余额不足' in last_error:
                refund_logger.error(
                    f"[REFUND] 商户号余额不足，终止重试: order_no={order.order_no}"
                )
                return {'success': False, 'error': last_error}

            # 如果是已退款，认为是成功
            if '已退款' in last_error or '重复' in last_error:
                refund_logger.info(f"[REFUND] 会员订单已退款（重复操作）: order_no={order.order_no}")
                break

            # 其他错误，等待后重试
            if attempt < max_retries:
                wait_seconds = 2 * attempt
                refund_logger.info(f"[REFUND] {wait_seconds}s 后重试...")
                time.sleep(wait_seconds)

        if not refund_result.get('success'):
            return {'success': False, 'error': f'微信退款发起失败: {last_error}'}

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

        # 扣回会员赠送的 1000 发丝
        total_hairs = (user.scissor_hairs or 0) + (user.comb_hairs or 0)
        hairs_to_deduct = 1000
        cash_deduction = 0.0

        if total_hairs >= hairs_to_deduct:
            # 发丝充足，直接扣回 1000 发丝
            deduct_ratio = hairs_to_deduct / total_hairs if total_hairs > 0 else 0
            deduct_scissor = int((user.scissor_hairs or 0) * deduct_ratio)
            deduct_comb = int((user.comb_hairs or 0) * deduct_ratio)
            
            user.scissor_hairs = (user.scissor_hairs or 0) - deduct_scissor
            user.comb_hairs = (user.comb_hairs or 0) - deduct_comb
            
            refund_logger.info(
                f"[REFUND] 发丝充足，扣回 1000 发丝：scissor={deduct_scissor}, comb={deduct_comb}"
            )
        else:
            # 发丝不足，扣回全部剩余发丝，差额用现金抵扣
            deduct_scissor = user.scissor_hairs or 0
            deduct_comb = user.comb_hairs or 0
            remaining_hairs = total_hairs
            
            user.scissor_hairs = 0
            user.comb_hairs = 0
            
            # 计算差额：10 元 = 1000 发丝，即 0.01 元/发丝
            missing_hairs = hairs_to_deduct - remaining_hairs
            cash_deduction = round(missing_hairs * 0.01, 2)
            
            refund_logger.info(
                f"[REFUND] 发丝不足，扣回 {remaining_hairs} 发丝，现金抵扣 ¥{cash_deduction} "
                f"(缺 {missing_hairs} 发丝 × 0.01 元)"
            )

        # 记录财务流水（退款金额减去现金抵扣）
        actual_refund = calculated_refund - cash_deduction
        
        from financial_service import FinancialService
        FinancialService.record_refund(
            user_id=user.id,
            refund_amount=actual_refund,
            refund_type='membership',
            related_id=order.id
        )

        # 如果有现金抵扣，记录发丝扣回流水
        if deduct_scissor > 0 or deduct_comb > 0:
            from models import ConsumptionRecord
            consumption = ConsumptionRecord(
                user_id=user.id,
                task_id=f'membership_refund_{application.id}',
                service_type='combined',
                hairs_consumed=deduct_scissor + deduct_comb,
                scissor_deducted=deduct_scissor,
                comb_deducted=deduct_comb,
                status='success'
            )
            db.session.add(consumption)

        # 如果有现金抵扣，记录现金扣回流水
        if cash_deduction > 0:
            from models import FinancialRecord
            cash_record = FinancialRecord(
                user_id=user.id,
                record_type='cash_consumption',
                amount=-cash_deduction,
                description=f'会员退款发丝不足抵扣 (缺{hairs_to_deduct - total_hairs}发丝)',
                payment_method='balance',
                related_id=application.id,
                related_type='refund_application',
                hairs_changed=hairs_to_deduct - total_hairs,
                status='success'
            )
            db.session.add(cash_record)

        db.session.commit()

        refund_logger.info(
            f"[REFUND] 会员退款成功: application_id={application.id}, "
            f"user_id={user.id}, amount={calculated_refund}, "
            f"remaining_days={remaining_days}"
        )

        return {
            'success': True,
            'status': 'approved',
            'refund_amount': calculated_refund,
            'refund_no': refund_no,
            'remaining_days': remaining_days,
            'wechat_refund_id': refund_result.get('refund_id')
        }

    def _deduct_hairs_on_refund(self, user, application):
        """
        退款时扣回用户发丝（充值退款通用规则）

        规则：梳子卡槽发丝是赠送的，退款时只扣回剪刀卡槽发丝。
        剪刀发丝充足则全额扣回；不足则扣回全部剩余剪刀发丝，
        差额按 10元=1000发丝（0.01元/发丝）从退款金额中抵扣。

        Args:
            user: User 对象
            application: RefundApplication 对象
        """
        from models import RechargeRecord, ConsumptionRecord, FinancialRecord
        import logging

        refund_logger = logging.getLogger('refund')

        # 找到原订单
        order = RechargeRecord.query.filter_by(
            user_id=user.id, payment_status='refunded'
        ).order_by(RechargeRecord.refunded_at.desc()).first()

        if not order:
            refund_logger.warning(f"[REFUND] 找不到已退款订单，无法扣回发丝: user_id={user.id}")
            return

        # 按退款比例计算应扣回的发丝（只扣剪刀卡槽，梳子是赠送的不扣）
        refund_ratio = float(application.refund_amount) / float(order.amount)
        need_scissor = int(order.scissor_hairs * refund_ratio)
        hairs_to_deduct = need_scissor

        scissor_hairs = user.scissor_hairs or 0
        cash_deduction = 0.0
        deduct_scissor = 0

        if scissor_hairs >= hairs_to_deduct:
            # 剪刀发丝充足，扣回应扣数量
            deduct_scissor = need_scissor
            user.scissor_hairs = scissor_hairs - deduct_scissor

            refund_logger.info(
                f"[REFUND] 剪刀发丝充足，扣回 {deduct_scissor} 发丝"
            )
        else:
            # 剪刀发丝不足，扣回全部剩余剪刀发丝，差额用现金抵扣
            deduct_scissor = scissor_hairs
            user.scissor_hairs = 0

            missing_hairs = hairs_to_deduct - scissor_hairs
            cash_deduction = round(missing_hairs * 0.01, 2)

            refund_logger.info(
                f"[REFUND] 剪刀发丝不足，扣回 {deduct_scissor} 发丝，现金抵扣 ¥{cash_deduction} "
                f"(缺 {missing_hairs} 发丝 × 0.01 元)"
            )

        # 记录消费流水
        if deduct_scissor > 0:
            consumption = ConsumptionRecord(
                user_id=user.id,
                task_id=f'refund_{application.id}',
                service_type='combined',
                hairs_consumed=deduct_scissor,
                scissor_deducted=deduct_scissor,
                comb_deducted=0,
                status='success'
            )
            db.session.add(consumption)

        # 记录退款财务流水（退款金额减去现金抵扣）
        actual_refund = float(application.refund_amount) - cash_deduction
        financial = FinancialRecord(
            user_id=user.id,
            record_type='refund',
            amount=-actual_refund,
            description=f'退款扣回 (申请#{application.id})',
            payment_method='wechat',
            related_id=application.id,
            related_type='refund_application',
            hairs_changed=deduct_scissor,
            status='success'
        )
        db.session.add(financial)

        # 如果有现金抵扣，记录现金扣回流水
        if cash_deduction > 0:
            cash_record = FinancialRecord(
                user_id=user.id,
                record_type='cash_consumption',
                amount=-cash_deduction,
                description=f'退款发丝不足抵扣 (缺{hairs_to_deduct - scissor_hairs}发丝)',
                payment_method='balance',
                related_id=application.id,
                related_type='refund_application',
                hairs_changed=hairs_to_deduct - scissor_hairs,
                status='success'
            )
            db.session.add(cash_record)

        db.session.commit()

        refund_logger.info(
            f"[REFUND] 发丝扣回完成: user_id={user.id}, "
            f"scissor={deduct_scissor}, cash_deduction=¥{cash_deduction}"
        )
