#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云闪付支付模块
实现银联云闪付下单和回调验证
"""

import time
import hashlib
from config import get_config


class UnionPay:
    """云闪付支付"""
    
    def __init__(self):
        self.config = get_config()
        self.mer_id = self.config.UNIONPAY_MER_ID
        self.private_key = self.config.UNIONPAY_PRIVATE_KEY
        self.notify_url = self.config.UNIONPAY_NOTIFY_URL
        self.front_url = 'https://gateway.95516.com/jiaofei/api/frontTransReq.do'
        self.back_url = 'https://gateway.95516.com/jiaofei/api/backTransReq.do'
    
    def _sign(self, params):
        """生成签名"""
        # 按字典序排序
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        
        # 拼接字符串
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # SHA256签名
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        
        return sign
    
    def _build_params(self, params):
        """构建请求参数"""
        # 添加公共参数
        params['merId'] = self.mer_id
        params['txnTime'] = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        params['txnType'] = '01'  # 消费
        params['backUrl'] = self.notify_url
        params['frontUrl'] = self.notify_url
        params['currencyCode'] = '156'  # 人民币
        
        # 生成签名
        params['signature'] = self._sign(params)
        
        return params
    
    def create_order(self, order_no, amount, order_desc='发型迁移充值'):
        """
        创建订单
        
        Args:
            order_no: 订单号
            amount: 金额（分）
            order_desc: 订单描述
        
        Returns:
            dict: {success, tn, error}
        """
        try:
            # 构建请求参数
            params = {
                'orderId': order_no,
                'txnAmt': str(amount),
                'orderDesc': order_desc
            }
            
            params = self._build_params(params)
            
            # TODO: 调用银联API
            # 这里需要使用requests发送POST请求到银联API
            
            # 临时返回模拟数据
            return {
                'success': False,
                'error': '云闪付API待实现，需要安装python-acp'
            }
            
        except Exception as e:
            print(f"❌ 创建云闪付订单失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_callback(self, params):
        """
        验证支付回调
        
        Args:
            params: 回调参数
        
        Returns:
            dict: {success, data, error}
        """
        try:
            # 验证签名
            signature = params.get('signature')
            if not signature:
                return {
                    'success': False,
                    'error': '缺少签名'
                }
            
            # 移除签名参数
            params_copy = {k: v for k, v in params.items() if k != 'signature'}
            
            calculated_signature = self._sign(params_copy)
            
            if signature != calculated_signature:
                return {
                    'success': False,
                    'error': '签名验证失败'
                }
            
            # 验证交易状态
            resp_code = params.get('respCode')
            if resp_code != '00':
                return {
                    'success': False,
                    'error': f'交易状态: {resp_code}'
                }
            
            return {
                'success': True,
                'data': params
            }
            
        except Exception as e:
            print(f"❌ 验证云闪付回调失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_response(self, success=True):
        """
        生成响应
        
        Args:
            success: 是否成功
        
        Returns:
            str: 响应字符串
        """
        if success:
            return 'success'
        else:
            return 'failure'


# 测试代码
if __name__ == '__main__':
    unionpay = UnionPay()
    
    # 测试签名
    test_params = {
        'merId': 'test_mer_id',
        'orderId': 'test_order',
        'txnAmt': '100',
        'txnTime': '20240101000000',
        'txnType': '01'
    }
    
    sign = unionpay._sign(test_params)
    print(f"签名: {sign}")
