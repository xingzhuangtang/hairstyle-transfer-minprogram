#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务记录一致性检查与修复工具
检测并修复以下不一致：
1. 成功充值订单缺失 financial_records
2. 成功会员订单缺失 financial_records
3. 成功退款订单缺失 financial_records
"""

from app import app
from models import db, RechargeRecord, MemberOrder, FinancialRecord
from financial_service import FinancialService
from datetime import datetime


def check_and_fix_recharge_records():
    """检查并修复充值订单缺失的财务记录"""
    print("\n" + "=" * 60)
    print("检查充值订单财务记录...")
    print("=" * 60)

    with app.app_context():
        # 查找 payment_status='success' 但没有对应 financial_record 的充值订单
        missing = db.session.execute(db.text("""
            SELECT rr.id, rr.user_id, rr.amount, rr.scissor_hairs, rr.comb_hairs,
                   rr.payment_method, rr.order_no, rr.paid_at
            FROM recharge_records rr
            LEFT JOIN financial_records fr
                ON fr.related_type = 'recharge_record' AND fr.related_id = rr.id
            WHERE rr.payment_status = 'success'
              AND fr.id IS NULL
            ORDER BY rr.id
        """)).fetchall()

        if not missing:
            print("✅ 所有成功充值订单都有对应的财务记录")
            return 0

        print(f"⚠️  发现 {len(missing)} 笔缺失财务记录的充值订单:")

        fixed = 0
        for row in missing:
            order_id, user_id, amount, scissor, comb, method, order_no, paid_at = row
            total_hairs = scissor + comb
            print(f"  订单 #{order_id}: user_id={user_id}, ¥{amount}, "
                  f"发丝={total_hairs}(剪刀:{scissor} 梳子:{comb})")

            try:
                record = FinancialRecord(
                    user_id=user_id,
                    record_type='recharge',
                    amount=amount,
                    description=f'充值 ¥{amount}，获得 {total_hairs} 发丝（剪刀:{scissor} 梳子:{comb}）',
                    payment_method=method,
                    related_type='recharge_record',
                    related_id=order_id,
                    hairs_changed=total_hairs,
                    status='success',
                    created_at=paid_at or datetime.now()
                )
                db.session.add(record)
                db.session.flush()
                print(f"    ✅ 已补录财务记录 #{record.id}")
                fixed += 1
            except Exception as e:
                print(f"    ❌ 补录失败: {e}")

        db.session.commit()
        print(f"\n✅ 充值订单修复完成: {fixed}/{len(missing)} 条")
        return len(missing) - fixed


def check_and_fix_member_orders():
    """检查并修复会员订单缺失的财务记录"""
    print("\n" + "=" * 60)
    print("检查会员订单财务记录...")
    print("=" * 60)

    with app.app_context():
        missing = db.session.execute(db.text("""
            SELECT mo.id, mo.user_id, mo.amount, mo.bonus_hairs,
                   mo.payment_method, mo.order_no, mo.paid_at
            FROM member_orders mo
            LEFT JOIN financial_records fr
                ON fr.related_type = 'member_order' AND fr.related_id = mo.id
            WHERE mo.payment_status = 'success'
              AND fr.id IS NULL
            ORDER BY mo.id
        """)).fetchall()

        if not missing:
            print("✅ 所有成功会员订单都有对应的财务记录")
            return 0

        print(f"⚠️  发现 {len(missing)} 笔缺失财务记录的会员订单:")

        fixed = 0
        for row in missing:
            order_id, user_id, amount, bonus_hairs, method, order_no, paid_at = row
            print(f"  订单 #{order_id}: user_id={user_id}, ¥{amount}, "
                  f"赠送发丝={bonus_hairs}")

            try:
                record = FinancialRecord(
                    user_id=user_id,
                    record_type='member_purchase',
                    amount=amount,
                    description=f'购买 VIP 会员 ¥{amount}' + (f'，赠送 {bonus_hairs} 发丝' if bonus_hairs else ''),
                    payment_method=method,
                    related_type='member_order',
                    related_id=order_id,
                    hairs_changed=bonus_hairs if bonus_hairs else 0,
                    status='success',
                    created_at=paid_at or datetime.now()
                )
                db.session.add(record)
                db.session.flush()
                print(f"    ✅ 已补录财务记录 #{record.id}")
                fixed += 1
            except Exception as e:
                print(f"    ❌ 补录失败: {e}")

        db.session.commit()
        print(f"\n✅ 会员订单修复完成: {fixed}/{len(missing)} 条")
        return len(missing) - fixed


def check_and_fix_refund_records():
    """检查并修复退款订单缺失的财务记录"""
    print("\n" + "=" * 60)
    print("检查退款订单财务记录...")
    print("=" * 60)

    with app.app_context():
        missing = db.session.execute(db.text("""
            SELECT rr.id, rr.user_id, rr.refund_amount, rr.paid_at
            FROM recharge_records rr
            LEFT JOIN financial_records fr
                ON fr.related_type = 'refund_application' AND fr.related_id = rr.id
            WHERE rr.payment_status = 'refunded'
              AND rr.refund_amount IS NOT NULL
              AND rr.refund_amount > 0
              AND fr.id IS NULL
            ORDER BY rr.id
        """)).fetchall()

        if not missing:
            print("✅ 所有成功退款订单都有对应的财务记录")
            return 0

        print(f"⚠️  发现 {len(missing)} 笔缺失财务记录的退款订单:")

        fixed = 0
        for row in missing:
            order_id, user_id, refund_amount, paid_at = row
            print(f"  订单 #{order_id}: user_id={user_id}, 退款 ¥{refund_amount}")

            try:
                record = FinancialRecord(
                    user_id=user_id,
                    record_type='refund',
                    amount=-refund_amount,
                    description=f'充值退款 -¥{refund_amount}（原路退回）',
                    payment_method=None,
                    related_type='refund_application',
                    related_id=order_id,
                    hairs_changed=None,
                    status='success',
                    created_at=paid_at or datetime.now()
                )
                db.session.add(record)
                db.session.flush()
                print(f"    ✅ 已补录财务记录 #{record.id}")
                fixed += 1
            except Exception as e:
                print(f"    ❌ 补录失败: {e}")

        db.session.commit()
        print(f"\n✅ 退款订单修复完成: {fixed}/{len(missing)} 条")
        return len(missing) - fixed


def print_summary():
    """打印整体统计"""
    print("\n" + "=" * 60)
    print("财务记录统计")
    print("=" * 60)

    with app.app_context():
        stats = db.session.execute(db.text("""
            SELECT record_type, COUNT(*) as count, SUM(amount) as total
            FROM financial_records
            GROUP BY record_type
            ORDER BY record_type
        """)).fetchall()

        print(f"{'类型':<20} {'记录数':<10} {'总金额':<15}")
        print("-" * 45)
        type_names = {
            'recharge': '充值',
            'member_purchase': '会员购买',
            'refund': '退款',
            'commission': '推广佣金',
            'withdrawal': '提现',
            'cash_consumption': '存钱罐消费'
        }
        for row in stats:
            rtype, count, total = row
            name = type_names.get(rtype, rtype)
            total = total or 0
            print(f"{name:<18} {count:<12} ¥{float(total):<12.2f}")

        total_count = db.session.execute(db.text("SELECT COUNT(*) FROM financial_records")).fetchone()[0]
        print("-" * 45)
        print(f"{'总计':<18} {total_count:<12}")


if __name__ == '__main__':
    print("财务记录一致性检查与修复工具")
    print("=" * 60)

    errors = 0
    errors += check_and_fix_recharge_records()
    errors += check_and_fix_member_orders()
    errors += check_and_fix_refund_records()

    print_summary()

    if errors > 0:
        print(f"\n⚠️  检查完成，但有 {errors} 条记录修复失败，请查看上方日志")
    else:
        print(f"\n✅ 检查完成，所有不一致已修复")
