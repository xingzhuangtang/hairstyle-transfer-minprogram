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
            from .models import SystemAlert, FixExecution

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
                'analyzed_at': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f'模式分析失败: {e}')
            return {'error': str(e)}

    def calculate_health_score(self):
        """计算综合健康评分 0-100"""
        if not self.db:
            return {'score': 0, 'error': '数据库未配置'}

        try:
            from .models import SystemAlert, FixExecution, DefenseRule

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

            total = (alert_score * 0.3 + fix_score * 0.25 +
                     system_score * 0.25 + defense_score * 0.2)
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
