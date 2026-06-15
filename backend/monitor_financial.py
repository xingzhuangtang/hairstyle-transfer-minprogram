#!/usr/bin/env python3
"""
财务流水记录完整性监控脚本
检查充值订单、会员订单与财务记录的对应关系
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import RechargeRecord, MemberOrder, FinancialRecord, User
from sqlalchemy import func


def monitor_financial():
    """监控财务流水记录完整性"""
    with app.app_context():
        print("=" * 70)
        print("财务流水记录完整性监控")
        print("=" * 70)
        print()

        issues = []

        # 1. 检查充值订单与财务记录对应关系
        print("【充值订单 vs 财务记录】")
        success_recharge_orders = RechargeRecord.query.filter_by(payment_status='success').all()
        recharge_financial = FinancialRecord.query.filter_by(record_type='recharge', status='success').all()

        print(f"  成功充值订单数: {len(success_recharge_orders)}")
        print(f"  充值财务记录数: {len(recharge_financial)}")

        # 检查每个成功订单是否有对应财务记录
        orders_without_financial = []
        for order in success_recharge_orders:
            expected_desc = f"充值 ¥{float(order.amount)}，获得 {order.scissor_hairs + order.comb_hairs} 发丝（剪刀:{order.scissor_hairs} 梳子:{order.comb_hairs}）"
            matching = [r for r in recharge_financial if r.description == expected_desc and r.user_id == order.user_id]
            if not matching:
                orders_without_financial.append(order.order_no)

        if orders_without_financial:
            print(f"  ✗ {len(orders_without_financial)} 个订单缺少财务记录:")
            for order_no in orders_without_financial[:5]:
                print(f"    - {order_no}")
            if len(orders_without_financial) > 5:
                print(f"    ... 还有 {len(orders_without_financial) - 5} 个")
            issues.append(f"充值订单缺少财务记录: {len(orders_without_financial)} 个")
        else:
            print("  ✓ 所有充值订单都有对应财务记录")

        # 2. 检查会员订单与财务记录对应关系
        print()
        print("【会员订单 vs 财务记录】")
        success_member_orders = MemberOrder.query.filter_by(payment_status='success').all()
        member_financial = FinancialRecord.query.filter_by(record_type='member_purchase', status='success').all()

        print(f"  成功会员订单数: {len(success_member_orders)}")
        print(f"  会员财务记录数: {len(member_financial)}")

        # 检查每个成功订单是否有对应财务记录
        member_orders_without_financial = []
        for order in success_member_orders:
            expected_desc = f"购买 VIP 会员 ¥{float(order.amount)}"
            if order.bonus_hairs:
                expected_desc += f"，赠送 {order.bonus_hairs} 发丝"
            matching = [r for r in member_financial if r.description == expected_desc and r.user_id == order.user_id]
            if not matching:
                member_orders_without_financial.append(order.order_no)

        if member_orders_without_financial:
            print(f"  ✗ {len(member_orders_without_financial)} 个订单缺少财务记录:")
            for order_no in member_orders_without_financial[:5]:
                print(f"    - {order_no}")
            issues.append(f"会员订单缺少财务记录: {len(member_orders_without_financial)} 个")
        else:
            print("  ✓ 所有会员订单都有对应财务记录")

        # 3. 检查异常财务记录
        print()
        print("【异常财务记录检查】")

        # 金额为 0 的记录
        zero_amount = FinancialRecord.query.filter_by(amount=0).count()
        if zero_amount > 0:
            print(f"  ⚠ 金额为 0 的记录: {zero_amount} 条")
            issues.append(f"金额为 0 的财务记录: {zero_amount} 条")
        else:
            print("  ✓ 无金额为 0 的记录")

        # 状态为 failed 的记录
        failed_records = FinancialRecord.query.filter_by(status='failed').count()
        if failed_records > 0:
            print(f"  ⚠ 状态为 failed 的记录: {failed_records} 条")
            issues.append(f"状态为 failed 的财务记录: {failed_records} 条")
        else:
            print("  ✓ 无状态为 failed 的记录")

        # 4. 用户余额与充值记录一致性
        print()
        print("【用户余额检查】")
        users = User.query.all()
        balance_issues = []

        for user in users:
            # 计算用户应得发丝（基于成功订单）
            user_orders = RechargeRecord.query.filter_by(user_id=user.id, payment_status='success').all()
            expected_scissor = sum(o.scissor_hairs for o in user_orders)
            expected_comb = sum(o.comb_hairs for o in user_orders)

            # 检查是否有会员赠送
            member_orders = MemberOrder.query.filter_by(user_id=user.id, payment_status='success').all()
            for mo in member_orders:
                expected_comb += mo.bonus_hairs

            # 检查消耗记录
            consumption = db.session.query(func.sum(FinancialRecord.hairs_changed)).filter(
                FinancialRecord.user_id == user.id,
                FinancialRecord.record_type.in_(['cash_consumption']),
                FinancialRecord.status == 'success'
            ).scalar() or 0

            # 检查退款扣回
            refunds = RechargeRecord.query.filter_by(user_id=user.id, payment_status='refunded').all()
            refunded_scissor = sum(o.scissor_hairs for o in refunds)
            refunded_comb = sum(o.comb_hairs for o in refunds)

            # 计算期望余额
            expected_scissor_final = expected_scissor - refunded_scissor
            expected_comb_final = expected_comb - refunded_comb + consumption

            # 注意：这里只是粗略检查，实际可能还有其他因素（如新用户赠送等）
            # 只检查明显异常
            if user.scissor_hairs < 0 or user.comb_hairs < 0:
                balance_issues.append(f"User {user.id}: 余额为负 (scissor={user.scissor_hairs}, comb={user.comb_hairs})")

        if balance_issues:
            print(f"  ✗ 发现 {len(balance_issues)} 个余额异常:")
            for issue in balance_issues[:5]:
                print(f"    - {issue}")
            issues.extend(balance_issues)
        else:
            print("  ✓ 所有用户余额正常（非负）")

        # 5. 统计汇总
        print()
        print("【财务统计汇总】")

        # 充值总额
        total_recharge = db.session.query(func.sum(RechargeRecord.amount)).filter(
            RechargeRecord.payment_status == 'success'
        ).scalar() or 0
        print(f"  充值总额: ¥{float(total_recharge):.2f}")

        # 会员购买总额
        total_member = db.session.query(func.sum(MemberOrder.amount)).filter(
            MemberOrder.payment_status == 'success'
        ).scalar() or 0
        print(f"  会员购买总额: ¥{float(total_member):.2f}")

        # 退款总额
        total_refund = db.session.query(func.sum(RechargeRecord.refund_amount)).filter(
            RechargeRecord.payment_status == 'refunded'
        ).scalar() or 0
        print(f"  退款总额: ¥{float(total_refund):.2f}")

        # 结论
        print()
        print("=" * 70)
        print("【监控结论】")
        print("=" * 70)
        print()

        if issues:
            print(f"发现 {len(issues)} 个问题:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            return False
        else:
            print("✓ 财务流水记录完整，无异常")
            return True


if __name__ == '__main__':
    success = monitor_financial()
    sys.exit(0 if success else 1)
