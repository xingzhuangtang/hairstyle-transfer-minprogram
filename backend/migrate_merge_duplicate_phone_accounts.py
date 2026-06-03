#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性迁移脚本：合并纯手机号账号到微信+手机号账号

当同一个手机号同时存在于两个账号时：
  - 保留有 openid 的账号（微信+手机号）
  - 删除没有 openid 的账号（纯手机号）
  - 转移余额、记录等所有数据

幂等设计：可重复运行，无副作用
"""
import os
import sys

# 确保能导入项目模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ['FLASK_ENV'] = 'production'

from dotenv import load_dotenv
load_dotenv()

from app import app
from models import db, User
from models import ConsumptionRecord, HistoryRecord, RechargeRecord, MemberOrder
from models import Device, InsufficientReminder, GuestBonusRecord, UserBonusRecord
from models import MemberReminder, ReferralRelation, CommissionRecord
from models import CashWithdrawalRecord, CashConsumptionRecord, Message
from sqlalchemy import func


def find_duplicate_phones():
    """找出所有重复的手机号"""
    result = db.session.query(
        User.phone, func.count(User.id).label('cnt')
    ).filter(
        User.phone.isnot(None),
        User.phone != '',
        User.is_deactivated == False
    ).group_by(User.phone).having(func.count(User.id) > 1).all()
    return result


def merge_accounts(source_user, target_user):
    """将 source_user 的所有数据转移到 target_user"""
    print(f"   合并: user_id={source_user.id} (无openid) -> user_id={target_user.id} (有openid)")
    print(f"     source phone={source_user.phone}, target phone={target_user.phone}")

    # 1. 合并余额和累计数据
    target_user.scissor_hairs = (target_user.scissor_hairs or 0) + (source_user.scissor_hairs or 0)
    target_user.comb_hairs = (target_user.comb_hairs or 0) + (source_user.comb_hairs or 0)
    target_user.cash_balance = (target_user.cash_balance or 0) + (source_user.cash_balance or 0)
    target_user.total_referral_earnings = (target_user.total_referral_earnings or 0) + (source_user.total_referral_earnings or 0)
    target_user.total_recharge = (target_user.total_recharge or 0) + (source_user.total_recharge or 0)
    target_user.total_consumed_hairs = (target_user.total_consumed_hairs or 0) + (source_user.total_consumed_hairs or 0)

    print(f"     余额合并: scissor={target_user.scissor_hairs}, comb={target_user.comb_hairs}")

    # 2. 转移所有 user_id 外键记录
    transfers = [
        (ConsumptionRecord, 'consumption_records'),
        (HistoryRecord, 'history_records'),
        (RechargeRecord, 'recharge_records'),
        (MemberOrder, 'member_orders'),
        (Device, 'devices'),
        (InsufficientReminder, 'insufficient_reminders'),
        (GuestBonusRecord, 'guest_bonus_records'),
        (UserBonusRecord, 'user_bonus_records'),
        (MemberReminder, 'member_reminders'),
        (CashWithdrawalRecord, 'cash_withdrawal_records'),
        (CashConsumptionRecord, 'cash_consumption_records'),
        (Message, 'messages'),
    ]
    for model, name in transfers:
        count = model.query.filter_by(user_id=source_user.id).update({'user_id': target_user.id})
        if count > 0:
            print(f"     转移 {count} 条 {name}")

    # 3. 处理推广关系（referee_id 转移，referrer_id 删除）
    ref_relation_count = ReferralRelation.query.filter_by(referee_id=source_user.id).update({'referee_id': target_user.id})
    if ref_relation_count > 0:
        print(f"     转移 {ref_relation_count} 条推广关系(source为被推广人)")

    comm_referee_count = CommissionRecord.query.filter_by(referee_id=source_user.id).update({'referee_id': target_user.id})
    if comm_referee_count > 0:
        print(f"     转移 {comm_referee_count} 条佣金记录(source为被推广人)")

    # 删除 source 为推广人的关系和佣金记录
    referrer_count = ReferralRelation.query.filter_by(referrer_id=source_user.id).count()
    if referrer_count > 0:
        ReferralRelation.query.filter_by(referrer_id=source_user.id).delete()
        print(f"     删除 {referrer_count} 条推广关系(source为推广人)")

    comm_user_count = CommissionRecord.query.filter_by(user_id=source_user.id).count()
    if comm_user_count > 0:
        CommissionRecord.query.filter_by(user_id=source_user.id).delete()
        print(f"     删除 {comm_user_count} 条佣金记录(source为推广人)")

    # 4. 取消 source 的未完成游客续赠记录
    GuestBonusRecord.query.filter_by(
        user_id=source_user.id,
        bonus_type='auto_renew',
        is_completed=False
    ).update({'is_completed': True})

    # 5. 删除 source 用户
    db.session.delete(source_user)
    db.session.commit()
    print(f"     已删除源账号 user_id={source_user.id}")


def main():
    with app.app_context():
        print("\n" + "=" * 60)
        print("开始合并重复手机号账号")
        print("=" * 60 + "\n")

        duplicates = find_duplicate_phones()
        if not duplicates:
            print("未发现重复手机号账号，无需合并。")
            return

        print(f"发现 {len(duplicates)} 个重复手机号:\n")
        total_merged = 0

        for phone, count in duplicates:
            print(f"手机号: {phone} (共 {count} 个账号)")
            users = User.query.filter_by(phone=phone).all()

            # 分离有 openid 和无 openid 的账号
            with_openid = [u for u in users if u.openid is not None]
            without_openid = [u for u in users if u.openid is None]

            if len(with_openid) == 0:
                print(f"  跳过: 所有账号都无 openid (纯手机号账号，未被微信登录过)")
                continue

            if len(with_openid) > 1:
                print(f"  警告: {len(with_openid)} 个账号都有 openid，需要手动处理，跳过")
                continue

            target = with_openid[0]
            print(f"  目标账号: user_id={target.id}, openid={target.openid[:20]}...")

            for source in without_openid:
                merge_accounts(source, target)
                total_merged += 1

            print()

        print("=" * 60)
        print(f"合并完成！共合并 {total_merged} 个账号")
        print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
