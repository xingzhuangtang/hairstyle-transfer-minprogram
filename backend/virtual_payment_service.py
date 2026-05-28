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

    def _generate_sign(self, params):
        """生成签名"""
        # 按 key 排序并拼接
        sorted_params = sorted(params.items())
        string_a = "&".join([f"{k}={v}" for k, v in sorted_params if v is not None])
        string_sign_temp = f"{string_a}&key={self.config.WECHAT_PAY_API_V3_KEY}"
        return hashlib.md5(string_sign_temp.encode("utf-8")).hexdigest().upper()

    def create_virtual_pay_order(self, user_openid, order_no, amount_yuan, goods_id, body):
        """
        创建虚拟支付订单

        Args:
            user_openid: 用户 openid
            order_no: 商户订单号
            amount_yuan: 金额（元）
            goods_id: 虚拟商品 ID
            body: 商品描述

        Returns:
            dict: 虚拟支付参数，前端用于调起支付
        """
        # 虚拟支付使用"米"为单位，1元 = 10米
        amount_mi = int(amount_yuan * 10)

        timestamp = str(int(time.time()))
        nonce_str = self._generate_nonce_str()

        # 请求参数
        params = {
            "mch_id": self.mch_id,
            "appid": self.app_id,
            "out_trade_no": order_no,
            "body": body,
            "total_fee": amount_mi,
            "notify_url": self.config.WECHAT_VIRTUAL_PAY_NOTIFY_URL,
            "spbill_create_ip": "127.0.0.1",  # 虚拟支付不需要实际IP
            "openid": user_openid,
            "goods_id": goods_id,
            "nonce_str": nonce_str,
            "timestamp": timestamp,
        }

        # 生成签名
        sign = self._generate_sign(params)
        params["sign"] = sign

        # 返回前端用于调起虚拟支付的参数
        return {
            "mch_id": self.mch_id,
            "appid": self.app_id,
            "package": "WXBiz",
            "nonce_str": nonce_str,
            "time_stamp": timestamp,
            "sign": sign,
            "out_trade_no": order_no,
            "goods_id": goods_id,
            "total_fee": amount_mi,
        }

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
