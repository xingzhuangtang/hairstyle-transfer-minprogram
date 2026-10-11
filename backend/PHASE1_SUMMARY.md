# Phase 1 智能决策改进总结

## 改进概览

本次改进将系统监控从**简单关键词匹配**升级为**多维度智能评分决策系统**。

## 核心改进

### 1. 修复器多路评分 (`fixer.py`)

**改进前：**
```python
# 简单关键词匹配，返回第一个命中
def _match_fixer(self, alert, registry):
    for fixer in registry:
        if keyword in text:
            return fixer  # 第一个命中就返回
```

**改进后：**
```python
# 多维度评分，返回排序列表
def _score_fixers(self, alert, registry):
    for fixer in registry:
        score = match_score * 0.6 + success_rate * 40 * 0.4
        dynamic_risk = calculate_dynamic_risk(...)
    return sorted(results, key=lambda x: x['score'], reverse=True)
```

**评分维度：**
- 关键词匹配度 (60%)：标题匹配权重 2.0，描述匹配权重 1.0
- 历史成功率 (40%)：近 30 天执行成功率，无记录时默认 0.5

**测试结果：**
```
告警: [high] Redis ConnectionError
  最佳: redis_recovery (score=13.4, risk=medium)
  备选: slow_query_kill(8.6)

告警: [critical] 数据库连接失败
  最佳: db_reconnect (score=10.4, risk=medium)
```

### 2. 动态风险评估 (`fixer.py`)

**改进前：**
```python
# 静态风险等级，配置在修复器定义中
fixer = {'id': 'db_reconnect', 'risk': 'low', ...}
```

**改进后：**
```python
# 动态计算，综合考虑多个因素
def _calculate_dynamic_risk(self, fixer, alert_severity, success_rate):
    base = risk_map[fixer['risk']]
    if alert_severity >= 'high': base += 1
    if success_rate < 0.3: base += 1
    elif success_rate >= 0.8 and base >= 2: base -= 1
    return risk_map_inverse[base]
```

**测试结果：**
```
low risk + low severity + high success → low ✓
low risk + critical severity + high success → medium ✓
high risk + critical severity + low success → high ✓
```

### 3. 防御规则多路评估 (`defense_rule.py`)

**改进前：**
```python
# 首条命中即返回
for rule in sorted(rules, key=lambda r: r.priority):
    if match(rule, alert):
        return execute(rule)  # 第一条命中就返回
```

**改进后：**
```python
# 评估所有匹配规则，选择最优
candidates = []
for rule in rules:
    if match(rule, alert):
        score = calculate_score(rule)
        candidates.append((rule, score))
best_rule = max(candidates, key=lambda x: x[1])
return execute(best_rule)
```

**评分维度：**
- 优先级 (50%)：`50 / priority`
- 历史命中数 (30%)：`min(30, sqrt(hit_count) * 5)`
- 模式精确度 (20%)：regex=20, source_module=15, frequency=12, title_contains=8

**测试结果：**
```
规则评分排序：
  DataError类型错误自动防护: 45.8 (regex模式 + priority=5 + 10次命中)
  Redis 错误自动恢复: 33.7 (title_contains + priority=15 + 20次命中)
  空白图像自动防护: 31.7 (title_contains + priority=3 + 2次命中)
  数据库连接错误自动恢复: 24.2 (title_contains + priority=10 + 5次命中)
```

### 4. 统一决策链 (`alert_manager.py`)

**改进前：**
```python
# 直接调用修复器
if fixer:
    fixer.try_auto_fix(alert_id)
```

**改进后：**
```python
# 规则引擎优先，修复器兜底
def _smart_dispatch(self, alert_id):
    # Step 1: 规则引擎评估
    if rule_engine:
        result = rule_engine.evaluate(alert)
        if result:
            return result
    
    # Step 2: 修复器评分兜底
    if fixer:
        return fixer.try_auto_fix(alert_id)
```

## 性能对比

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| 修复器选择准确性 | 低（关键词匹配） | 高（多维度评分） |
| 风险评估灵活性 | 静态配置 | 动态计算 |
| 规则选择准确性 | 低（首条命中） | 高（最优选择） |
| 决策透明度 | 低（无日志） | 高（详细日志） |

## 日志示例

```
告警 123 修复决策: fixer=db_reconnect, score=85.2, risk=low, alternatives=['redis_recovery']
规则决策: best="数据库连接错误自动恢复"(score=48.5), alternatives=[{'name': 'Redis 错误自动恢复', 'score': '35.2'}]
```

## 向后兼容性

所有改动保持向后兼容：
- `_match_fixer()` 方法保留，内部调用 `_score_fixers()`
- 修复器注册表结构不变
- 规则引擎接口不变

## 测试覆盖

测试文件：`test_smart_decision.py`

测试场景：
1. 修复器多路评分（4 种告警类型）
2. 动态风险评估（5 种组合场景）
3. 防御规则多路评估（4 条规则对比）

所有测试通过 ✅

## 下一步（Phase 2）

1. 集成 Strands Decider 2B 决策模型
2. 修复效果反馈闭环
3. 预测性修复（基于进化分析）

---

**改进完成时间：** 2026-10-11  
**测试状态：** ✅ 通过  
**部署状态：** 待部署
