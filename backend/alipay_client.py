#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付宝支付模块 - H5手机网站支付
支持支付宝手机网站支付、支付回调验证
"""

import time
import json
import requests
from alipay import AliPay
from config import get_config


class AlipayClient:
    """支付宝支付客户端"""

    def __init__(self):
        """初始化支付宝客户端"""
        self.config = get_config()
        self.app_id = self.config.ALIPAY_APP_ID
        self.notify_url = self.config.ALIPAY_NOTIFY_URL

        # 从文件加载密钥
        self.app_private_key = self._load_private_key()
        self.alipay_public_key = self._load_public_key()

        # 初始化支付宝SDK
        try:
            self.alipay = AliPay(
                appid=self.app_id,
                app_notify_url=self.notify_url,
                app_private_key_string=self.app_private_key,
                alipay_public_key_string=self.alipay_public_key,
                sign_type="RSA2",
                debug=False,  # 生产环境设为False
            )
            print(f"✅ 支付宝客户端初始化成功 (AppID: {self.app_id})")
        except Exception as e:
            print(f"❌ 支付宝客户端初始化失败: {e}")
            raise

    def _load_private_key(self):
        """加载支付宝应用私钥"""
        try:
            key_file = getattr(self.config, "ALIPAY_PRIVATE_KEY_FILE", None)
            if not key_file:
                raise Exception("ALIPAY_PRIVATE_KEY_FILE 未配置")

            with open(key_file, "r", encoding="utf-8") as f:
                private_key = f.read()
            return private_key
        except FileNotFoundError:
            raise Exception(f"支付宝私钥文件不存在: {key_file}")
        except Exception as e:
            raise Exception(f"加载支付宝私钥失败: {e}")

    def _load_public_key(self):
        """加载支付宝公钥"""
        try:
            key_file = getattr(self.config, "ALIPAY_PUBLIC_KEY_FILE", None)
            if not key_file:
                raise Exception("ALIPAY_PUBLIC_KEY_FILE 未配置")

            with open(key_file, "r", encoding="utf-8") as f:
                public_key = f.read()
            return public_key
        except FileNotFoundError:
            raise Exception(f"支付宝公钥文件不存在: {key_file}")
        except Exception as e:
            raise Exception(f"加载支付宝公钥失败: {e}")

    def create_wap_pay_order(
        self, order_no, amount, subject="发型迁移充值", quit_url=""
    ):
        """
        创建H5手机网站支付订单

        Args:
            order_no: 订单号
            amount: 金额（元）
            subject: 商品标题
            quit_url: 用户付款中途退出返回商户网站的URL

        Returns:
            dict: {
                'success': bool,
                'pay_url': str,  # 支付URL
                'error': str
            }
        """
        try:
            # 转换为字符串格式的金额（保留2位小数）
            total_amount = f"{amount:.2f}"

            print(f"\n📱 创建支付宝H5支付订单...")
            print(f"   订单号: {order_no}")
            print(f"   金额: {amount} 元")
            print(f"   商品: {subject}")

            # 构建订单参数
            order_params = {
                "out_trade_no": order_no,
                "total_amount": total_amount,
                "subject": subject,
                "product_code": "QUICK_WAP_WAY",
            }

            # 如果提供了quit_url，添加到参数中
            if quit_url:
                order_params["quit_url"] = quit_url

            # 生成支付URL
            pay_url = self.alipay.api_alipay_trade_wap_pay(**order_params)

            # 支付宝返回的是完整的支付URL
            pay_url = f"{self.gateway}?{pay_url}"

            print(f"✅ 创建订单成功!")
            print(f"   支付URL: {pay_url}")

            return {"success": True, "pay_url": pay_url}

        except Exception as e:
            print(f"❌ 创建支付宝订单失败: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def verify_callback(self, request_data):
        """
        验证支付回调

        Args:
            request_data: Flask request 对象或 dict（包含POST数据）

        Returns:
            dict: {
                'success': bool,
                'data': {
                    'order_no': str,
                    'trade_no': str,  # 支付宝交易号
                    'amount': float
                },
                'error': str
            }
        """
        try:
            print(f"\n🔍 验证支付宝支付回调...")

            # 处理不同类型的输入
            if hasattr(request_data, "form"):
                # Flask request对象
                params = request_data.form.to_dict()
            elif hasattr(request_data, "get_json"):
                # Flask request对象（JSON）
                params = request_data.get_json()
            elif isinstance(request_data, dict):
                # 字典对象
                params = request_data
            else:
                return {"success": False, "error": "无效的参数类型"}

            # 验证签名
            signature = params.pop("sign", None)

            if not signature:
                return {"success": False, "error": "缺少签名"}

            # 使用SDK验证签名
            success = self.alipay.verify(params, signature)

            if not success:
                print(f"❌ 签名验证失败")
                return {"success": False, "error": "签名验证失败"}

            # 验证交易状态
            trade_status = params.get("trade_status")

            if trade_status not in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
                error_msg = f"交易状态: {trade_status}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}

            # 获取订单信息
            order_no = params.get("out_trade_no")
            trade_no = params.get("trade_no")
            total_amount = float(params.get("total_amount", "0"))

            print(f"✅ 支付成功!")
            print(f"   订单号: {order_no}")
            print(f"   支付宝交易号: {trade_no}")
            print(f"   支付金额: {total_amount} 元")

            return {
                "success": True,
                "data": {
                    "order_no": order_no,
                    "trade_no": trade_no,
                    "amount": total_amount,
                },
            }

        except Exception as e:
            print(f"❌ 验证支付宝回调异常: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def query_order(self, order_no):
        """
        查询订单状态

        Args:
            order_no: 商户订单号

        Returns:
            dict: {
                'success': bool,
                'trade_status': str,
                'error': str
            }
        """
        try:
            result = self.alipay.api_alipay_trade_query(out_trade_no=order_no)

            if result.get("code") == "10000":
                return {
                    "success": True,
                    "trade_status": result.get("trade_status"),
                    "data": result,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("sub_msg", result.get("msg", "查询失败")),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @property
    def gateway(self):
        """支付宝网关地址"""
        # 生产环境
        return "https://openapi.alipay.com/gateway.do"


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("支付宝支付模块测试")
    print("=" * 60)

    try:
        # 测试初始化
        alipay_client = AlipayClient()
        print(f"\n✅ 初始化成功")
        print(f"   AppID: {alipay_client.app_id}")

        # 测试签名（需要真实证书才能测试）
        print(f"\n⚠️  完整功能测试需要:")
        print(f"   1. 配置支付宝应用APPID")
        print(f"   2. 配置应用私钥（RSA2）")
        print(f"   3. 配置支付宝公钥")
        print(f"   4. 使用真实订单号测试")

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        print(f"\n请检查:")
        print(f"   1. .env 文件是否配置了支付宝参数")
        print(f"   2. 应用私钥格式是否正确")
        print(f"   3. 支付宝公钥格式是否正确")

    print("\n" + "=" * 60)
