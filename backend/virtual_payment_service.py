#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信虚拟支付服务（iOS端）
用于小程序内虚拟商品购买（头发丝充值、VIP会员）
"""

import hashlib
import json
import time
import uuid
import requests
from datetime import datetime
from config import get_config


class WeChatVirtualPayService:
    """微信虚拟支付服务"""

    BASE_URL = "https://api.mch.weixin.qq.com"

    def __init__(self):
        self.config = get_config()
        self.mch_id = self.config.WECHAT_VIRTUAL_PAY_MCH_ID
        self.app_id = self.config.WECHAT_APP_ID

    def _generate_nonce_str(self):
        """生成随机字符串"""
        return uuid.uuid4().hex[:32]

    def _get_sign_key(self):
        """获取签名密钥：虚拟支付使用 AppKey，非普通微信支付 API Key"""
        return self.config.VIRTUAL_PRODUCTION_APP_KEY or self.config.VIRTUAL_SANDBOX_APP_KEY

    def _generate_sign(self, params):
        """生成签名"""
        sorted_params = sorted(params.items())
        string_a = "&".join([f"{k}={v}" for k, v in sorted_params if v is not None])
        sign_key = self._get_sign_key()
        string_sign_temp = f"{string_a}&key={sign_key}"
        return hashlib.md5(string_sign_temp.encode("utf-8")).hexdigest().upper()

    def create_virtual_pay_order(self, user_openid, order_no, amount_yuan, goods_id, body, session_key, product_id=None):
        """
        创建虚拟支付订单（用于 wx.requestVirtualPayment）

        Args:
            user_openid: 用户 openid
            order_no: 商户订单号
            amount_yuan: 金额（元）
            goods_id: 虚拟商品 ID
            body: 商品描述
            session_key: 用户 session_key（从 wx.login 获取）
            product_id: 道具 ID（productId）

        Returns:
            dict: 虚拟支付参数，前端用于调起支付
        """
        # 虚拟支付使用"分"为单位，1元 = 100分
        amount_fen = int(amount_yuan * 100)

        # 构建 signData（不包含 mode，mode 是独立参数）
        sign_data = {
            "offerId": self.config.VIRTUAL_OFFER_ID,
            "buyQuantity": 1,
            "env": 0,  # 0=正式环境
            "currencyType": "CNY",
            "productId": product_id or goods_id,
            "goodsPrice": amount_fen,
            "outTradeNo": order_no,
            "attach": body
        }

        sign_data_str = json.dumps(sign_data, separators=(',', ':'))

        # 生成支付签名（pay_sig）- 使用 HMAC-SHA256，密钥是 session_key
        pay_sig = self._generate_pay_sig(sign_data_str, session_key)

        # 生成用户态签名（signature）- 使用 HMAC-SHA256，密钥是 session_key
        signature = self._generate_signature(sign_data_str, session_key)

        # 返回前端用于调起虚拟支付的参数
        return {
            "signData": sign_data_str,
            "pay_sig": pay_sig,
            "signature": signature,
            "mode": "short_series_goods"
        }

    def _generate_pay_sig(self, sign_data_str, session_key):
        """
        生成支付签名（pay_sig）
        签名算法：hmac_sha256(session_key, signData) 大写
        """
        import hmac
        signature = hmac.new(
            session_key.encode('utf-8'),
            sign_data_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        return signature

    def _generate_signature(self, sign_data_str, session_key):
        """
        生成用户态签名（signature）
        签名算法：hmac_sha256(session_key, signData) 小写
        """
        import hmac
        signature = hmac.new(
            session_key.encode('utf-8'),
            sign_data_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_callback(self, request_data):
        """
        验证虚拟支付回调

        Args:
            request_data: 回调请求数据

        Returns:
            dict: 解析后的回调数据，如果验证失败返回 None
        """
        # 验证签名
        received_sign = request_data.get("sign", "")
        params = dict(request_data)
        params.pop("sign", None)

        calculated_sign = self._generate_sign(params)
        if calculated_sign != received_sign:
            return None

        return request_data

    def get_goods_id(self, goods_key):
        """
        根据商品键获取虚拟商品 ID

        Args:
            goods_key: 商品键（如 recharge_10, member_vip）

        Returns:
            str: 虚拟商品 ID，如果未配置返回 None
        """
        return self.config.WECHAT_VIRTUAL_GOODS_IDS.get(goods_key, "")

    def is_virtual_pay_enabled(self):
        """检查虚拟支付是否已配置"""
        return bool(self.mch_id) and bool(self.config.WECHAT_VIRTUAL_PAY_NOTIFY_URL)
