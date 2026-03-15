# 配置更新报告

## 更新时间
2026-03-14

## 更新内容

根据用户提供的"📋 项目福利政策与充值策略规范"文档，已完成以下配置更新：

---

## 一、核心配置变更

### 1. 用户类型命名
- **变更前**: `normal` / `premium`
- **变更后**: `normal` / `vip`

### 2. 余额不足自动赠送配置
| 配置项 | 变更前 | 变更后 |
|--------|--------|--------|
| 检查间隔 | 72 小时 | **4 小时** |
| 年度上限 | 12 次 | **36 次** |
| 普通用户赠送 | 188 根 | 188 根 (不变) |
| VIP 用户赠送 | 98 根 | 98 根 (不变) |

### 3. 新用户注册赠送
- **赠送数量**: 1000 梳子发丝 (comb_hairs)
- **触发条件**: 注册完成

### 4. VIP 会员配置
- **价格**: ¥99/年
- **购买赠送**: 1000 梳子发丝
- **续费赠送**: 1000 梳子发丝
- **服务折扣**: 50% (5 折)
- **历史记录保留**: 45 天
- **到期处理**: 自动降级为 normal

---

## 二、充值规则

### 普通用户充值规则
| 金额 | 剪刀发丝 | 梳子发丝 | 赠送比例 |
|------|----------|----------|----------|
| ¥10  | 1000     | 0        | 1:100    |
| ¥20  | 2000     | 88       | 1:104.4  |
| ¥50  | 5000     | 588      | 1:111.76 |
| ¥100 | 10000    | 1688     | 1:116.88 |

### VIP 会员充值规则 (额外赠送)
| 金额 | 剪刀发丝 | 梳子发丝 | 赠送比例 |
|------|----------|----------|----------|
| ¥10  | 1000     | 8        | 1:100    |
| ¥20  | 2000     | 48       | 1:104.4  |
| ¥50  | 5000     | 299      | 1:111.76 |
| ¥100 | 10000    | 888      | 1:116.88 |

---

## 三、服务价格

### 普通用户价格
| 服务类型 | 价格 (发丝) |
|----------|-------------|
| 仅提取发型 | 4 |
| 仅迁移发型 | 4 |
| 单独素描 | 84 |
| 综合处理 (发型迁移 + 素描) | 88 |
| 分步模式第 1 步 (发型迁移) | 4 |
| 分步模式第 2 步 (素描) | 88 |

### VIP 会员价格 (5 折)
| 服务类型 | 价格 (发丝) |
|----------|-------------|
| 仅提取发型 | 2 |
| 仅迁移发型 | 2 |
| 单独素描 | 42 |
| 综合处理 (发型迁移 + 素描) | 46 |
| 分步模式第 1 步 (发型迁移) | 2 |
| 分步模式第 2 步 (素描) | 44 |

---

## 四、已更新文件清单

### 后端文件
| 文件 | 更新内容 |
|------|----------|
| `backend/config.py` | 新增 NORMAL_RECHARGE_RULES, VIP_RECHARGE_RULES, NORMAL_SERVICE_PRICING, VIP_SERVICE_PRICING, MEMBER_CONFIG, NEW_USER_BONUS, AUTO_GIFT_CONFIG |
| `backend/config_policy.py` | 创建独立的策略配置文件 |
| `backend/models.py` | 会员等级枚举从 'premium' 改为 'vip'，方法名 is_premium() 改为 is_vip() |
| `backend/auth.py` | 装饰器 premium_required 改为 vip_required |
| `backend/payment_service.py` | 使用新的会员配置结构，'premium' 改为 'vip' |
| `backend/hair_service.py` | 使用新的价格配置，'premium' 改为 'vip' |
| `backend/account_service.py` | 更新余额不足赠送逻辑 (4 小时/36 次) |

### 前端文件
| 文件 | 更新内容 |
|------|----------|
| `miniprogram/utils/constants.js` | PRICING 从 premium 改为 vip，INSUFFICIENT_BONUS_CONFIG 变量名更新 |

---

## 五、双槽消费逻辑

头发丝消费优先级：
1. **优先消费**: 梳子卡槽 (comb_hairs) - 用于赠送、奖励发丝
2. **次级消费**: 剪刀卡槽 (scissor_hairs) - 用于充值购买发丝

消费流程：
```
if comb_hairs >= required:
    comb_hairs -= required
else:
    scissor_needed = required - comb_hairs
    comb_hairs = 0
    scissor_hairs -= scissor_needed
```

---

## 六、验证步骤

### 1. Python 语法检查
```bash
cd backend
python3 -m py_compile config.py
python3 -m py_compile account_service.py
python3 -m py_compile payment_service.py
python3 -m py_compile hair_service.py
python3 -m py_compile models.py
python3 -m py_compile auth.py
```
✅ 所有文件语法检查通过

### 2. 数据库迁移 (需要执行)
由于会员等级从 'premium' 改为 'vip'，需要更新数据库：

```sql
-- 更新用户表
UPDATE users SET member_level = 'vip' WHERE member_level = 'premium';

-- 更新会员订单表
UPDATE member_orders SET member_level = 'vip' WHERE member_level = 'premium';

-- 修改枚举约束 (MySQL)
ALTER TABLE users MODIFY COLUMN member_level ENUM('normal', 'vip') DEFAULT 'normal';
ALTER TABLE member_orders MODIFY COLUMN member_level ENUM('normal', 'vip') NOT NULL;
```

### 3. 功能测试清单
- [ ] 新用户注册赠送 1000 梳子发丝
- [ ] 余额不足时 4 小时后自动赠送
- [ ] 年度赠送次数上限 36 次
- [ ] VIP 会员购买 ¥99/年赠送 1000 梳子发丝
- [ ] VIP 会员享受 5 折服务价格
- [ ] 双槽消费逻辑正确 (梳子优先)
- [ ] VIP 到期自动降级为 normal

---

## 七、配置引用

```python
from config import (
    NORMAL_RECHARGE_RULES,
    VIP_RECHARGE_RULES,
    NORMAL_SERVICE_PRICING,
    VIP_SERVICE_PRICING,
    MEMBER_CONFIG,
    NEW_USER_BONUS,
    AUTO_GIFT_CONFIG
)

# 根据用户类型获取配置
def get_recharge_rules(user_level):
    return VIP_RECHARGE_RULES if user_level == 'vip' else NORMAL_RECHARGE_RULES

def get_pricing(user_level):
    return VIP_SERVICE_PRICING if user_level == 'vip' else NORMAL_SERVICE_PRICING
```

---

## 八、注意事项

1. **数据库迁移必须在部署前完成**
2. **测试环境验证后再上线**
3. **小程序前端 API 地址已改为 http://localhost:5003**
4. **会员等级变更后，历史数据需要兼容处理**

---

报告生成时间：2026-03-14
