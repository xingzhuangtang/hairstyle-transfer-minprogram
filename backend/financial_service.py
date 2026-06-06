#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务流水记录服务
统一记录所有与人民币相关的资金流水
"""

from models import db, FinancialRecord


class FinancialService:
    """财务流水记录服务"""

    @staticmethod
    def record_recharge(user_id, amount, payment_method, scissor_hairs, comb_hairs, order_no, status='success'):
        """记录充值流水"""
        total_hairs = scissor_hairs + comb_hairs
        record = FinancialRecord(
            user_id=user_id,
            record_type='recharge',
            amount=amount,
            description=f'充值 ¥{amount}，获得 {total_hairs} 发丝（剪刀:{scissor_hairs} 梳子:{comb_hairs}）',
            payment_method=payment_method,
            related_type='recharge_record',
            hairs_changed=total_hairs,
            status=status
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def record_member_purchase(user_id, amount, payment_method, bonus_hairs, order_no, status='success'):
        """记录会员购买/续费流水"""
        record = FinancialRecord(
            user_id=user_id,
            record_type='member_purchase',
            amount=amount,
            description=f'购买 VIP 会员 ¥{amount}' + (f'，赠送 {bonus_hairs} 发丝' if bonus_hairs else ''),
            payment_method=payment_method,
            related_type='member_order',
            hairs_changed=bonus_hairs if bonus_hairs else 0,
            status=status
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def record_refund(user_id, refund_amount, refund_type, related_id, status='success'):
        """记录退款流水"""
        refund_type_text = '充值退款' if refund_type == 'recharge' else '会员退款'
        record = FinancialRecord(
            user_id=user_id,
            record_type='refund',
            amount=-refund_amount,  # 负数表示支出（对用户而言是退回）
            description=f'{refund_type_text} -¥{refund_amount}（原路退回）',
            payment_method=None,
            related_type='refund_application',
            related_id=related_id,
            hairs_changed=None,
            status=status
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def record_commission(user_id, amount, referee_id, referral_id, status='paid'):
        """记录推广佣金流水"""
        record = FinancialRecord(
            user_id=user_id,
            record_type='commission',
            amount=amount,
            description=f'推广好友 #{referee_id} 获得佣金 ¥{amount}',
            payment_method=None,
            related_type='commission_record',
            related_id=referral_id,
            hairs_changed=None,
            status=status
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def record_withdrawal(user_id, amount, withdrawal_id, status='pending'):
        """记录提现流水"""
        record = FinancialRecord(
            user_id=user_id,
            record_type='withdrawal',
            amount=-amount,  # 负数表示支出
            description=f'提现 ¥{amount} 到微信零钱',
            payment_method='wechat',
            related_type='cash_withdrawal_record',
            related_id=withdrawal_id,
            hairs_changed=None,
            status=status
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def record_cash_consumption(user_id, cash_spent, hairs_received, related_id=None):
        """记录本地消费（存钱罐余额购买发丝）流水"""
        record = FinancialRecord(
            user_id=user_id,
            record_type='cash_consumption',
            amount=-cash_spent,  # 负数表示支出
            description=f'存钱罐消费 ¥{cash_spent}，获得 {hairs_received} 发丝',
            payment_method=None,
            related_type='cash_consumption_record',
            related_id=related_id,
            hairs_changed=hairs_received,
            status='success'
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def get_user_financial_records(user_id, page=1, page_size=20, record_type=None):
        """获取用户财务流水记录（分页）"""
        query = FinancialRecord.query.filter_by(user_id=user_id)

        if record_type:
            query = query.filter_by(record_type=record_type)

        total = query.count()
        records = query.order_by(FinancialRecord.created_at.desc())\
            .offset((page - 1) * page_size).limit(page_size).all()

        return {
            'records': [r.to_dict() for r in records],
            'total': total,
            'page': page,
            'page_size': page_size
        }
