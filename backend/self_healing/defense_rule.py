#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
防御规则引擎
基于规则模式匹配告警，执行自动处置（auto_fix / warn / suppress）
"""

import json
import logging
import re
import time
from datetime import datetime

logger = logging.getLogger('self_healing')

DEFAULT_RULES = [
    {
        'name': '数据库连接错误自动恢复',
        'pattern_type': 'title_contains',
        'pattern_value': 'OperationalError',
        'action': 'auto_fix',
        'action_config': json.dumps({'fix_id': 'db_reconnect'}),
        'priority': 10,
        'cooldown_seconds': 300,
    },
    {
        'name': 'Redis 错误自动恢复',
        'pattern_type': 'title_contains',
        'pattern_value': 'Redis',
        'action': 'auto_fix',
        'action_config': json.dumps({'fix_id': 'redis_recovery'}),
        'priority': 15,
        'cooldown_seconds': 300,
    },
    {
        'name': '同源模块告警抑制',
        'pattern_type': 'frequency',
        'pattern_value': json.dumps({'threshold': 10, 'window_seconds': 300}),
        'action': 'suppress',
        'action_config': json.dumps({'message': '同源模块告警频率过高，已自动抑制'}),
        'priority': 50,
        'cooldown_seconds': 600,
    },
]


class RuleEngine:
    """防御规则引擎"""

    def __init__(self, app, config, db=None, fixer=None, alert_manager=None):
        self.app = app
        self.config = config
        self.db = db
        self.fixer = fixer
        self.alert_manager = alert_manager
        self._cooldown_cache = {}

    def evaluate(self, alert):
        """评估告警，返回处置动作"""
        rules = self._load_rules()
        if not rules:
            return None

        for rule in sorted(rules, key=lambda r: r.priority):
            if not rule.enabled:
                continue

            if self._match_rule(rule, alert):
                if self._check_cooldown(rule):
                    self._update_hit(rule)
                    return self._execute_action(rule, alert)

        return None

    def _load_rules(self):
        """从 DB 加载规则"""
        if not self.db:
            return []

        try:
            from .models import DefenseRule
            return self.db.session.query(DefenseRule) \
                .filter(DefenseRule.enabled == 1) \
                .all()
        except Exception as e:
            logger.error(f'加载防御规则失败: {e}')
            return []

    def _match_rule(self, rule, alert):
        """检查告警是否匹配规则"""
        ptype = rule.pattern_type
        pvalue = rule.pattern_value

        if ptype == 'title_contains':
            return pvalue.lower() in (alert.title or '').lower()

        elif ptype == 'regex':
            try:
                return bool(re.search(pvalue, alert.title or '', re.IGNORECASE))
            except re.error:
                return False

        elif ptype == 'source_module':
            return pvalue == (alert.source_module or '')

        elif ptype == 'frequency':
            try:
                cfg = json.loads(pvalue)
                threshold = cfg.get('threshold', 10)
                window = cfg.get('window_seconds', 300)
                return self._check_frequency(alert, threshold, window)
            except (json.JSONDecodeError, TypeError):
                return False

        return False

    def _check_frequency(self, alert, threshold, window):
        """检查同一模块告警频率"""
        if not self.db:
            return False

        try:
            from .models import SystemAlert
            from sqlalchemy import func as sql_func

            since = datetime.now() - __import__('datetime').timedelta(seconds=window)
            count = self.db.session.query(SystemAlert) \
                .filter(
                    SystemAlert.source_module == alert.source_module,
                    SystemAlert.created_at >= since,
                ).count()

            return count >= threshold
        except Exception:
            return False

    def _check_cooldown(self, rule):
        """检查冷却期"""
        cooldown = rule.cooldown_seconds or 300
        cache_key = f'rule_{rule.id}'

        if cache_key in self._cooldown_cache:
            last_hit = self._cooldown_cache[cache_key]
            if time.time() - last_hit < cooldown:
                return False

        if rule.last_hit_at:
            elapsed = (datetime.now() - rule.last_hit_at).total_seconds()
            if elapsed < cooldown:
                return False

        return True

    def _update_hit(self, rule):
        """更新规则命中记录"""
        self._cooldown_cache[f'rule_{rule.id}'] = time.time()

        if self.db:
            try:
                rule.hit_count = (rule.hit_count or 0) + 1
                rule.last_hit_at = datetime.now()
                self.db.session.commit()
            except Exception as e:
                logger.error(f'更新规则命中失败: {e}')
                try:
                    self.db.session.rollback()
                except Exception:
                    pass

    def _execute_action(self, rule, alert):
        """执行规则动作"""
        action = rule.action

        if action == 'auto_fix':
            return self._action_auto_fix(rule, alert)
        elif action == 'warn':
            return {'action': 'warn', 'rule_id': rule.id, 'rule_name': rule.name}
        elif action == 'suppress':
            return {'action': 'suppress', 'rule_id': rule.id, 'rule_name': rule.name}

        return None

    def _action_auto_fix(self, rule, alert):
        """执行自动修复"""
        fix_id = None
        try:
            config = json.loads(rule.action_config or '{}')
            fix_id = config.get('fix_id')
        except (json.JSONDecodeError, TypeError):
            pass

        if not fix_id:
            return {'action': 'warn', 'rule_id': rule.id, 'message': '规则未配置 fix_id'}

        if self.fixer:
            self.fixer.try_auto_fix(alert.id)
            return {'action': 'auto_fix', 'rule_id': rule.id, 'fix_id': fix_id}

        return {'action': 'warn', 'rule_id': rule.id, 'message': '修复引擎未初始化'}

    # ==================== 规则 CRUD ====================

    def list_rules(self):
        """列出所有规则"""
        if not self.db:
            return []
        try:
            from .models import DefenseRule
            return self.db.session.query(DefenseRule) \
                .order_by(DefenseRule.priority.asc()).all()
        except Exception as e:
            logger.error(f'查询规则列表失败: {e}')
            return []

    def create_rule(self, name, pattern_type, pattern_value, action,
                    action_config=None, priority=100, cooldown_seconds=300):
        """创建规则"""
        if not self.db:
            return None

        try:
            from .models import DefenseRule
            rule = DefenseRule(
                name=name,
                enabled=1,
                priority=priority,
                pattern_type=pattern_type,
                pattern_value=pattern_value,
                action=action,
                action_config=action_config,
                cooldown_seconds=cooldown_seconds,
            )
            self.db.session.add(rule)
            self.db.session.commit()
            return rule
        except Exception as e:
            logger.error(f'创建规则失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return None

    # 允许通过 API 修改的字段白名单
    UPDATABLE_FIELDS = {
        'name', 'enabled', 'priority', 'pattern_type', 'pattern_value',
        'action', 'action_config', 'cooldown_seconds'
    }

    def update_rule(self, rule_id, **kwargs):
        """更新规则（仅允许修改白名单字段）"""
        if not self.db:
            return None

        try:
            from .models import DefenseRule
            rule = self.db.session.query(DefenseRule).get(rule_id)
            if not rule:
                return None

            for key, value in kwargs.items():
                if key in self.UPDATABLE_FIELDS and value is not None:
                    setattr(rule, key, value)

            self.db.session.commit()
            return rule
        except Exception as e:
            logger.error(f'更新规则失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return None

    def delete_rule(self, rule_id):
        """删除规则"""
        if not self.db:
            return False

        try:
            from .models import DefenseRule
            rule = self.db.session.query(DefenseRule).get(rule_id)
            if not rule:
                return False
            self.db.session.delete(rule)
            self.db.session.commit()
            return True
        except Exception as e:
            logger.error(f'删除规则失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return False

    def init_default_rules(self):
        """初始化默认规则（仅首次运行）"""
        if not self.db:
            return

        try:
            from .models import DefenseRule
            existing = self.db.session.query(DefenseRule).count()
            if existing > 0:
                return

            for rule_data in DEFAULT_RULES:
                rule = DefenseRule(
                    name=rule_data['name'],
                    enabled=1,
                    priority=rule_data['priority'],
                    pattern_type=rule_data['pattern_type'],
                    pattern_value=rule_data['pattern_value'],
                    action=rule_data['action'],
                    action_config=rule_data.get('action_config'),
                    cooldown_seconds=rule_data.get('cooldown_seconds', 300),
                )
                self.db.session.add(rule)

            self.db.session.commit()
            logger.info(f'已初始化 {len(DEFAULT_RULES)} 条默认防御规则')
        except Exception as e:
            logger.error(f'初始化默认规则失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
