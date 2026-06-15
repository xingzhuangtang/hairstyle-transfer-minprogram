#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动补单脚本 - 修复支付成功但余额未更新的订单

使用方法:
    cd backend
    python manual_fix_recharge.py --phone 15001190323 [--dry-run]
"""

import argparse
import sys
from datetime import datetime

from app import app
from models import db, User, RechargeRecord
from payment_service import PaymentService


def fix_recharge(phone, dry_run=True):
    """修复指定手机号的 pending 充值订单"""
    with app.app_context():
        # 查找用户
        user = User.query.filter_by(phone=phone).first()
        if not user:
            print(f"❌ 用户不存在: {phone}")
            return False

        print(f"📱 用户信息:")
        print(f"   ID: {user.id}")
        print(f"   手机: {user.phone}")
        print(f"   当前余额: scissor={user.scissor_hairs}, comb={user.comb_hairs}")

        # 查找 pending 订单
        pending_orders = RechargeRecord.query.filter_by(
            user_id=user.id,
            payment_status='pending'
        ).order_by(RechargeRecord.created_at.desc()).all()

        if not pending_orders:
            print(f"✅ 没有 pending 状态的充值订单")
            return True

        print(f"\n📋 找到 {len(pending_orders)} 个 pending 订单:")
        for order in pending_orders:
            print(f"   - {order.order_no}: {order.amount}元, "
                  f"scissor={order.scissor_hairs}, comb={order.comb_hairs}, "
                  f"创建时间={order.created_at}")

        if dry_run:
            print(f"\n⚠️  Dry run 模式，未实际修复。去掉 --dry-run 参数执行修复。")
            return True

        # 执行修复
        payment_service = PaymentService()
        fixed_count = 0

        for order in pending_orders:
            print(f"\n🔧 处理订单: {order.order_no}")
            result = payment_service.process_recharge_success(
                order_no=order.order_no,
                transaction_id=f"MANUAL_FIX_{order.order_no}_{int(datetime.now().timestamp())}"
            )

            if result['success']:
                print(f"✅ 修复成功: 增加 scissor={result.get('scissor_hairs', 0)}, "
                      f"comb={result.get('comb_hairs', 0)}")
                fixed_count += 1
            else:
                print(f"❌ 修复失败: {result.get('error', '未知错误')}")

        # 显示修复后的余额
        db.session.refresh(user)
        print(f"\n📊 修复完成:")
        print(f"   修复订单数: {fixed_count}/{len(pending_orders)}")
        print(f"   修复后余额: scissor={user.scissor_hairs}, comb={user.comb_hairs}")

        return fixed_count > 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='手动补单脚本')
    parser.add_argument('--phone', required=True, help='用户手机号')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='预览模式，不实际修复（默认）')
    parser.add_argument('--fix', action='store_true',
                        help='执行修复（覆盖 dry-run）')

    args = parser.parse_args()
    dry_run = not args.fix

    print(f"🔧 手动补单工具")
    print(f"   手机号: {args.phone}")
    print(f"   模式: {'预览' if dry_run else '执行修复'}")
    print(f"{'='*50}\n")

    success = fix_recharge(args.phone, dry_run=dry_run)
    sys.exit(0 if success else 1)
