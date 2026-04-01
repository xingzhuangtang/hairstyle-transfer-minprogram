#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付服务模块
支持微信支付、支付宝（禁用）
"""

import uuid
import time
from datetime import datetime
from flask import request
from models import db, User, RechargeRecord, MemberOrder
from config import get_config, NORMAL_RECHARGE_RULES, VIP_RECHARGE_RULES, MEMBER_CONFIG, NEW_USER_BONUS, AUTO_GIFT_CONFIG
from wechat_pay import WeChatPay
# 支付宝功能暂时注释（SDK结构需要适配）
# from alipay_client import AlipayClient
# 云闪付已删除


class PaymentService:
    """支付服务"""

    def __init__(self):
        self.config = get_config()
        self.normal_recharge_rules = NORMAL_RECHARGE_RULES
        self.vip_recharge_rules = VIP_RECHARGE_RULES
        self.member_config = MEMBER_CONFIG
        self.new_user_bonus = NEW_USER_BONUS
        self.auto_gift_config = AUTO_GIFT_CONFIG

    def get_recharge_rules(self, user_level):
        """根据用户类型获取充值规则"""
        if user_level == 'vip':
            return self.vip_recharge_rules
        return self.normal_recharge_rules
    
    def generate_order_no(self, prefix='RE'):
        """生成订单号"""
        timestamp = int(time.time())
        random_str = uuid.uuid4().hex[:8].upper()
        return f"{prefix}{timestamp}{random_str}"
    
    def create_recharge_order(self, user_id, amount, payment_method):
        """
        创建充值订单
        
        Args:
            user_id: 用户ID
            amount: 充值金额
            payment_method: 支付方式 (wechat, alipay, unionpay)
        
        Returns:
            dict: {success, order_no, error}
        """
        try:
            # 验证充值金额
            if amount not in self.normal_recharge_rules:
                return {
                    'success': False,
                    'error': '充值金额不合法'
                }

            # 获取充值规则
            rule = self.normal_recharge_rules[amount]
            
            # 生成订单号
            order_no = self.generate_order_no('RE')
            
            # 创建充值记录
            recharge_record = RechargeRecord(
                user_id=user_id,
                order_no=order_no,
                amount=amount,
                scissor_hairs=rule['scissor_hairs'],
                comb_hairs=rule['comb_hairs'],
                payment_method=payment_method,
                payment_status='pending'
            )
            
            db.session.add(recharge_record)
            db.session.commit()
            
            print(f"✅ 充值订单创建成功: order_no={order_no}, amount={amount}")
            
            return {
                'success': True,
                'order_no': order_no,
                'amount': amount,
                'scissor_hairs': rule['scissor_hairs'],
                'comb_hairs': rule['comb_hairs']
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 充值订单创建失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_member_order(self, user_id, payment_method):
        """
        创建会员订单
        
        Args:
            user_id: 用户ID
            payment_method: 支付方式 (wechat, alipay, unionpay)
        
        Returns:
            dict: {success, order_no, error}
        """
        try:
            # 获取会员配置
            config = self.member_config['vip']
            
            # 生成订单号
            order_no = self.generate_order_no('MB')
            
            # 计算到期时间
            expire_at = datetime.now() + timedelta(days=config['duration_days'])
            
            # 创建会员订单
            member_order = MemberOrder(
                user_id=user_id,
                order_no=order_no,
                member_level='vip',  # 会员等级
                amount=float(config['price']),  # 确保是浮点数
                bonus_hairs=int(config.get('purchase_bonus', {}).get('comb_hairs', 0)),  # 确保是整数
                payment_method=payment_method,  # 使用传入的支付方式
                payment_status='pending',
                expire_at=expire_at
            )
            
            db.session.add(member_order)
            db.session.commit()
            
            print(f"✅ 会员订单创建成功: order_no={order_no}, amount={config['price']}")
            
            return {
                'success': True,
                'order_no': order_no,
                'amount': config['price'],
                'bonus_hairs': int(config.get('purchase_bonus', {}).get('comb_hairs', 0)),
                'expire_at': expire_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 会员订单创建失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_recharge_success(self, order_no, transaction_id):
        """
        处理充值成功
        
        Args:
            order_no: 订单号
            transaction_id: 第三方交易号
        
        Returns:
            dict: {success, error}
        """
        try:
            # 查询订单
            order = RechargeRecord.query.filter_by(order_no=order_no).first()
            
            if not order:
                return {
                    'success': False,
                    'error': '订单不存在'
                }
            
            if order.payment_status == 'success':
                return {
                    'success': True,
                    'message': '订单已处理'
                }
            
            # 更新订单状态
            order.payment_status = 'success'
            order.transaction_id = transaction_id
            order.paid_at = datetime.now()
            
            # 增加用户头发丝
            user = User.query.get(order.user_id)
            user.scissor_hairs += order.scissor_hairs
            user.comb_hairs += order.comb_hairs
            user.total_recharge += order.amount
            
            db.session.commit()
            
            print(f"✅ 充值成功处理: order_no={order_no}, user_id={user.id}, "
                  f"scissor={order.scissor_hairs}, comb={order.comb_hairs}")
            
            return {
                'success': True,
                'user_id': user.id,
                'scissor_hairs': order.scissor_hairs,
                'comb_hairs': order.comb_hairs
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 充值成功处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_member_success(self, order_no, transaction_id):
        """
        处理会员购买成功
        
        Args:
            order_no: 订单号
            transaction_id: 第三方交易号
        
        Returns:
            dict: {success, error}
        """
        try:
            # 查询订单
            order = MemberOrder.query.filter_by(order_no=order_no).first()
            
            if not order:
                return {
                    'success': False,
                    'error': '订单不存在'
                }
            
            if order.payment_status == 'success':
                return {
                    'success': True,
                    'message': '订单已处理'
                }
            
            # 更新订单状态
            order.payment_status = 'success'
            order.transaction_id = transaction_id
            order.paid_at = datetime.now()
            
            # 更新用户会员信息
            user = User.query.get(order.user_id)
            
            # 如果之前是陪跑会员，延长到期时间
            if user.member_level == 'vip' and user.member_expire_at:
                if user.member_expire_at > datetime.now():
                    # 未过期，延长
                    user.member_expire_at = user.member_expire_at + timedelta(days=365)
                else:
                    # 已过期，重新计算
                    user.member_expire_at = order.expire_at
            else:
                # 新会员或普通会员
                user.member_expire_at = order.expire_at
            
            user.member_level = 'vip'
            
            # 赠送头发丝
            user.comb_hairs += order.bonus_hairs
            
            db.session.commit()
            
            print(f"✅ 会员购买成功处理: order_no={order_no}, user_id={user.id}, "
                  f"bonus_hairs={order.bonus_hairs}, expire_at={user.member_expire_at}")
            
            return {
                'success': True,
                'user_id': user.id,
                'bonus_hairs': order.bonus_hairs,
                'expire_at': user.member_expire_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 会员购买成功处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class WeChatPayService:
    """微信支付服务 (API v3)"""

    def __init__(self):
        """初始化微信支付服务"""
        from wechat_pay import WeChatPayClient
        self.wechat_pay = WeChatPayClient()

    def create_jsapi_order(self, order_no, amount, openid, body='发型迁移充值'):
        """
        创建 JSAPI 支付订单

        Args:
            order_no: 订单号
            amount: 金额（元）
            openid: 用户 openid
            body: 商品描述

        Returns:
            dict: {
                'success': bool,
                'prepay_id': str,
                'wxpay_params': dict,
                'error': str
            }
        """
        try:
            result = self.wechat_pay.create_jsapi_order(
                order_no=order_no,
                amount=amount,
                openid=openid,
                body=body
            )
            return result
        except Exception as e:
            print(f"❌ 创建微信支付订单失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def verify_callback(self, request_data):
        """
        验证支付回调

        Args:
            request_data: Flask request 对象或 dict

        Returns:
            dict: {
                'success': bool,
                'data': dict,
                'error': str
            }
        """
        try:
            result = self.wechat_pay.verify_callback(request_data)
            return result
        except Exception as e:
            print(f"❌ 验证微信支付回调失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class AlipayService:
    """支付宝支付服务 (H5手机网站支付)"""

    def __init__(self):
        """初始化支付宝支付服务"""
        # 支付宝功能暂时注释（SDK结构需要适配）
        # from alipay_client import AlipayClient
        # self.alipay = AlipayClient()
        pass

    def create_wap_pay_order(self, order_no, amount, subject='发型迁移充值'):
        """
        创建H5手机网站支付订单

        Args:
            order_no: 订单号
            amount: 金额（元）
            subject: 商品标题

        Returns:
            dict: {
                'success': bool,
                'pay_url': str,
                'error': str
            }
        """
        try:
            result = self.alipay.create_wap_pay_order(
                order_no=order_no,
                amount=amount,
                subject=subject
            )
            return result
        except Exception as e:
            print(f"❌ 创建支付宝支付订单失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def verify_callback(self, request_data):
        """
        验证支付回调

        Args:
            request_data: Flask request 对象或 dict

        Returns:
            dict: {
                'success': bool,
                'data': dict,
                'error': str
            }
        """
        try:
            result = self.alipay.verify_callback(request_data)
            return result
        except Exception as e:
            print(f"❌ 验证支付宝支付回调失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def query_order(self, order_no):
        """
        查询订单状态

        Args:
            order_no: 订单号

        Returns:
            dict: {
                'success': bool,
                'trade_status': str,
                'error': str
            }
        """
        try:
            result = self.alipay.query_order(order_no)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
