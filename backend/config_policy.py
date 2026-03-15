#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户福利政策与充值策略配置
根据用户提供的最终规则定义
"""

# ============================================
# 充值规则配置
# ============================================

# 普通用户充值规则
NORMAL_RECHARGE_RULES = {
    10:  {"scissor_hairs": 1000, "comb_hairs": 0,     "bonus_ratio": 1.0},     # 1:100
    20:  {"scissor_hairs": 2000, "comb_hairs": 88,    "bonus_ratio": 1.044},   # 1:104.4
    50:  {"scissor_hairs": 5000, "comb_hairs": 588,   "bonus_ratio": 1.1176},  # 1:111.76
    100: {"scissor_hairs": 10000, "comb_hairs": 1688, "bonus_ratio": 1.1688},  # 1:116.88
}

# 陪跑会员充值规则 (额外赠送 comb_hairs)
VIP_RECHARGE_RULES = {
    10:  {"scissor_hairs": 1000, "comb_hairs": 8,    "bonus_ratio": 1.0},     # 1:100
    20:  {"scissor_hairs": 2000, "comb_hairs": 48,   "bonus_ratio": 1.044},   # 1:104.4
    50:  {"scissor_hairs": 5000, "comb_hairs": 299,  "bonus_ratio": 1.1176},  # 1:111.76
    100: {"scissor_hairs": 10000, "comb_hairs": 888, "bonus_ratio": 1.1688},  # 1:116.88
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
