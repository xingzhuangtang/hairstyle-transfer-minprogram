#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
包含数据库、Redis、支付等配置
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """基础配置"""

    # Flask配置
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # 服务器配置
    SERVER_HOST = os.getenv("SERVER_HOST", "localhost:5003")
    SERVER_URL = os.getenv("SERVER_URL", "https://xn--gmq63iba0780e.com")

    # 文件上传配置
    UPLOAD_FOLDER = "static/uploads"
    RESULT_FOLDER = "static/results"
    HAIR_EXTRACTED_FOLDER = "static/hair_extracted"
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp"}

    # JWT配置
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.urandom(32).hex())
    JWT_ACCESS_TOKEN_EXPIRES = 30 * 24 * 60 * 60  # 30天

    # 阿里云配置
    ALIBABA_CLOUD_ACCESS_KEY_ID = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
    ALIBABA_CLOUD_ACCESS_KEY_SECRET = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

    # OSS配置
    OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "oss-cn-shanghai.aliyuncs.com")
    OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "hair-transfer-bucket")

    # 微信小程序配置
    WECHAT_APP_ID = os.getenv("WECHAT_APP_ID")
    WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET")

    # 微信支付配置 (API v2 - 向后兼容)
    WECHAT_API_KEY = os.getenv("WECHAT_API_KEY")

    # 微信支付配置 (API v3)
    WECHAT_PAY_ENV = os.getenv("WECHAT_PAY_ENV", "production")  # sandbox 或 production
    WECHAT_MCH_ID = os.getenv("WECHAT_MCH_ID")
    WECHAT_PAY_CERT_PATH = os.getenv("WECHAT_PAY_CERT_PATH")  # 商户API证书
    WECHAT_PAY_KEY_PATH = os.getenv("WECHAT_PAY_KEY_PATH")  # 商户API私钥
    WECHAT_PAY_PLATFORM_CERT_PATH = os.getenv(
        "WECHAT_PAY_PLATFORM_CERT_PATH"
    )  # 微信支付平台证书
    WECHAT_PAY_API_V3_KEY = os.getenv("WECHAT_PAY_API_V3_KEY")  # API v3密钥(32字节)
    WECHAT_NOTIFY_URL = os.getenv("WECHAT_NOTIFY_URL")

    # 支付宝配置
    ALIPAY_APP_ID = os.getenv("ALIPAY_APP_ID")
    ALIPAY_PRIVATE_KEY = os.getenv("ALIPAY_PRIVATE_KEY")
    ALIPAY_PUBLIC_KEY = os.getenv("ALIPAY_PUBLIC_KEY")
    ALIPAY_PRIVATE_KEY_FILE = os.getenv("ALIPAY_PRIVATE_KEY_FILE")
    ALIPAY_PUBLIC_KEY_FILE = os.getenv("ALIPAY_PUBLIC_KEY_FILE")
    ALIPAY_NOTIFY_URL = os.getenv("ALIPAY_NOTIFY_URL")

    # 短信配置（阿里云短信）
    SMS_ACCESS_KEY_ID = os.getenv("SMS_ACCESS_KEY_ID")
    SMS_ACCESS_KEY_SECRET = os.getenv("SMS_ACCESS_KEY_SECRET")
    SMS_SIGN_NAME = os.getenv("SMS_SIGN_NAME")
    SMS_TEMPLATE_CODE = os.getenv("SMS_TEMPLATE_CODE")


class DevelopmentConfig(Config):
    """开发环境配置"""

    # 数据库配置
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "hairstyle_transfer")

    # Redis配置
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG = False

    # 数据库配置
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

    # Redis配置
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


# 配置映射
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


# 获取当前配置
def get_config(env=None):
    """获取配置"""
    if env is None:
        env = os.getenv("FLASK_ENV", "development")
    return config.get(env, DevelopmentConfig)


# 充值规则配置
RECHARGE_RULES = {
    10: {"scissor_hairs": 1000, "comb_hairs": 0},
    20: {"scissor_hairs": 2000, "comb_hairs": 88},
    50: {"scissor_hairs": 5000, "comb_hairs": 588},
    100: {"scissor_hairs": 10000, "comb_hairs": 1688},
}


# 收费规则配置
PRICING_RULES = {
    "normal": {
        "hair_segment": 4,
        "face_merge": 4,
        "sketch": 84,  # 单独素描收费（独立）
        "combined": 88,  # 综合处理（发型迁移 + 素描）
        "face_merge_step": 4,  # 分步模式第1步：仅发型迁移
        "sketch_step": 88,  # 分步模式第2步：基于第1步结果生成素描
    },
    "premium": {
        "hair_segment": 2,
        "face_merge": 2,
        "sketch": 42,  # 单独素描收费（会员50%）
        "combined": 46,  # 综合处理（会员50%）
        "face_merge_step": 2,  # 分步模式第1步（会员50%）
        "sketch_step": 44,  # 分步模式第2步（会员50%）
    },
}


# 会员配置
MEMBER_CONFIG = {"vip": {"price": 99, "duration_days": 365, "bonus_hairs": 1000}}


# ============================================
# 充值规则配置
# ============================================

# 普通用户充值规则
NORMAL_RECHARGE_RULES = {
    10:  {"scissor_hairs": 1000, "comb_hairs": 0,     "bonus_ratio": 1.0},
    20:  {"scissor_hairs": 2000, "comb_hairs": 88,    "bonus_ratio": 1.044},
    50:  {"scissor_hairs": 5000, "comb_hairs": 588,   "bonus_ratio": 1.1176},
    100: {"scissor_hairs": 10000, "comb_hairs": 1688, "bonus_ratio": 1.1688},
}

# 陪跑会员充值规则 (额外赠送 comb_hairs)
VIP_RECHARGE_RULES = {
    10:  {"scissor_hairs": 1000, "comb_hairs": 8,    "bonus_ratio": 1.0},
    20:  {"scissor_hairs": 2000, "comb_hairs": 48,   "bonus_ratio": 1.044},
    50:  {"scissor_hairs": 5000, "comb_hairs": 299,  "bonus_ratio": 1.1176},
    100: {"scissor_hairs": 10000, "comb_hairs": 888, "bonus_ratio": 1.1688},
}

# 统一充值规则引用 (根据用户类型动态选择)
RECHARGE_RULES = {
    "normal": NORMAL_RECHARGE_RULES,
    "vip": VIP_RECHARGE_RULES,
}


# ============================================
# 收费规则配置
# ============================================

# 普通用户服务价格
NORMAL_SERVICE_PRICING = {
    "extract_hair_only": 4,       # 仅提取发型
    "migrate_hair_only": 4,       # 仅迁移发型
    "sketch_only": 84,            # 单独素描
    "combined": 88,               # 综合处理 (发型迁移 + 素描)
    "step1_migrate": 4,           # 分步模式第 1 步 (发型迁移)
    "step2_sketch": 88,           # 分步模式第 2 步 (素描)
}

# 陪跑会员服务价格 (5 折优惠)
VIP_SERVICE_PRICING = {
    "extract_hair_only": 2,       # 仅提取发型
    "migrate_hair_only": 2,       # 仅迁移发型
    "sketch_only": 42,            # 单独素描
    "combined": 46,               # 综合处理 (发型迁移 + 素描)
    "step1_migrate": 2,           # 分步模式第 1 步
    "step2_sketch": 44,           # 分步模式第 2 步
}

# 统一收费规则引用 (根据用户类型动态选择)
PRICING_RULES = {
    "normal": NORMAL_SERVICE_PRICING,
    "vip": VIP_SERVICE_PRICING,
}


# ============================================
# 会员配置
# ============================================

MEMBER_CONFIG = {
    "vip": {
        "price": 99,                    # ¥99/年
        "duration_days": 365,           # 365 天
        "purchase_bonus": {"comb_hairs": 1000},  # 购买即赠
        "renew_bonus": {"comb_hairs": 1000},     # 续费/重新购买也赠
        "privileges": {
            "service_discount": 0.5,           # 50% 折扣
            "history_retention_days": 45,      # 历史记录保留
            "auto_downgrade": True             # 到期自动降级为 normal
        }
    }
}


# ============================================
# 新用户福利配置
# ============================================

NEW_USER_BONUS = {
    "comb_hairs": 1000,      # 赠送梳子发丝
    "trigger": "注册完成"
}


# ============================================
# 余额不足自动赠送配置
# ============================================

AUTO_GIFT_CONFIG = {
    "check_after_hours": 4,        # 4 小时后检查
    "max_gifts_per_year": 36,      # 年度上限 36 次
    "cooldown_hours": 4,           # 赠送间隔 4 小时
    "normal_user_bonus": 188,      # 普通用户赠送 188 根
    "vip_user_bonus": 98,          # 陪跑会员赠送 98 根
}


# ============================================
# 访客模式配置
# ============================================

GUEST_MODE_CONFIG = {
    "initial_bonus": 198,           # 首次赠送梳子发丝数量
    "auto_renew_bonus": 198,        # 4 小时续赠数量
    "check_after_hours": 4,         # 4 小时后检查
    "max_bonus_per_year": 9,        # 年度上限 9 次
    "registration_bonus": 1000,     # 注册赠送梳子发丝
    "bonus_valid_hours": 4,         # 赠送有效期（4 小时后失效）
}


# ============================================
# 开发者测试账号配置
# ============================================
# 从环境变量读取开发者模式开关和开发者账号，未配置则禁用（功能默认禁用）
# 本地开发时可在 .env 中设置：DEVELOPER_MODE_ENABLED=true, DEVELOPER_ACCOUNTS=5,7
try:
    # 优先从本地 debug_config.py 读取（不提交到 git）
    from debug_config import DEVELOPER_MODE_ENABLED, DEVELOPER_ACCOUNTS
except ImportError:
    # 否则从环境变量读取
    DEVELOPER_MODE_ENABLED = os.getenv("DEVELOPER_MODE_ENABLED", "False").lower() == "true"
    DEVELOPER_ACCOUNTS = [int(x.strip()) for x in os.getenv("DEVELOPER_ACCOUNTS", "").split(",") if x.strip()]
