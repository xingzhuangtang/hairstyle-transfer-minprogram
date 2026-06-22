#!/usr/bin/env python3
"""
退款流程测试
测试充值退款的完整流程，包括正常流程和安全性测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import User, RechargeRecord
from payment_service import PaymentService

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_normal_refund():
    """测试 1: 正常退款流程"""
    print_section("测试 1: 正常退款流程")
    
    with app.app_context():
        # 创建测试用户
        user = User.query.filter_by(phone='13800000001').first()
        if not user:
            user = User(
                phone='13800000001',
                openid='test_refund_user_openid',
                user_type='registered',
                member_level='normal',
                scissor_hairs=0,
                comb_hairs=0
            )
            db.session.add(user)
            db.session.commit()
        
        initial_scissor = user.scissor_hairs
        initial_comb = user.comb_hairs
        print(f"测试用户: id={user.id}, phone={user.phone}")
        print(f"初始余额: scissor={initial_scissor}, comb={initial_comb}")
        
        # 步骤 1: 模拟充值成功
        print(f"\n--- 步骤 1: 模拟充值 20 元 ---")
        ps = PaymentService()
        result = ps.create_recharge_order(user.id, 20, 'wechat', user=user)
        order_no = result['order_no']
        print(f"创建订单: {order_no}")
        
        # 模拟充值成功回调
        process_result = ps.process_recharge_success(order_no=order_no, transaction_id='TEST_TXN_001')
        print(f"充值处理结果: {process_result}")
        
        # 刷新用户数据
        db.session.refresh(user)
        after_recharge_scissor = user.scissor_hairs
        after_recharge_comb = user.comb_hairs
        print(f"充值后余额: scissor={after_recharge_scissor}, comb={after_recharge_comb}")
        
        # 步骤 2: 模拟全额退款
        print(f"\n--- 步骤 2: 模拟全额退款 20 元 ---")
        refund_result = ps.process_refund_success(
            order_no=order_no,
            refund_no='TEST_RF_001',
            refund_amount=20.0
        )
        print(f"退款处理结果: {refund_result}")
        
        # 刷新用户数据
        db.session.refresh(user)
        after_refund_scissor = user.scissor_hairs
        after_refund_comb = user.comb_hairs
        print(f"退款后余额: scissor={after_refund_scissor}, comb={after_refund_comb}")
        
        # 验证
        assert after_refund_scissor == initial_scissor, f"全额退款后 scissor 应恢复为 {initial_scissor}，实际 {after_refund_scissor}"
        assert after_refund_comb == initial_comb, f"全额退款后 comb 应恢复为 {initial_comb}，实际 {after_refund_comb}"
        print(f"✅ 全额退款测试通过：余额已恢复到初始状态")
        
        # 检查订单状态
        order = RechargeRecord.query.filter_by(order_no=order_no).first()
        assert order.payment_status == 'refunded', f"订单状态应为 refunded，实际 {order.payment_status}"
        assert order.refund_no == 'TEST_RF_001', f"退款单号应为 TEST_RF_001，实际 {order.refund_no}"
        assert float(order.refund_amount) == 20.0, f"退款金额应为 20.0，实际 {order.refund_amount}"
        print(f"✅ 订单状态验证通过")
        
        return True

def test_partial_refund():
    """测试 2: 部分退款"""
    print_section("测试 2: 部分退款（50% 退款）")
    
    with app.app_context():
        # 创建测试用户
        user = User.query.filter_by(phone='13800000002').first()
        if not user:
            user = User(
                phone='13800000002',
                openid='test_partial_refund_openid',
                user_type='registered',
                member_level='normal',
                scissor_hairs=100,
                comb_hairs=50
            )
            db.session.add(user)
            db.session.commit()
        
        initial_scissor = user.scissor_hairs
        initial_comb = user.comb_hairs
        print(f"测试用户: id={user.id}")
        print(f"初始余额: scissor={initial_scissor}, comb={initial_comb}")
        
        # 充值 50 元 (VIP 规则: 5000 scissor + 588 comb)
        ps = PaymentService()
        result = ps.create_recharge_order(user.id, 50, 'wechat', user=user)
        order_no = result['order_no']
        print(f"创建订单: {order_no}, 充值 50 元")
        
        process_result = ps.process_recharge_success(order_no=order_no, transaction_id='TEST_TXN_002')
        print(f"充值处理结果: {process_result}")
        
        db.session.refresh(user)
        after_recharge_scissor = user.scissor_hairs
        after_recharge_comb = user.comb_hairs
        print(f"充值后余额: scissor={after_recharge_scissor}, comb={after_recharge_comb}")
        
        # 部分退款 25 元（50%）
        print(f"\n--- 部分退款 25 元（50%）---")
        refund_result = ps.process_refund_success(
            order_no=order_no,
            refund_no='TEST_RF_002',
            refund_amount=25.0
        )
        print(f"退款处理结果: {refund_result}")
        
        db.session.refresh(user)
        after_refund_scissor = user.scissor_hairs
        after_refund_comb = user.comb_hairs
        print(f"部分退款后余额: scissor={after_refund_scissor}, comb={after_refund_comb}")
        
        # 50% 退款应扣回一半发丝
        expected_deduct_scissor = int(process_result['scissor_hairs'] * 0.5)
        expected_deduct_comb = int(process_result['comb_hairs'] * 0.5)
        expected_scissor = after_recharge_scissor - expected_deduct_scissor
        expected_comb = after_recharge_comb - expected_deduct_comb
        
        assert after_refund_scissor == expected_scissor, f"部分退款后 scissor 应为 {expected_scissor}，实际 {after_refund_scissor}"
        assert after_refund_comb == expected_comb, f"部分退款后 comb 应为 {expected_comb}，实际 {after_refund_comb}"
        print(f"✅ 部分退款测试通过：扣回 scissor={expected_deduct_scissor}, comb={expected_deduct_comb}")
        
        return True

def test_double_refund():
    """测试 3: 重复退款攻击"""
    print_section("测试 3: 安全性 - 重复退款攻击")
    
    with app.app_context():
        # 创建测试用户
        user = User.query.filter_by(phone='13800000003').first()
        if not user:
            user = User(
                phone='13800000003',
                openid='test_double_refund_openid',
                user_type='registered',
                member_level='normal',
                scissor_hairs=100,
                comb_hairs=100
            )
            db.session.add(user)
            db.session.commit()
        
        before_scissor = user.scissor_hairs
        before_comb = user.comb_hairs
        print(f"测试用户: id={user.id}")
        print(f"初始余额: scissor={before_scissor}, comb={before_comb}")
        
        # 充值 10 元
        ps = PaymentService()
        result = ps.create_recharge_order(user.id, 10, 'wechat', user=user)
        order_no = result['order_no']
        
        ps.process_recharge_success(order_no=order_no, transaction_id='TEST_TXN_003')
        db.session.refresh(user)
        print(f"充值后余额: scissor={user.scissor_hairs}, comb={user.comb_hairs}")
        
        # 第一次退款
        print(f"\n--- 第一次退款 ---")
        refund1 = ps.process_refund_success(
            order_no=order_no,
            refund_no='TEST_RF_003A',
            refund_amount=10.0
        )
        print(f"第一次退款结果: {refund1}")
        
        db.session.refresh(user)
        after_first_refund = user.scissor_hairs
        print(f"第一次退款后: scissor={after_first_refund}")
        
        # 第二次退款（应该失败）
        print(f"\n--- 第二次退款（应该失败）---")
        refund2 = ps.process_refund_success(
            order_no=order_no,
            refund_no='TEST_RF_003B',
            refund_amount=10.0
        )
        print(f"第二次退款结果: {refund2}")
        
        # 验证第二次退款失败
        assert not refund2['success'], "第二次退款应该失败"
        assert '已退款' in refund2['error'] or 'refunded' in refund2['error'], f"错误信息应包含已退款相关信息，实际: {refund2['error']}"
        print(f"✅ 重复退款攻击防御测试通过：第二次退款被拒绝")
        
        # 验证余额没有进一步减少
        db.session.refresh(user)
        assert user.scissor_hairs == after_first_refund, "余额不应在第二次退款时继续减少"
        print(f"✅ 余额保护测试通过：scissor={user.scissor_hairs}")
        
        return True

def test_refund_pending_order():
    """测试 4: 退款未支付订单"""
    print_section("测试 4: 安全性 - 退款未支付订单")
    
    with app.app_context():
        user = User.query.filter_by(phone='13800000004').first()
        if not user:
            user = User(
                phone='13800000004',
                openid='test_pending_refund_openid',
                user_type='registered',
                member_level='normal',
                scissor_hairs=100,
                comb_hairs=100
            )
            db.session.add(user)
            db.session.commit()
        
        before_scissor = user.scissor_hairs
        
        # 创建订单但不支付
        ps = PaymentService()
        result = ps.create_recharge_order(user.id, 10, 'wechat', user=user)
        order_no = result['order_no']
        print(f"创建未支付订单: {order_no}")
        
        # 尝试退款
        print(f"\n--- 尝试退款未支付订单 ---")
        refund = ps.process_refund_success(
            order_no=order_no,
            refund_no='TEST_RF_004',
            refund_amount=10.0
        )
        print(f"退款结果: {refund}")
        
        assert not refund['success'], "退款未支付订单应该失败"
        print(f"✅ 未支付订单退款防御测试通过")
        
        # 验证余额未变化
        db.session.refresh(user)
        assert user.scissor_hairs == before_scissor, "余额不应变化"
        print(f"✅ 余额保护测试通过")
        
        return True

def test_refund_nonexistent_order():
    """测试 5: 退款不存在的订单"""
    print_section("测试 5: 安全性 - 退款不存在的订单")
    
    with app.app_context():
        ps = PaymentService()
        
        refund = ps.process_refund_success(
            order_no='NONEXISTENT_ORDER_999',
            refund_no='TEST_RF_005',
            refund_amount=10.0
        )
        print(f"退款结果: {refund}")
        
        assert not refund['success'], "退款不存在的订单应该失败"
        assert '订单不存在' in refund['error'], f"错误信息应包含'订单不存在'，实际: {refund['error']}"
        print(f"✅ 不存在订单退款防御测试通过")
        
        return True

def test_refund_more_than_paid():
    """测试 6: 退款金额超过支付金额"""
    print_section("测试 6: 安全性 - 退款金额超过支付金额")
    
    with app.app_context():
        user = User.query.filter_by(phone='13800000006').first()
        if not user:
            user = User(
                phone='13800000006',
                openid='test_over_refund_openid',
                user_type='registered',
                member_level='normal',
                scissor_hairs=100,
                comb_hairs=100
            )
            db.session.add(user)
            db.session.commit()
        
        before_scissor = user.scissor_hairs
        
        # 充值 10 元
        ps = PaymentService()
        result = ps.create_recharge_order(user.id, 10, 'wechat', user=user)
        order_no = result['order_no']
        
        ps.process_recharge_success(order_no=order_no, transaction_id='TEST_TXN_006')
        db.session.refresh(user)
        print(f"充值 10 元后余额: scissor={user.scissor_hairs}")
        
        # 尝试退款 20 元（超过支付金额）
        print(f"\n--- 尝试退款 20 元（超过支付的 10 元）---")
        refund = ps.process_refund_success(
            order_no=order_no,
            refund_no='TEST_RF_006',
            refund_amount=20.0
        )
        print(f"退款结果: {refund}")
        
        # 即使退款金额超过支付金额，系统也应该按比例扣回，但不应该导致负数余额
        db.session.refresh(user)
        assert user.scissor_hairs >= 0, f"余额不应为负数，实际: {user.scissor_hairs}"
        print(f"✅ 超额退款保护测试通过：余额={user.scissor_hairs}（非负）")
        
        return True

def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("  充值退款功能测试套件")
    print("="*60)
    
    tests = [
        ("正常退款流程", test_normal_refund),
        ("部分退款流程", test_partial_refund),
        ("重复退款攻击防御", test_double_refund),
        ("未支付订单退款防御", test_refund_pending_order),
        ("不存在订单退款防御", test_refund_nonexistent_order),
        ("超额退款保护", test_refund_more_than_paid),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
            import traceback
            traceback.print_exc()
    
    # 汇总
    print(f"\n{'='*60}")
    print("  测试汇总")
    print(f"{'='*60}")
    
    passed = sum(1 for _, s, _ in results if s)
    failed = sum(1 for _, s, _ in results if not s)
    
    for name, success, error in results:
        status = "✅ PASS" if success else f"❌ FAIL: {error}"
        print(f"  {status} - {name}")
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {len(results)} 总计")
    
    if failed == 0:
        print("\n🎉 所有测试通过！退款功能安全可靠。")
    else:
        print(f"\n⚠️  {failed} 个测试失败，请检查问题。")
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
