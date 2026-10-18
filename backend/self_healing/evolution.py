#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进化分析引擎
基于历史告警数据的模式识别、健康评分、风险预测
"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger('self_healing')


class EvolutionAnalyzer:
    """进化分析引擎"""

    def __init__(self, app, config, db=None, collector=None):
        self.app = app
        self.config = config
        self.db = db
        self.collector = collector

    def analyze_patterns(self, days=7):
        """分析近 N 天告警模式"""
        if not self.db:
            return {'error': '数据库未配置'}

        try:
            from .models import SystemAlert, FixExecution, BugKnowledge

            since = datetime.now() - timedelta(days=days)

            alerts = self.db.session.query(SystemAlert) \
                .filter(SystemAlert.created_at >= since).all()

            if not alerts:
                return {
                    'period_days': days,
                    'total_alerts': 0,
                    'message': '该时段内无告警记录',
                }

            by_type = Counter(a.alert_type for a in alerts)
            by_severity = Counter(a.severity for a in alerts)
            by_module = Counter(a.source_module or 'unknown' for a in alerts)
            by_hour = Counter(a.created_at.hour for a in alerts)

            top_titles = Counter(a.title for a in alerts).most_common(10)

            fixes = self.db.session.query(FixExecution) \
                .filter(FixExecution.executed_at >= since).all()
            fix_success = sum(1 for f in fixes if f.status == 'success')
            fix_total = len(fixes)

            resolved = sum(1 for a in alerts if a.status == 'resolved')

            # 新增：Bug 知识库分析
            bug_stats = self._analyze_bug_trends(since)

            return {
                'period_days': days,
                'total_alerts': len(alerts),
                'by_type': dict(by_type),
                'by_severity': dict(by_severity),
                'by_module': dict(by_module.most_common(10)),
                'by_hour': {str(h): c for h, c in sorted(by_hour.items())},
                'top_titles': [{'title': t, 'count': c} for t, c in top_titles],
                'fix_stats': {
                    'total': fix_total,
                    'success': fix_success,
                    'success_rate': round(fix_success / fix_total * 100, 1) if fix_total > 0 else 0,
                },
                'resolution_rate': round(resolved / len(alerts) * 100, 1) if alerts else 0,
                'bug_stats': bug_stats,  # 新增
                'analyzed_at': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f'模式分析失败: {e}')
            return {'error': str(e)}

    def _analyze_bug_trends(self, since):
        """分析 Bug 知识库趋势"""
        try:
            from .models import BugKnowledge

            # 统计各分类的 Bug 数量
            bugs = self.db.session.query(BugKnowledge).filter(
                BugKnowledge.status == 'active'
            ).all()

            by_category = Counter(b.category for b in bugs)
            by_severity = Counter(b.severity for b in bugs)

            # 统计高置信度 Bug（可自动生成防御规则）
            high_confidence = sum(1 for b in bugs if b.confidence >= 0.7)

            # 统计近期发现的 Bug
            recent_bugs = [b for b in bugs if b.discovered_at and b.discovered_at >= since]

            # 找出复发率高的 Bug（验证次数多但成功率低）
            recurring_bugs = []
            for bug in bugs:
                if bug.verification_count and bug.verification_count >= 3:
                    success_rate = (bug.success_count or 0) / bug.verification_count
                    if success_rate < 0.5:
                        recurring_bugs.append({
                            'bug_id': bug.bug_id,
                            'title': bug.title,
                            'verification_count': bug.verification_count,
                            'success_rate': round(success_rate * 100, 1),
                        })

            return {
                'total_active': len(bugs),
                'by_category': dict(by_category),
                'by_severity': dict(by_severity),
                'high_confidence_count': high_confidence,
                'recent_count': len(recent_bugs),
                'recurring_bugs': recurring_bugs[:5],  # 最多返回 5 个
            }

        except Exception as e:
            logger.debug(f'Bug 趋势分析失败: {e}')
            return {}

    def calculate_health_score(self):
        """计算综合健康评分 0-100"""
        if not self.db:
            return {'score': 0, 'error': '数据库未配置'}

        try:
            from .models import SystemAlert, FixExecution, DefenseRule, BugKnowledge

            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)

            today_alerts = self.db.session.query(SystemAlert) \
                .filter(SystemAlert.created_at >= today_start).count()
            week_alerts = self.db.session.query(SystemAlert) \
                .filter(SystemAlert.created_at >= week_ago).count()

            alert_score = max(0, 100 - today_alerts * 10 - (week_alerts // 7) * 3)
            alert_score = min(100, alert_score)

            week_fixes = self.db.session.query(FixExecution) \
                .filter(FixExecution.executed_at >= week_ago).all()
            if week_fixes:
                success_count = sum(1 for f in week_fixes if f.status == 'success')
                fix_score = round(success_count / len(week_fixes) * 100)
            else:
                fix_score = 100

            system_score = 100
            if self.collector:
                metrics = self.collector.get_metrics()
                sys_metrics = metrics.get('system', {})
                cpu = sys_metrics.get('cpu_percent', 0)
                mem = sys_metrics.get('memory_percent', 0)
                if cpu > 90:
                    system_score -= 40
                elif cpu > 70:
                    system_score -= 20
                if mem > 90:
                    system_score -= 40
                elif mem > 70:
                    system_score -= 20
            system_score = max(0, system_score)

            total_rules = self.db.session.query(DefenseRule).count()
            enabled_rules = self.db.session.query(DefenseRule) \
                .filter(DefenseRule.enabled == 1).count()
            defense_score = round(enabled_rules / total_rules * 100) if total_rules > 0 else 50

            # 新增：Bug 知识库健康度评分
            bug_score = self._calculate_bug_health_score()

            # 调整权重，加入 Bug 知识库指标
            total = (alert_score * 0.25 + fix_score * 0.25 +
                     system_score * 0.25 + defense_score * 0.15 + bug_score * 0.1)
            total = round(max(0, min(100, total)))

            level = 'excellent' if total >= 90 else 'good' if total >= 70 else 'warning' if total >= 50 else 'critical'

            return {
                'score': total,
                'level': level,
                'breakdown': {
                    'alert_score': round(alert_score, 1),
                    'fix_score': round(fix_score, 1),
                    'system_score': round(system_score, 1),
                    'defense_score': round(defense_score, 1),
                    'bug_score': round(bug_score, 1),  # 新增
                },
                'summary': {
                    'today_alerts': today_alerts,
                    'week_alerts': week_alerts,
                    'week_fixes': len(week_fixes),
                    'enabled_rules': enabled_rules,
                },
                'calculated_at': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f'健康评分计算失败: {e}')
            return {'score': 0, 'error': str(e)}

    def _calculate_bug_health_score(self):
        """计算 Bug 知识库健康度评分"""
        try:
            from .models import BugKnowledge

            total_bugs = self.db.session.query(BugKnowledge).filter(
                BugKnowledge.status == 'active'
            ).count()

            if total_bugs == 0:
                return 100  # 没有 Bug 记录，满分

            # 高置信度 Bug 比例（越高越好，说明知识库质量高）
            high_confidence = self.db.session.query(BugKnowledge).filter(
                BugKnowledge.status == 'active',
                BugKnowledge.confidence >= 0.7,
            ).count()
            confidence_ratio = high_confidence / total_bugs

            # 复发率低的 Bug 比例（越高越好）
            recurring_bugs = self.db.session.query(BugKnowledge).filter(
                BugKnowledge.status == 'active',
                BugKnowledge.verification_count >= 3,
            ).all()

            low_recurrence_count = 0
            for bug in recurring_bugs:
                if bug.verification_count > 0:
                    success_rate = (bug.success_count or 0) / bug.verification_count
                    if success_rate >= 0.7:
                        low_recurrence_count += 1

            recurrence_ratio = low_recurrence_count / len(recurring_bugs) if recurring_bugs else 1.0

            # 综合评分：置信度占 60%，复发率占 40%
            score = confidence_ratio * 60 + recurrence_ratio * 40

            # 惩罚：如果 Bug 总数过多，扣分
            if total_bugs > 50:
                score -= (total_bugs - 50) * 0.5

            return max(0, min(100, score))

        except Exception as e:
            logger.debug(f'Bug 健康度评分计算失败: {e}')
            return 50  # 默认中等分数

    def predict_risks(self):
        """基于趋势预测潜在风险"""
        if not self.db:
            return {'error': '数据库未配置'}

        try:
            from .models import SystemAlert

            now = datetime.now()
            recent_7d = now - timedelta(days=7)
            prev_7d_start = now - timedelta(days=14)
            prev_7d_end = now - timedelta(days=7)

            recent_alerts = self.db.session.query(SystemAlert) \
                .filter(SystemAlert.created_at >= recent_7d).all()
            prev_alerts = self.db.session.query(SystemAlert) \
                .filter(
                    SystemAlert.created_at >= prev_7d_start,
                    SystemAlert.created_at < prev_7d_end,
                ).all()

            recent_count = len(recent_alerts)
            prev_count = len(prev_alerts)

            risks = []

            if prev_count > 0:
                change_rate = (recent_count - prev_count) / prev_count
                if change_rate > 0.5:
                    risks.append({
                        'level': 'high',
                        'message': f'告警数量较上周增长 {round(change_rate * 100)}%，系统稳定性下降',
                        'recent': recent_count,
                        'previous': prev_count,
                    })
                elif change_rate > 0.2:
                    risks.append({
                        'level': 'medium',
                        'message': f'告警数量较上周增长 {round(change_rate * 100)}%，需关注',
                        'recent': recent_count,
                        'previous': prev_count,
                    })
            elif recent_count > 5:
                risks.append({
                    'level': 'medium',
                    'message': f'近 7 天新增 {recent_count} 条告警（前 7 天为 0），可能出现新问题',
                })

            recent_critical = sum(1 for a in recent_alerts if a.severity == 'critical')
            if recent_critical >= 3:
                risks.append({
                    'level': 'high',
                    'message': f'近 7 天出现 {recent_critical} 次严重告警，建议立即排查',
                })

            module_counts = Counter(a.source_module for a in recent_alerts if a.source_module)
            for module, count in module_counts.most_common(3):
                if count >= 5:
                    risks.append({
                        'level': 'medium',
                        'message': f'模块 [{module}] 近 7 天告警 {count} 次，可能存在系统性问题',
                        'module': module,
                        'count': count,
                    })

            unresolved = sum(1 for a in recent_alerts if a.status == 'new')
            if unresolved > 10:
                risks.append({
                    'level': 'medium',
                    'message': f'有 {unresolved} 条告警未处理，建议及时清理',
                })

            # 新增：Bug 知识库风险预测
            bug_risks = self._predict_bug_related_risks()
            risks.extend(bug_risks)

            if not risks:
                risks.append({
                    'level': 'low',
                    'message': '系统运行平稳，未发现明显风险趋势',
                })

            return {
                'risks': risks,
                'recent_count': recent_count,
                'previous_count': prev_count,
                'predicted_at': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f'风险预测失败: {e}')
            return {'error': str(e)}

    def _predict_bug_related_risks(self):
        """基于 Bug 知识库预测风险"""
        risks = []

        try:
            from .models import BugKnowledge

            # 1. 检查复发率高的 Bug
            recurring_bugs = self.db.session.query(BugKnowledge).filter(
                BugKnowledge.status == 'active',
                BugKnowledge.verification_count >= 3,
            ).all()

            high_recurrence = []
            for bug in recurring_bugs:
                if bug.verification_count > 0:
                    success_rate = (bug.success_count or 0) / bug.verification_count
                    if success_rate < 0.5:
                        high_recurrence.append(bug)

            if high_recurrence:
                risks.append({
                    'level': 'high',
                    'message': f'发现 {len(high_recurrence)} 个高复发率 Bug（修复成功率 < 50%），需要重新审视修复方案',
                    'bug_count': len(high_recurrence),
                    'bugs': [{'bug_id': b.bug_id, 'title': b.title} for b in high_recurrence[:3]],
                })

            # 2. 检查低置信度的 Bug（可能是误判或修复不彻底）
            low_confidence = self.db.session.query(BugKnowledge).filter(
                BugKnowledge.status == 'active',
                BugKnowledge.confidence < 0.5,
            ).count()

            if low_confidence >= 5:
                risks.append({
                    'level': 'medium',
                    'message': f'有 {low_confidence} 个低置信度 Bug（< 0.5），建议复查根因分析',
                    'count': low_confidence,
                })

            # 3. 检查特定分类的 Bug 集中度
            recent_bugs = self.db.session.query(BugKnowledge).filter(
                BugKnowledge.status == 'active',
                BugKnowledge.discovered_at >= datetime.now() - timedelta(days=30),
            ).all()

            category_counts = Counter(b.category for b in recent_bugs)
            for category, count in category_counts.most_common(3):
                if count >= 5:
                    category_names = {
                        'data_type': '数据类型',
                        'deployment': '部署',
                        'security': '安全',
                        'performance': '性能',
                        'logic': '逻辑',
                    }
                    risks.append({
                        'level': 'medium',
                        'message': f'近 30 天 [{category_names.get(category, category)}] 类 Bug 集中出现 {count} 次，可能存在系统性问题',
                        'category': category,
                        'count': count,
                    })

        except Exception as e:
            logger.debug(f'Bug 风险预测失败: {e}')

        return risks

    def generate_report(self):
        """生成进化报告并写入 EvolutionLog"""
        patterns = self.analyze_patterns(days=7)
        health = self.calculate_health_score()
        risks = self.predict_risks()

        report = {
            'patterns': patterns,
            'health': health,
            'risks': risks,
            'generated_at': datetime.now().isoformat(),
        }

        if self.db:
            try:
                from .models import EvolutionLog
                log = EvolutionLog(
                    log_type='evolution',
                    title=f'进化报告 - 健康评分 {health.get("score", 0)}',
                    description=f'告警 {patterns.get("total_alerts", 0)} 条, '
                                f'风险 {len(risks.get("risks", []))} 项',
                    action_taken=json.dumps(report, ensure_ascii=False),
                    effect=json.dumps(health.get('breakdown', {}), ensure_ascii=False),
                    created_by='system',
                )
                self.db.session.add(log)
                self.db.session.commit()
            except Exception as e:
                logger.error(f'写入进化报告失败: {e}')
                try:
                    self.db.session.rollback()
                except Exception:
                    pass

        return report

    def get_latest_report(self):
        """获取最新的进化报告"""
        if not self.db:
            return None

        try:
            from .models import EvolutionLog
            log = self.db.session.query(EvolutionLog) \
                .filter(EvolutionLog.log_type == 'evolution') \
                .order_by(EvolutionLog.created_at.desc()) \
                .first()

            if log and log.action_taken:
                return json.loads(log.action_taken)
            return None
        except Exception as e:
            logger.error(f'获取进化报告失败: {e}')
            return None
