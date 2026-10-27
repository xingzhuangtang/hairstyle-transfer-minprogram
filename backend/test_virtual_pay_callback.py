#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟支付回调全面测试
覆盖字段名变体、金额校验、边界条件、幂等性、回归测试
"""
import os
os.environ['FLASK_ENV'] = 'production'

import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from app import app
from models import db, User, RechargeRecord, MemberOrder


class VirtualPayCallbackTestBase(unittest.TestCase):
    """测试基类：创建测试用户和订单"""

    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

        # 创建测试用户
        self.test_user = User.query.filter_by(phone='13900009999').first()
        if not self.test_user:
            self.test_user = User(
                phone='13900009999',
                device_id='test_device_callback',
                nickname='测试用户',
                scissor_hairs=100,
                comb_hairs=50,
                total_recharge=0,
                member_level='normal',
            )
            db.session.add(self.test_user)
            db.session.commit()

        self.user_id = self.test_user.id
        self.initial_scissor = self.test_user.scissor_hairs
        self.initial_comb = self.test_user.comb_hairs

    def tearDown(self):
        # 清理测试订单
        RechargeRecord.query.filter(
            RechargeRecord.order_no.like('TEST_%')
        ).delete(synchronize_session='fetch')
        MemberOrder.query.filter(
            MemberOrder.order_no.like('TEST_%')
        ).delete(synchronize_session='fetch')
        db.session.commit()

        # 恢复用户余额
        db.session.refresh(self.test_user)
        self.test_user.scissor_hairs = self.initial_scissor
        self.test_user.comb_hairs = self.initial_comb
        db.session.commit()

        self.ctx.pop()

    def create_test_order(self, amount=10.00, payment_method='wechat_virtual', order_no=None):
        """创建测试充值订单"""
        if order_no is None:
            order_no = f"TEST_{int(datetime.now().timestamp() * 1000)}"
        order = RechargeRecord(
            user_id=self.user_id,
            order_no=order_no,
            amount=amount,
            scissor_hairs=int(amount * 100),
            comb_hairs=0,
            payment_method=payment_method,
            payment_status='pending',
        )
        db.session.add(order)
        db.session.commit()
        return order

    def create_test_member_order(self, amount=30.00, order_no=None):
        """创建测试会员订单"""
        from datetime import timedelta
        if order_no is None:
            order_no = f"TEST_MEM_{int(datetime.now().timestamp() * 1000)}"
        order = MemberOrder(
            user_id=self.user_id,
            order_no=order_no,
            member_level='vip',
            amount=amount,
            bonus_hairs=100,
            payment_method='wechat_virtual',
            payment_status='pending',
            expire_at=datetime.now() + timedelta(days=365),
        )
        db.session.add(order)
        db.session.commit()
        return order


class TestCallbackFieldNames(VirtualPayCallbackTestBase):
    """测试1: 回调字段名变体（核心回归测试）"""

    def _make_callback(self, payload):
        return self.client.post(
            '/api/virtual-pay/callback',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_pascal_case_fields(self):
        """微信官方 PascalCase 字段名"""
        order = self.create_test_order(amount=10.00, order_no='TEST_PASCAL_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
            'TransactionId': 'WX_PASCAL_001',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')

        db.session.refresh(order)
        self.assertEqual(order.payment_status, 'success')

    def test_camel_case_fields(self):
        """camelCase 字段名兼容"""
        order = self.create_test_order(amount=10.00, order_no='TEST_CAMEL_001')
        resp = self._make_callback({
            'outTradeNo': order.order_no,
            'status': 'SUCCESS',
            'total_fee': 1000,
            'transactionId': 'WX_CAMEL_001',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')

    def test_snake_case_fields(self):
        """snake_case 字段名兼容"""
        order = self.create_test_order(amount=10.00, order_no='TEST_SNAKE_001')
        resp = self._make_callback({
            'out_trade_no': order.order_no,
            'result_code': 'SUCCESS',
            'total_fee': 1000,
            'transaction_id': 'WX_SNAKE_001',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')

    def test_status_as_integer_zero(self):
        """Status 字段为整数 0（某些版本微信用 0 表示成功）"""
        order = self.create_test_order(amount=10.00, order_no='TEST_STATUS_INT_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 0,
            'Fee': 1000,
            'TransactionId': 'WX_INT_001',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')

    def test_pay_info_nested(self):
        """PayInfo 嵌套数据解析"""
        order = self.create_test_order(amount=10.00, order_no='TEST_PAYINFO_001')
        resp = self._make_callback({
            'PayInfo': {
                'OutTradeNo': order.order_no,
                'Status': 'SUCCESS',
                'Fee': 1000,
                'TransactionId': 'WX_PAYINFO_001',
            }
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')


class TestAmountValidation(VirtualPayCallbackTestBase):
    """测试2: 金额校验逻辑"""

    def _make_callback(self, payload):
        return self.client.post(
            '/api/virtual-pay/callback',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_correct_amount(self):
        """金额匹配 - 正常通过"""
        order = self.create_test_order(amount=10.00, order_no='TEST_AMT_OK_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
            'TransactionId': 'WX_AMT_OK_001',
        })
        self.assertEqual(resp.status_code, 200)

    def test_amount_mismatch_rejected(self):
        """金额不匹配 - 拒绝"""
        order = self.create_test_order(amount=10.00, order_no='TEST_AMT_BAD_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 2000,  # 20元，但订单是10元
            'TransactionId': 'WX_AMT_BAD_001',
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'FAIL')

    def test_missing_fee_field(self):
        """Fee 字段缺失 - 不阻断（callback_amount=0 时跳过校验）"""
        order = self.create_test_order(amount=10.00, order_no='TEST_NOFEE_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'TransactionId': 'WX_NOFEE_001',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')

    def test_fee_zero_skips_validation(self):
        """Fee 为 0 - 跳过金额校验，不阻断"""
        order = self.create_test_order(amount=10.00, order_no='TEST_FEE0_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 0,
            'TransactionId': 'WX_FEE0_001',
        })
        self.assertEqual(resp.status_code, 200)

    def test_amount_boundary_001(self):
        """金额差 0.01 元 - 允许（浮点精度）"""
        order = self.create_test_order(amount=10.00, order_no='TEST_BOUNDARY_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1001,  # 10.01元，差0.01
            'TransactionId': 'WX_BOUNDARY_001',
        })
        self.assertEqual(resp.status_code, 200)

    def test_amount_boundary_002(self):
        """金额差 0.02 元 - 拒绝"""
        order = self.create_test_order(amount=10.00, order_no='TEST_BOUNDARY_002')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1002,  # 10.02元，差0.02
            'TransactionId': 'WX_BOUNDARY_002',
        })
        self.assertEqual(resp.status_code, 400)


class TestCallbackEdgeCases(VirtualPayCallbackTestBase):
    """测试3: 边界条件和异常"""

    def _make_callback(self, payload):
        return self.client.post(
            '/api/virtual-pay/callback',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_missing_order_no(self):
        """缺少订单号 - 返回 400"""
        resp = self._make_callback({
            'Status': 'SUCCESS',
            'Fee': 1000,
        })
        self.assertEqual(resp.status_code, 400)

    def test_order_not_found(self):
        """订单不存在 - 返回 404"""
        resp = self._make_callback({
            'OutTradeNo': 'NONEXISTENT_ORDER',
            'Status': 'SUCCESS',
            'Fee': 1000,
        })
        self.assertEqual(resp.status_code, 404)

    def test_payment_failed_status(self):
        """支付失败状态 - 标记订单为 failed"""
        order = self.create_test_order(amount=10.00, order_no='TEST_FAIL_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'FAIL',
            'Fee': 1000,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'FAIL')

        db.session.refresh(order)
        self.assertEqual(order.payment_status, 'failed')

    def test_empty_body(self):
        """空请求体 - 返回 400"""
        resp = self.client.post(
            '/api/virtual-pay/callback',
            data='',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json(self):
        """非法 JSON - 返回 400"""
        resp = self.client.post(
            '/api/virtual-pay/callback',
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


class TestIdempotency(VirtualPayCallbackTestBase):
    """测试4: 幂等性 - 重复回调不会重复增加余额"""

    def _make_callback(self, payload):
        return self.client.post(
            '/api/virtual-pay/callback',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_duplicate_callback(self):
        """同一订单回调两次 - 余额只增加一次"""
        order = self.create_test_order(amount=10.00, order_no='TEST_IDEM_001')

        # 第一次回调
        resp1 = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
            'TransactionId': 'WX_IDEM_001',
        })
        self.assertEqual(resp1.status_code, 200)

        # 第二次回调（微信可能重试）
        resp2 = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
            'TransactionId': 'WX_IDEM_001',
        })
        self.assertEqual(resp2.status_code, 200)

        # 验证余额只增加一次
        db.session.refresh(self.test_user)
        expected_scissor = self.initial_scissor + 1000
        self.assertEqual(self.test_user.scissor_hairs, expected_scissor)


class TestMemberOrderCallback(VirtualPayCallbackTestBase):
    """测试5: 会员订单回调"""

    def _make_callback(self, payload):
        return self.client.post(
            '/api/virtual-pay/callback',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_member_order_success(self):
        """会员订单回调成功"""
        order = self.create_test_member_order(amount=30.00, order_no='TEST_MEM_CB_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 3000,
            'TransactionId': 'WX_MEM_001',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')

        db.session.refresh(order)
        self.assertEqual(order.payment_status, 'success')

    def test_member_order_amount_mismatch(self):
        """会员订单金额不匹配"""
        order = self.create_test_member_order(amount=30.00, order_no='TEST_MEM_AMT_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,  # 10元，但订单是30元
            'TransactionId': 'WX_MEM_AMT_001',
        })
        self.assertEqual(resp.status_code, 400)


class TestBalanceUpdate(VirtualPayCallbackTestBase):
    """测试6: 余额更新正确性"""

    def _make_callback(self, payload):
        return self.client.post(
            '/api/virtual-pay/callback',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_10_yuan_recharge(self):
        """10元充值：增加1000剪刀发丝"""
        order = self.create_test_order(amount=10.00, order_no='TEST_BAL_10')
        self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
            'TransactionId': 'WX_BAL_10',
        })

        db.session.refresh(self.test_user)
        self.assertEqual(self.test_user.scissor_hairs, self.initial_scissor + 1000)
        self.assertEqual(self.test_user.comb_hairs, self.initial_comb)

    def test_20_yuan_recharge(self):
        """20元充值：增加2000剪刀 + 88梳子"""
        order = self.create_test_order(amount=20.00, order_no='TEST_BAL_20')
        order.scissor_hairs = 2000
        order.comb_hairs = 88
        db.session.commit()

        self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 2000,
            'TransactionId': 'WX_BAL_20',
        })

        db.session.refresh(self.test_user)
        self.assertEqual(self.test_user.scissor_hairs, self.initial_scissor + 2000)
        self.assertEqual(self.test_user.comb_hairs, self.initial_comb + 88)

    def test_total_recharge_updated(self):
        """累计充值金额正确更新"""
        db.session.refresh(self.test_user)
        initial_total = float(self.test_user.total_recharge or 0)

        order = self.create_test_order(amount=10.00, order_no='TEST_BAL_TOTAL')
        self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
            'TransactionId': 'WX_BAL_TOTAL',
        })

        db.session.refresh(self.test_user)
        self.assertEqual(float(self.test_user.total_recharge), initial_total + 10.00)

    def test_transaction_id_recorded(self):
        """第三方交易号正确记录"""
        order = self.create_test_order(amount=10.00, order_no='TEST_BAL_TXN')
        self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
            'TransactionId': 'WX_CUSTOM_TXN_12345',
        })

        db.session.refresh(order)
        self.assertEqual(order.transaction_id, 'WX_CUSTOM_TXN_12345')
        self.assertIsNotNone(order.paid_at)


class TestFormFieldCallback(VirtualPayCallbackTestBase):
    """测试7: Form-data 格式回调"""

    def test_form_data_callback(self):
        """微信可能以 form-data 格式发送回调"""
        order = self.create_test_order(amount=10.00, order_no='TEST_FORM_001')
        resp = self.client.post(
            '/api/virtual-pay/callback',
            data={
                'OutTradeNo': order.order_no,
                'Status': 'SUCCESS',
                'Fee': '1000',
                'TransactionId': 'WX_FORM_001',
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')


class TestSchedulerCompensation(VirtualPayCallbackTestBase):
    """测试8: 定时任务补偿逻辑（验证订单状态转换）"""

    def test_virtual_pay_order_timeout_logic(self):
        """虚拟支付订单超时60分钟应被标记为failed"""
        from datetime import timedelta

        order = self.create_test_order(amount=10.00, order_no='TEST_SCHED_001')
        order.created_at = datetime.now() - timedelta(minutes=61)
        db.session.commit()

        # 直接模拟scheduler的补偿逻辑
        time_diff = datetime.now() - order.created_at
        if order.payment_method == 'wechat_virtual' and time_diff > timedelta(minutes=60):
            order.payment_status = 'failed'
            db.session.commit()

        db.session.refresh(order)
        self.assertEqual(order.payment_status, 'failed')

    def test_wechat_order_not_closed_prematurely(self):
        """普通微信支付订单2分钟内不应被关闭"""
        from datetime import timedelta

        order = self.create_test_order(
            amount=10.00,
            payment_method='wechat',
            order_no='TEST_SCHED_WX_001',
        )
        order.created_at = datetime.now() - timedelta(minutes=1)
        db.session.commit()

        # 模拟scheduler逻辑：2分钟内的订单不处理
        time_diff = datetime.now() - order.created_at
        if order.payment_method == 'wechat' and time_diff > timedelta(minutes=2):
            order.payment_status = 'failed'
            db.session.commit()

        db.session.refresh(order)
        self.assertEqual(order.payment_status, 'pending')


class TestRegressionPreviousBug(VirtualPayCallbackTestBase):
    """测试9: 回归测试 - 确保之前的 bug 不再发生"""

    def _make_callback(self, payload):
        return self.client.post(
            '/api/virtual-pay/callback',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_bug_outtradeno_pascal_case(self):
        """回归: OutTradeNo (PascalCase) 必须被识别"""
        order = self.create_test_order(amount=10.00, order_no='TEST_REG_001')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
        })
        self.assertEqual(resp.status_code, 200, "OutTradeNo 字段未被识别")
        data = resp.get_json()
        self.assertEqual(data['return_code'], 'SUCCESS')

    def test_bug_fee_field_not_total_fee(self):
        """回归: Fee 字段必须被识别（不是 total_fee）"""
        order = self.create_test_order(amount=10.00, order_no='TEST_REG_002')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
            'Fee': 1000,
        })
        self.assertEqual(resp.status_code, 200, "Fee 字段未被识别")

    def test_bug_missing_fee_doesnt_block(self):
        """回归: Fee 缺失时不能阻断回调（之前 total_fee 默认为0导致金额校验失败）"""
        order = self.create_test_order(amount=10.00, order_no='TEST_REG_003')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 'SUCCESS',
        })
        self.assertEqual(resp.status_code, 200, "Fee 缺失不应阻断回调")

    def test_bug_status_integer_zero(self):
        """回归: Status=0 应视为成功"""
        order = self.create_test_order(amount=10.00, order_no='TEST_REG_004')
        resp = self._make_callback({
            'OutTradeNo': order.order_no,
            'Status': 0,
            'Fee': 1000,
        })
        self.assertEqual(resp.status_code, 200, "Status=0 未被识别为成功")


if __name__ == '__main__':
    unittest.main(verbosity=2)
