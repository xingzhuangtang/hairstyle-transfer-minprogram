#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试推广佣金逻辑：
1. 被推广人每2次素描消费 → 推广人获得 ¥0.03
2. 封顶 99 次佣金发放
3. 非素描消费不触发佣金
4. 重复调用不会重复发放
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models import db, User, ReferralRelation, CommissionRecord, CashConsumptionRecord, FinancialRecord, ConsumptionRecord
from referral_service import ReferralService
from datetime import datetime, timedelta
from decimal import Decimal
import uuid


def test_referral_commission():
    app.app_context().push()
    referral_service = ReferralService()

    print("=" * 60)
    print("测试1: 基础佣金发放流程")
    print("=" * 60)

    # 创建推广人和被推广人（使用随机手机号避免冲突）
    referrer = User(
        openid=f"test_referrer_{uuid.uuid4().hex[:8]}",
        phone=f"138{uuid.uuid4().hex[:9]}",
        nickname="推广人"
    )
    referee = User(
        openid=f"test_referee_{uuid.uuid4().hex[:8]}",
        phone=f"139{uuid.uuid4().hex[:9]}",
        nickname="被推广人"
    )
    db.session.add_all([referrer, referee])
    db.session.flush()

    # 建立推广关系（设置为25小时前，跳过冷却期）
    relation = ReferralRelation(
        referrer_id=referrer.id,
        referee_id=referee.id,
        scene="test_scene_1",
        status='active',
        created_at=datetime.now() - timedelta(hours=25)  # 25小时前，已过冷却期
    )
    db.session.add(relation)
    db.session.commit()

    print(f"推广人 ID: {referrer.id}, 初始余额: {referrer.cash_balance}")
    print(f"被推广人 ID: {referee.id}")

    # 被推广人第1次素描消费 → 不应发放佣金
    create_sketch_consumption(referee.id)
    referral_service.check_and_grant_commission(referee.id)
    db.session.refresh(referrer)
    print(f"第1次素描消费后，推广人余额: {referrer.cash_balance} (预期: 0)")
    assert referrer.cash_balance == Decimal('0'), "第1次消费不应发放佣金"

    # 被推广人第2次素描消费 → 应发放 ¥0.03
    create_sketch_consumption(referee.id)
    referral_service.check_and_grant_commission(referee.id)
    db.session.refresh(referrer)
    print(f"第2次素描消费后，推广人余额: {referrer.cash_balance} (预期: 0.03)")
    assert referrer.cash_balance == Decimal('0.03'), "第2次消费应发放 ¥0.03"

    commission_count = CommissionRecord.query.filter_by(referral_id=relation.id).count()
    assert commission_count == 1, f"应有1条佣金记录，实际 {commission_count}"
    print(f"✅ 第2次消费触发佣金，佣金记录数: {commission_count}")

    print("\n" + "=" * 60)
    print("测试2: 第3次消费不触发，第4次触发")
    print("=" * 60)

    # 第3次 → 不触发
    create_sketch_consumption(referee.id)
    referral_service.check_and_grant_commission(referee.id)
    db.session.refresh(referrer)
    print(f"第3次素描消费后，推广人余额: {referrer.cash_balance} (预期: 0.03)")
    assert referrer.cash_balance == Decimal('0.03'), "第3次消费不应发放佣金"

    # 第4次 → 触发
    create_sketch_consumption(referee.id)
    referral_service.check_and_grant_commission(referee.id)
    db.session.refresh(referrer)
    print(f"第4次素描消费后，推广人余额: {referrer.cash_balance} (预期: 0.06)")
    assert referrer.cash_balance == Decimal('0.06'), "第4次消费应再发放 ¥0.03"

    commission_count = CommissionRecord.query.filter_by(referral_id=relation.id).count()
    assert commission_count == 2, f"应有2条佣金记录，实际 {commission_count}"
    print(f"✅ 第4次消费再次触发佣金，佣金记录数: {commission_count}")

    print("\n" + "=" * 60)
    print("测试3: 非素描消费不触发佣金")
    print("=" * 60)

    # 非素描消费（hair_segment）
    create_non_sketch_consumption(referee.id)
    create_non_sketch_consumption(referee.id)
    referral_service.check_and_grant_commission(referee.id)
    db.session.refresh(referrer)
    print(f"2次非素描消费后，推广人余额: {referrer.cash_balance} (预期: 0.06)")
    assert referrer.cash_balance == Decimal('0.06'), "非素描消费不应触发佣金"
    print("✅ 非素描消费不触发佣金")

    print("\n" + "=" * 60)
    print("测试4: 重复调用不会重复发放")
    print("=" * 60)

    # 连续调用5次，不应重复发放
    for i in range(5):
        referral_service.check_and_grant_commission(referee.id)
    db.session.refresh(referrer)
    print(f"重复调用5次后，推广人余额: {referrer.cash_balance} (预期: 0.06)")
    assert referrer.cash_balance == Decimal('0.06'), "重复调用不应重复发放"
    print("✅ 重复调用安全，无重复发放")

    print("\n" + "=" * 60)
    print("测试5: 99次佣金封顶")
    print("=" * 60)

    # 快速模拟到 99 次佣金
    # 当前已有 2 次佣金，还需要 97 次
    # 每次需要2次素描消费
    remaining_commissions = 99 - 2
    print(f"当前已发佣金: 2 次，还需: {remaining_commissions} 次")

    # 批量创建消费记录（模拟）
    for i in range(remaining_commissions):
        create_sketch_consumption(referee.id)
        create_sketch_consumption(referee.id)
        referral_service.check_and_grant_commission(referee.id)

    db.session.refresh(referrer)
    commission_count = CommissionRecord.query.filter_by(referral_id=relation.id).count()
    expected_balance = Decimal('0.03') * 99

    print(f"99次佣金后，推广人余额: {referrer.cash_balance} (预期: {expected_balance})")
    print(f"佣金记录数: {commission_count} (预期: 99)")
    assert commission_count == 99, f"应有99条佣金记录，实际 {commission_count}"
    assert referrer.cash_balance == expected_balance, f"余额应为 {expected_balance}，实际 {referrer.cash_balance}"
    print("✅ 99次佣金发放完成")

    # 再消费2次，不应再发放
    create_sketch_consumption(referee.id)
    create_sketch_consumption(referee.id)
    referral_service.check_and_grant_commission(referee.id)
    db.session.refresh(referrer)
    print(f"封顶后再消费2次，推广人余额: {referrer.cash_balance} (预期: {expected_balance})")
    assert referrer.cash_balance == expected_balance, "封顶后不应再发放佣金"
    print("✅ 99次封顶生效")

    print("\n" + "=" * 60)
    print("测试7: 24小时冷却期防刷")
    print("=" * 60)

    # 创建新推广人和被推广人
    referrer2 = User(
        openid=f"test_referrer2_{uuid.uuid4().hex[:8]}",
        phone=f"138{uuid.uuid4().hex[:9]}",
        nickname="推广人2"
    )
    referee2 = User(
        openid=f"test_referee2_{uuid.uuid4().hex[:8]}",
        phone=f"139{uuid.uuid4().hex[:9]}",
        nickname="被推广人2"
    )
    db.session.add_all([referrer2, referee2])
    db.session.flush()

    # 建立推广关系（刚刚创建，在冷却期内）
    relation2 = ReferralRelation(
        referrer_id=referrer2.id,
        referee_id=referee2.id,
        scene="test_scene_cooldown",
        status='active',
        created_at=datetime.now()  # 刚刚创建
    )
    db.session.add(relation2)
    db.session.commit()

    # 在冷却期内完成2次素描消费 → 不应发放佣金
    create_sketch_consumption(referee2.id)
    create_sketch_consumption(referee2.id)
    referral_service.check_and_grant_commission(referee2.id)
    db.session.refresh(referrer2)

    print(f"冷却期内2次素描消费后，推广人余额: {referrer2.cash_balance} (预期: 0)")
    assert referrer2.cash_balance == Decimal('0'), "冷却期内不应发放佣金"
    print("✅ 24小时冷却期生效，注册后立即消费不触发佣金")

    # 清理
    db.session.delete(relation2)
    ConsumptionRecord.query.filter_by(user_id=referee2.id).delete(synchronize_session=False)
    db.session.delete(referee2)
    db.session.delete(referrer2)
    db.session.commit()
    print("✅ 冷却期测试数据已清理")

    print("\n" + "=" * 60)
    print("测试8: 佣金明细来源追溯")
    print("=" * 60)

    # 验证佣金历史包含来源信息
    stats = referral_service.get_piggy_bank_stats(referrer.id)
    assert 'commission_history' in stats, "应包含佣金明细"
    assert len(stats['commission_history']) == 99, f"应有99条佣金记录，实际 {len(stats['commission_history'])}"

    # 检查第一条记录的来源追溯信息
    first_commission = stats['commission_history'][0]
    assert 'referee_id' in first_commission, "应包含被推广人ID"
    assert 'referee_nickname' in first_commission, "应包含被推广人昵称"
    assert 'reason' in first_commission, "应包含佣金原因"
    assert 'amount' in first_commission, "应包含佣金金额"
    assert 'created_at' in first_commission, "应包含创建时间"

    print(f"佣金明细第一条：金额={first_commission['amount']}, "
          f"来源用户={first_commission['referee_nickname']}, "
          f"原因={first_commission['reason']}")
    print("✅ 佣金来源追溯信息完整")

    print("\n" + "=" * 60)
    print("所有测试通过！✅")
    print("=" * 60)

    # 清理测试数据（按 FK 依赖顺序）
    FinancialRecord.query.filter_by(user_id=referrer.id).delete(synchronize_session=False)
    FinancialRecord.query.filter_by(user_id=referee.id).delete(synchronize_session=False)
    CommissionRecord.query.filter_by(referral_id=relation.id).delete(synchronize_session=False)
    db.session.delete(relation)
    ConsumptionRecord.query.filter_by(user_id=referee.id).delete(synchronize_session=False)
    db.session.delete(referee)
    db.session.delete(referrer)
    db.session.commit()
    print("✅ 测试数据已清理")


def create_sketch_consumption(user_id):
    """创建一条素描消费记录"""
    record = ConsumptionRecord(
        user_id=user_id,
        task_id=str(uuid.uuid4()),
        service_type='sketch',
        hairs_consumed=10,
        scissor_deducted=10,
        comb_deducted=0,
        status='success',
        created_at=datetime.now()
    )
    db.session.add(record)
    db.session.commit()


def create_non_sketch_consumption(user_id):
    """创建一条非素描消费记录"""
    record = ConsumptionRecord(
        user_id=user_id,
        task_id=str(uuid.uuid4()),
        service_type='hair_segment',
        hairs_consumed=10,
        scissor_deducted=10,
        comb_deducted=0,
        status='success',
        created_at=datetime.now()
    )
    db.session.add(record)
    db.session.commit()


if __name__ == '__main__':
    test_referral_commission()
