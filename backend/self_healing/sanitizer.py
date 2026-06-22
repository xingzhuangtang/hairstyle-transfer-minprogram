#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
敏感数据脱敏模块
在告警写入DB和推送通知前，自动脱敏敏感字段
"""

import re
import json

# 完全替换的字段名模式
FULLY_REDACT_PATTERNS = [
    'password', 'passwd', 'pwd',
    'token', 'secret', 'key', 'authorization',
    'access_token', 'refresh_token', 'api_key', 'api_secret',
    'mch_id', 'mch_key', 'pay_secret',
]

# 手机号脱敏：保留前3后4
PHONE_PATTERNS = ['phone', 'mobile', 'telephone', 'cellphone']

# ID类脱敏：保留前6后4
ID_PATTERNS = ['openid', 'unionid', 'id_card', 'identity', 'wechat_openid']

# 支付相关：保留前4后4
PAY_PATTERNS = ['transaction_id', 'out_trade_no', 'prepay_id']


def _should_fully_redact(field_name):
    name = field_name.lower()
    return any(p in name for p in FULLY_REDACT_PATTERNS)


def _should_mask_phone(field_name):
    name = field_name.lower()
    return any(p in name for p in PHONE_PATTERNS)


def _should_mask_id(field_name):
    name = field_name.lower()
    return any(p in name for p in ID_PATTERNS)


def _should_mask_pay(field_name):
    name = field_name.lower()
    return any(p in name for p in PAY_PATTERNS)


def _mask_phone(value):
    s = str(value)
    if len(s) >= 7:
        return s[:3] + '****' + s[-4:]
    return '***'


def _mask_id(value):
    s = str(value)
    if len(s) >= 10:
        return s[:6] + '****' + s[-4:]
    return '***'


def _mask_pay(value):
    s = str(value)
    if len(s) >= 8:
        return s[:4] + '****' + s[-4:]
    return '***'


def sanitize_value(field_name, value):
    """根据字段名单个值脱敏"""
    if value is None:
        return None
    if _should_fully_redact(field_name):
        return '***'
    if _should_mask_phone(field_name):
        return _mask_phone(value)
    if _should_mask_id(field_name):
        return _mask_id(value)
    if _should_mask_pay(field_name):
        return _mask_pay(value)
    return value


def sanitize_dict(data, max_len=None):
    """递归脱敏字典"""
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: sanitize_value(k, sanitize_dict(v, max_len)) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [sanitize_dict(item, max_len) for item in data]
    if isinstance(data, str) and max_len and len(data) > max_len:
        return data[:max_len] + '...(truncated)'
    return data


def sanitize_request_params(params, max_len=None):
    """脱敏请求参数（支持 dict 和 JSON string）"""
    if params is None:
        return None
    if isinstance(params, str):
        try:
            parsed = json.loads(params)
            sanitized = sanitize_dict(parsed, max_len)
            result = json.dumps(sanitized, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            result = params
    else:
        sanitized = sanitize_dict(params, max_len)
        result = json.dumps(sanitized, ensure_ascii=False) if sanitized else None

    if max_len and result and len(result) > max_len:
        result = result[:max_len] + '...(truncated)'
    return result


def sanitize_headers(headers, max_len=None):
    """脱敏HTTP Headers"""
    if headers is None:
        return None
    if isinstance(headers, dict):
        sanitized = {}
        for k, v in headers.items():
            if _should_fully_redact(k):
                sanitized[k] = '***'
            else:
                val = str(v)
                if max_len and len(val) > max_len:
                    val = val[:max_len] + '...(truncated)'
                sanitized[k] = val
        return json.dumps(sanitized, ensure_ascii=False)
    return str(headers)[:max_len] if max_len else str(headers)


def sanitize_stack_trace(traceback_str, max_len=None):
    """截断堆栈信息"""
    if not traceback_str:
        return None
    if max_len and len(traceback_str) > max_len:
        return traceback_str[:max_len] + '\n...(truncated)'
    return traceback_str
