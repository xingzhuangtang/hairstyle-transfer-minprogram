#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信支付模块 - API v3
使用官方 wechatpayv3 SDK 实现微信小程序支付
支持 JSAPI 支付、支付回调验证
"""

import os
from wechatpayv3 import WeChatPayType, WeChatPay
from config import get_config


class WeChatPayClient:
    """微信支付 API v3 客户端"""

    def __init__(self):
        """初始化微信支付客户端"""
        self.config = get_config()
        self.appid = self.config.WECHAT_APP_ID
        self.mch_id = self.config.WECHAT_MCH_ID
        self.env = self.config.WECHAT_PAY_ENV
        self.notify_url = self.config.WECHAT_NOTIFY_URL

        # 初始化微信支付客户端
        try:
            self.client = WeChatPay(
                wechatpay_type=WeChatPayType.MINIPROG,  # 小程序支付
                mchid=self.mch_id,
                private_key=self._load_private_key(),  # 私钥字符串
                cert_serial_no=self._get_cert_serial_no(),  # 证书序列号
                appid=self.appid,
                apiv3_key=self.config.WECHAT_PAY_API_V3_KEY,  # API v3密钥
                cert_dir=self._get_cert_dir(),  # 证书目录
                notify_url=self.notify_url
            )
            print(f"✅ 微信支付客户端初始化成功 (环境: {self.env})")
        except Exception as e:
            print(f"❌ 微信支付客户端初始化失败: {e}")
            raise

    def _load_private_key(self):
        """加载商户私钥"""
        try:
            with open(self.config.WECHAT_PAY_KEY_PATH, 'r') as f:
                private_key = f.read()
            return private_key
        except FileNotFoundError:
            raise Exception(
                f"商户私钥文件不存在: {self.config.WECHAT_PAY_KEY_PATH}\n"
                f"请检查 WECHAT_PAY_KEY_PATH 配置"
            )
        except Exception as e:
            raise Exception(f"加载商户私钥失败: {e}")

    def _get_cert_dir(self):
        """获取证书目录"""
        # 从证书路径中提取目录
        cert_dir = os.path.dirname(self.config.WECHAT_PAY_CERT_PATH)
        return cert_dir

    def _get_cert_serial_no(self):
        """获取证书序列号"""
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend

            with open(self.config.WECHAT_PAY_CERT_PATH, 'rb') as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())

            serial_no = hex(cert.serial_number)[2:].upper()
            return serial_no
        except FileNotFoundError:
            raise Exception(
                f"商户证书文件不存在: {self.config.WECHAT_PAY_CERT_PATH}\n"
                f"请检查 WECHAT_PAY_CERT_PATH 配置"
            )
        except Exception as e:
            raise Exception(f"获取证书序列号失败: {e}")

    def create_jsapi_order(self, order_no, amount, openid, body='发型迁移充值'):
        """
        创建 JSAPI 支付订单 (API v3)

        Args:
            order_no: 订单号
            amount: 金额（元）
            openid: 用户 openid
            body: 商品描述

        Returns:
            dict: {
                'success': bool,
                'prepay_id': str,  # 预支付ID
                'wxpay_params': dict,  # 小程序支付参数
                'error': str
            }
        """
        try:
            # 转换为分
            total_fee = int(amount * 100)

            print(f"\n📱 创建微信支付订单...")
            print(f"   订单号: {order_no}")
            print(f"   金额: {amount} 元 ({total_fee} 分)")
            print(f"   OpenID: {openid}")

            # 调用统一下单API
            # SDK返回: (response_dict, status_code)
            response = self.client.pay(
                description=body,
                out_trade_no=order_no,
                amount={'total': total_fee, 'currency': 'CNY'},
                payer={'openid': openid}
            )

            # 处理返回值 (可能是tuple或dict)
            # wechatpayv3 SDK返回: (status_code, response_dict)
            if isinstance(response, tuple):
                status_code, result = response
            else:
                result = response
                status_code = 200

            print(f"   SDK返回: status={status_code}")
            print(f"   响应内容: {result}")

            # 检查响应
            if isinstance(result, dict) and result.get('prepay_id'):
                prepay_id = result['prepay_id']
                print(f"✅ 创建订单成功!")
                print(f"   PrepayID: {prepay_id}")

                # 生成小程序支付参数
                wxpay_params = self._generate_mini_pay_params(
                    prepay_id=prepay_id
                )

                print(f"   小程序支付参数已生成")

                return {
                    'success': True,
                    'prepay_id': prepay_id,
                    'wxpay_params': wxpay_params
                }
            else:
                error_msg = '创建订单失败：' + str(result) if result else '创建订单失败'
                print(f"❌ 创建订单失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            print(f"❌ 创建微信支付订单异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_mini_pay_params(self, prepay_id):
        """
        生成小程序支付参数

        Args:
            prepay_id: 预支付ID

        Returns:
            dict: 小程序支付所需参数
        """
        try:
            # 使用SDK的sign方法生成签名
            # 参数格式: [appId, timeStamp, nonceStr, package]
            import time
            import random
            import string

            timeStamp = str(int(time.time()))
            nonceStr = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            package = f"prepay_id={prepay_id}"

            # 调用SDK签名方法
            sign_str = self.client.sign([self.appid, timeStamp, nonceStr, package])

            return {
                'appId': self.appid,
                'timeStamp': timeStamp,
                'nonceStr': nonceStr,
                'package': package,
                'signType': 'RSA',
                'paySign': sign_str
            }
        except Exception as e:
            print(f"⚠️  生成支付参数失败: {e}")
            return {}

    def verify_callback(self, request_data):
        """
        验证支付回调 (API v3)

        Args:
            request_data: Flask request 对象或 dict

        Returns:
            dict: {
                'success': bool,
                'data': {
                    'order_no': str,
                    'transaction_id': str,
                    'amount': float
                },
                'error': str
            }
        """
        try:
            print(f"\n🔍 验证微信支付回调...")

            # 如果是 Flask request 对象，获取 JSON 数据
            if hasattr(request_data, 'get_json'):
                callback_data = request_data.get_json()
            else:
                callback_data = request_data

            # 使用SDK验证回调
            code, message, decrypted_data = self.client.callback(
                headers=request_data.headers if hasattr(request_data, 'headers') else {},
                body=callback_data
            )

            # 检查验证结果
            if code == 200 and decrypted_data:
                # 获取订单信息
                resource = decrypted_data.get('resource', {})
                cipher_text = resource.get('ciphertext', '')
                nonce = resource.get('nonce', '')
                associated_data = resource.get('associated_data', '')

                # 解密数据
                decrypted = self.client.decrypt(
                    ciphertext=cipher_text,
                    nonce=nonce,
                    associated_data=associated_data
                )

                # 解析JSON
                import json
                order_data = json.loads(decrypted)

                # 验证支付状态
                if order_data.get('trade_state') == 'SUCCESS':
                    print(f"✅ 支付成功!")
                    print(f"   订单号: {order_data.get('out_trade_no')}")
                    print(f"   微信订单号: {order_data.get('transaction_id')}")
                    print(f"   支付金额: {order_data.get('amount', {}).get('total', 0) / 100} 元")

                    return {
                        'success': True,
                        'data': {
                            'order_no': order_data.get('out_trade_no'),
                            'transaction_id': order_data.get('transaction_id'),
                            'amount': order_data.get('amount', {}).get('total', 0) / 100
                        }
                    }
                else:
                    error_msg = f"支付失败: {order_data.get('trade_state_desc', '未知错误')}"
                    print(f"❌ {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg
                    }
            else:
                error_msg = message or '签名验证失败'
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            print(f"❌ 验证微信支付回调异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def generate_response(self, success=True, message='OK'):
        """
        生成回调响应 (API v3 使用 JSON)

        Args:
            success: 是否成功
            message: 消息

        Returns:
            dict: 响应数据
        """
        return {
            'code': 'SUCCESS' if success else 'FAIL',
            'message': message
        }


# 测试代码
if __name__ == '__main__':
    import sys

    print("=" * 60)
    print("微信支付模块测试")
    print("=" * 60)

    try:
        # 测试初始化
        wechat_pay = WeChatPay()
        print(f"\n✅ 初始化成功")
        print(f"   AppID: {wechat_pay.appid}")
        print(f"   商户号: {wechat_pay.mch_id}")
        print(f"   环境: {wechat_pay.env}")

        # 测试签名（需要真实证书才能测试）
        print(f"\n⚠️  完整功能测试需要:")
        print(f"   1. 配置商户证书路径 ✓")
        print(f"   2. 配置 API v3 密钥 ✓")
        print(f"   3. 使用真实订单号测试")

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        print(f"\n请检查:")
        print(f"   1. .env 文件是否配置了微信支付参数")
        print(f"   2. 证书文件路径是否正确")
        print(f"   3. API v3 密钥是否设置")
        sys.exit(1)

    print("\n" + "=" * 60)
