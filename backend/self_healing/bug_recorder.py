#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bug 记录器
统一的 Bug 记录、搜索、预防接口
"""

import json
import logging
import re
from datetime import datetime

logger = logging.getLogger('self_healing')


class BugRecorder:
    """Bug 记录器"""

    def __init__(self, app, db=None):
        self.app = app
        self.db = db

    def record_bug(self, bug_id, title, category, severity,
                   root_cause='', affected_files=None, fix_description='',
                   prevention='', related_alert_id=None,
                   related_evolution_log_id=None,
                   discovered_at=None, fixed_at=None):
        """
        记录 Bug 到知识库

        Args:
            bug_id: Bug 唯一标识（如 BUG-2026-001）
            title: Bug 标题
            category: 分类（data_type/deployment/security/performance/logic）
            severity: 严重级别（low/medium/high/critical）
            root_cause: 根因分析
            affected_files: 受影响文件列表
            fix_description: 修复方案
            prevention: 预防措施
            related_alert_id: 关联告警 ID
            related_evolution_log_id: 关联进化日志 ID
            discovered_at: 发现时间
            fixed_at: 修复时间

        Returns:
            BugKnowledge 对象或 None
        """
        if not self.db:
            logger.warning('数据库未配置，Bug 记录跳过')
            return None

        try:
            from .models import BugKnowledge

            # 检查是否已存在
            existing = self.db.session.query(BugKnowledge) \
                .filter(BugKnowledge.bug_id == bug_id).first()
            if existing:
                logger.info(f'Bug {bug_id} 已存在，跳过记录')
                return existing

            bug = BugKnowledge(
                bug_id=bug_id,
                title=title,
                category=category,
                severity=severity,
                root_cause=root_cause,
                affected_files=json.dumps(affected_files or [], ensure_ascii=False),
                fix_description=fix_description,
                prevention=prevention,
                related_alert_id=related_alert_id,
                related_evolution_log_id=related_evolution_log_id,
                discovered_at=discovered_at or datetime.now(),
                fixed_at=fixed_at,
            )
            self.db.session.add(bug)
            self.db.session.commit()
            logger.info(f'Bug 已记录: {bug_id} - {title}')
            return bug
        except Exception as e:
            logger.error(f'记录 Bug 失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return None

    def search_similar_bugs(self, error_message, category=None):
        """
        根据错误信息搜索相似历史 Bug

        Args:
            error_message: 错误信息
            category: 可选分类过滤

        Returns:
            匹配的 Bug 列表
        """
        if not self.db:
            return []

        try:
            from .models import BugKnowledge

            query = self.db.session.query(BugKnowledge) \
                .filter(BugKnowledge.status == 'active')

            if category:
                query = query.filter(BugKnowledge.category == category)

            bugs = query.all()
            matches = []

            error_lower = error_message.lower()

            for bug in bugs:
                # 搜索标题、根因、修复方案中的关键词
                search_text = (
                    (bug.title or '').lower() + ' ' +
                    (bug.root_cause or '').lower() + ' ' +
                    (bug.fix_description or '').lower()
                )

                # 提取错误信息中的关键词（至少3个字符）
                keywords = re.findall(r'[a-z]{3,}|[\u4e00-\u9fa5]{2,}', error_lower)

                for keyword in keywords:
                    if keyword in search_text:
                        matches.append(bug.to_dict())
                        break

            return matches
        except Exception as e:
            logger.error(f'搜索相似 Bug 失败: {e}')
            return []

    def get_prevention_rules(self, bug_id):
        """
        获取 Bug 对应的防御规则建议

        Args:
            bug_id: Bug ID

        Returns:
            防御规则建议列表
        """
        if not self.db:
            return []

        try:
            from .models import BugKnowledge

            bug = self.db.session.query(BugKnowledge) \
                .filter(BugKnowledge.bug_id == bug_id).first()

            if not bug:
                return []

            rules = []

            # 根据分类生成防御规则建议
            if bug.category == 'data_type':
                rules.append({
                    'name': f'{bug.title} - 类型防护',
                    'pattern_type': 'title_contains',
                    'pattern_value': 'DataError',
                    'action': 'auto_fix',
                    'action_config': json.dumps({'fix_id': 'amount_type_guard'}),
                    'priority': 5,
                })
            elif bug.category == 'deployment':
                rules.append({
                    'name': f'{bug.title} - 路径校验',
                    'pattern_type': 'title_contains',
                    'pattern_value': '部署路径',
                    'action': 'auto_fix',
                    'action_config': json.dumps({'fix_id': 'deploy_path_validator'}),
                    'priority': 10,
                })

            return rules
        except Exception as e:
            logger.error(f'获取防御规则失败: {e}')
            return []

    def get_all_bugs(self, category=None, status='active'):
        """
        获取所有 Bug

        Args:
            category: 可选分类过滤
            status: 状态过滤

        Returns:
            Bug 列表
        """
        if not self.db:
            return []

        try:
            from .models import BugKnowledge

            query = self.db.session.query(BugKnowledge)

            if category:
                query = query.filter(BugKnowledge.category == category)
            if status:
                query = query.filter(BugKnowledge.status == status)

            bugs = query.order_by(BugKnowledge.created_at.desc()).all()
            return [b.to_dict() for b in bugs]
        except Exception as e:
            logger.error(f'获取 Bug 列表失败: {e}')
            return []

    def archive_bug(self, bug_id):
        """
        归档 Bug

        Args:
            bug_id: Bug ID

        Returns:
            True/False
        """
        if not self.db:
            return False

        try:
            from .models import BugKnowledge

            bug = self.db.session.query(BugKnowledge) \
                .filter(BugKnowledge.bug_id == bug_id).first()

            if not bug:
                return False

            bug.status = 'archived'
            self.db.session.commit()
            logger.info(f'Bug {bug_id} 已归档')
            return True
        except Exception as e:
            logger.error(f'归档 Bug 失败: {e}')
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return False
