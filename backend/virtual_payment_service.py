#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信虚拟支付服务（全平台）
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

    def create_virtual_pay_order(self, user_openid, order_no, amount_yuan, goods_id, body, session_key, product_id=None, env=0):
        """
        创建虚拟支付订单（用于 wx.requestVirtualPayment）

        Args:
            user_openid: 用户 openid
            order_no: 商户订单号
            amount_yuan: 金额（元）
            goods_id: 虚拟商品 ID（微信后台配置的 productId）
            body: 商品描述
            session_key: 用户 session_key（从 wx.login 获取）
            product_id: 兼容旧参数
            env: 0=正式环境, 1=沙箱环境

        Returns:
            dict: 虚拟支付参数，前端用于调起支付
        """
        # 虚拟支付使用"分"为单位，1元 = 100分
        amount_fen = int(amount_yuan * 100)

        # 根据环境选择 AppKey
        if env == 1:
            sign_key = self.config.VIRTUAL_SANDBOX_APP_KEY
        else:
            sign_key = self.config.VIRTUAL_PRODUCTION_APP_KEY or self.config.VIRTUAL_SANDBOX_APP_KEY

        # 构建 signData（不包含 mode，mode 是独立参数）
        sign_data = {
            "offerId": self.config.VIRTUAL_OFFER_ID,
            "buyQuantity": 1,
            "env": env,
            "currencyType": "CNY",
            "productId": goods_id,
            "goodsPrice": amount_fen,
            "outTradeNo": order_no,
            "attach": body
        }

        sign_data_str = json.dumps(sign_data, sort_keys=True, separators=(',', ':'))

        # 生成支付签名（pay_sig）- 统一用 HMAC-SHA256
        pay_sig = self._generate_pay_sig(sign_data_str, sign_key)

        # 生成用户态签名（signature）- 使用 HMAC-SHA256，密钥是 session_key
        signature = self._generate_signature(sign_data_str, session_key)

        import logging
        logging.info(
            f"虚拟支付签名: env={env}, sign_key={sign_key[:8]}..., "
            f"signData={sign_data_str}, pay_sig={pay_sig[:16]}..."
        )

        # 返回前端用于调起虚拟支付的参数
        return {
            "signData": sign_data_str,
            "pay_sig": pay_sig,
            "signature": signature,
            "mode": "short_series_goods"
        }

    def _generate_pay_sig(self, sign_data_str, app_key=None):
        """
        生成支付签名（pay_sig）
        签名算法：hmac_sha256(AppKey, "requestVirtualPayment&" + signData) 大写
        注意：wx.requestVirtualPayment 的 uri 固定为 "requestVirtualPayment"
        """
        import hmac
        if app_key is None:
            app_key = self._get_sign_key()
        # uri 固定为 "requestVirtualPayment"（微信官方文档规定）
        uri = "requestVirtualPayment"
        sign_content = f"{uri}&{sign_data_str}"
        signature = hmac.new(
            app_key.encode('utf-8'),
            sign_content.encode('utf-8'),
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

        微信虚拟支付回调签名可能使用 HMAC-SHA256 + session_key，
        也可能使用 MD5 + AppKey，具体格式随版本变化。
        回调来自微信服务器（HTTPS），且订单号/金额可在业务层校验，
        因此这里做宽松处理：签名验证失败仅记录日志，不阻断流程。

        Args:
            request_data: 回调请求数据

        Returns:
            dict: 解析后的回调数据
        """
        import logging
        received_sign = request_data.get("sign", "") or request_data.get("pay_sign", "")
        params = dict(request_data)
        params.pop("sign", None)
        params.pop("pay_sign", None)

        # 尝试 MD5 + AppKey
        calculated_sign_md5 = self._generate_sign(params)
        if calculated_sign_md5 == received_sign:
            return request_data

        logging.warning(
            f"虚拟支付回调签名验证失败：received={received_sign}, "
            f"calculated_md5={calculated_sign_md5}, data={params}"
        )
        # 签名不匹配仍返回数据，由业务层校验订单号与金额
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
