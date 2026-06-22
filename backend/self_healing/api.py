#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控面板 API 蓝图
所有接口仅开发者可访问
"""

from flask import Blueprint, jsonify, request

monitor_bp = Blueprint('self_healing_monitor', __name__, url_prefix='/api/dev/monitor')


def _init_api(app, alert_manager, collector, db, is_developer_func,
              fixer=None, approval_manager=None, rule_engine=None, evolution_analyzer=None):
    """注册 API 路由（需要外部传入依赖）"""

    def require_dev():
        """开发者权限检查"""
        try:
            if is_developer_func():
                return None
        except Exception:
            pass
        return jsonify({'error': '无权限访问'}), 403

    @monitor_bp.route('/alerts', methods=['GET'])
    def get_alerts():
        err = require_dev()
        if err:
            return err

        try:
            from .models import SystemAlert

            page = max(int(request.args.get('page', 1)), 1)
            page_size = min(max(int(request.args.get('page_size', 20)), 1), 50)
            alert_type = request.args.get('alert_type')
            severity = request.args.get('severity')
            status = request.args.get('status')
            source_module = request.args.get('source_module')

            query = db.session.query(SystemAlert)

            if alert_type:
                query = query.filter(SystemAlert.alert_type == alert_type)
            if severity:
                query = query.filter(SystemAlert.severity == severity)
            if status:
                query = query.filter(SystemAlert.status == status)
            if source_module:
                query = query.filter(SystemAlert.source_module == source_module)

            total = query.count()
            alerts = query.order_by(SystemAlert.created_at.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                'success': True,
                'data': {
                    'items': [a.to_dict() for a in alerts],
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size if page_size > 0 else 0,
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/alerts/<int:alert_id>', methods=['GET'])
    def get_alert_detail(alert_id):
        err = require_dev()
        if err:
            return err

        try:
            from .models import SystemAlert
            alert = db.session.query(SystemAlert).get(alert_id)
            if not alert:
                return jsonify({'success': False, 'error': '告警不存在'}), 404
            return jsonify({'success': True, 'data': alert.to_dict()})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['PUT'])
    def acknowledge_alert(alert_id):
        err = require_dev()
        if err:
            return err

        try:
            from .models import SystemAlert
            alert = db.session.query(SystemAlert).get(alert_id)
            if not alert:
                return jsonify({'success': False, 'error': '告警不存在'}), 404
            alert.status = 'acknowledged'
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/alerts/<int:alert_id>/resolve', methods=['PUT'])
    def resolve_alert(alert_id):
        err = require_dev()
        if err:
            return err

        try:
            from datetime import datetime
            from .models import SystemAlert
            alert = db.session.query(SystemAlert).get(alert_id)
            if not alert:
                return jsonify({'success': False, 'error': '告警不存在'}), 404

            data = request.get_json(silent=True) or {}
            alert.status = 'resolved'
            alert.resolved_at = datetime.now()
            alert.resolved_by = data.get('resolved_by', 'developer')
            alert.resolve_note = data.get('note', '')
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/alert-stats', methods=['GET'])
    def get_alert_stats():
        err = require_dev()
        if err:
            return err

        try:
            from .models import SystemAlert
            from sqlalchemy import func as sql_func
            from datetime import datetime

            total = db.session.query(SystemAlert).count()
            by_status = dict(db.session.query(
                SystemAlert.status, sql_func.count(SystemAlert.id)
            ).group_by(SystemAlert.status).all())
            by_severity = dict(db.session.query(
                SystemAlert.severity, sql_func.count(SystemAlert.id)
            ).group_by(SystemAlert.severity).all())
            by_type = dict(db.session.query(
                SystemAlert.alert_type, sql_func.count(SystemAlert.id)
            ).group_by(SystemAlert.alert_type).all())

            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_new = db.session.query(SystemAlert).filter(SystemAlert.created_at >= today_start).count()

            return jsonify({
                'success': True,
                'data': {
                    'total': total,
                    'today_new': today_new,
                    'by_status': by_status,
                    'by_severity': by_severity,
                    'by_type': by_type,
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/system-health', methods=['GET'])
    def get_system_health():
        err = require_dev()
        if err:
            return err

        try:
            metrics = collector.get_metrics() if collector else {}
            return jsonify({'success': True, 'data': metrics})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/evolution-logs', methods=['GET'])
    def get_evolution_logs():
        err = require_dev()
        if err:
            return err

        try:
            from .models import EvolutionLog

            page = max(int(request.args.get('page', 1)), 1)
            page_size = min(max(int(request.args.get('page_size', 20)), 1), 50)

            query = db.session.query(EvolutionLog)
            total = query.count()
            logs = query.order_by(EvolutionLog.created_at.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                'success': True,
                'data': {
                    'items': [l.to_dict() for l in logs],
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ==================== Phase 2: 自动修复 ====================

    @monitor_bp.route('/fix/list', methods=['GET'])
    def get_fix_list():
        err = require_dev()
        if err:
            return err

        try:
            if not fixer:
                return jsonify({'success': False, 'error': '修复引擎未初始化'}), 503
            registry = fixer.get_fix_registry()
            return jsonify({'success': True, 'data': registry})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/fix/execute', methods=['POST'])
    def execute_fix():
        err = require_dev()
        if err:
            return err

        try:
            if not fixer:
                return jsonify({'success': False, 'error': '修复引擎未初始化'}), 503

            data = request.get_json(silent=True) or {}
            fix_id = data.get('fix_id')
            alert_id = data.get('alert_id')

            if not fix_id:
                return jsonify({'success': False, 'error': '缺少 fix_id'}), 400

            result = fixer.execute_fix(
                fix_id=fix_id,
                alert_id=alert_id,
                fix_type='manual',
                executed_by='developer',
            )
            status_code = 200 if result.get('success') else 500
            return jsonify({'success': bool(result.get('success')), 'data': result}), status_code
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/fix/history', methods=['GET'])
    def get_fix_history():
        err = require_dev()
        if err:
            return err

        try:
            from .models import FixExecution

            page = max(int(request.args.get('page', 1)), 1)
            page_size = min(max(int(request.args.get('page_size', 20)), 1), 50)

            query = db.session.query(FixExecution)
            total = query.count()
            items = query.order_by(FixExecution.executed_at.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return jsonify({
                'success': True,
                'data': {
                    'items': [i.to_dict() for i in items],
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ==================== Phase 2: 审批流 ====================

    @monitor_bp.route('/approvals', methods=['GET'])
    def get_approvals():
        err = require_dev()
        if err:
            return err

        try:
            if not approval_manager:
                return jsonify({'success': False, 'error': '审批模块未初始化'}), 503

            page = max(int(request.args.get('page', 1)), 1)
            page_size = min(max(int(request.args.get('page_size', 20)), 1), 50)
            status = request.args.get('status')

            items, total = approval_manager.get_approval_history(
                page=page, page_size=page_size, status=status,
            )

            return jsonify({
                'success': True,
                'data': {
                    'items': [i.to_dict() for i in items],
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/approvals/<int:approval_id>/approve', methods=['PUT'])
    def approve_fix(approval_id):
        err = require_dev()
        if err:
            return err

        try:
            if not approval_manager:
                return jsonify({'success': False, 'error': '审批模块未初始化'}), 503

            result = approval_manager.approve(approval_id, approved_by='developer')
            status_code = 200 if result.get('success') else 400
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/approvals/<int:approval_id>/reject', methods=['PUT'])
    def reject_fix(approval_id):
        err = require_dev()
        if err:
            return err

        try:
            if not approval_manager:
                return jsonify({'success': False, 'error': '审批模块未初始化'}), 503

            result = approval_manager.reject(approval_id, rejected_by='developer')
            status_code = 200 if result.get('success') else 400
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ==================== Phase 3: 防御规则 ====================

    @monitor_bp.route('/defense/rules', methods=['GET'])
    def get_defense_rules():
        err = require_dev()
        if err:
            return err

        try:
            if not rule_engine:
                return jsonify({'success': False, 'error': '规则引擎未初始化'}), 503

            rules = rule_engine.list_rules()
            return jsonify({
                'success': True,
                'data': [r.to_dict() for r in rules],
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/defense/rules', methods=['POST'])
    def create_defense_rule():
        err = require_dev()
        if err:
            return err

        try:
            if not rule_engine:
                return jsonify({'success': False, 'error': '规则引擎未初始化'}), 503

            data = request.get_json(silent=True) or {}
            required = ['name', 'pattern_type', 'pattern_value', 'action']
            for field in required:
                if not data.get(field):
                    return jsonify({'success': False, 'error': f'缺少字段: {field}'}), 400

            rule = rule_engine.create_rule(
                name=data['name'],
                pattern_type=data['pattern_type'],
                pattern_value=data['pattern_value'],
                action=data['action'],
                action_config=data.get('action_config'),
                priority=data.get('priority', 100),
                cooldown_seconds=data.get('cooldown_seconds', 300),
            )

            if rule:
                return jsonify({'success': True, 'data': rule.to_dict()}), 201
            return jsonify({'success': False, 'error': '创建失败'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/defense/rules/<int:rule_id>', methods=['PUT'])
    def update_defense_rule(rule_id):
        err = require_dev()
        if err:
            return err

        try:
            if not rule_engine:
                return jsonify({'success': False, 'error': '规则引擎未初始化'}), 503

            data = request.get_json(silent=True) or {}
            if 'enabled' in data:
                data['enabled'] = 1 if data['enabled'] else 0

            rule = rule_engine.update_rule(rule_id, **data)
            if rule:
                return jsonify({'success': True, 'data': rule.to_dict()})
            return jsonify({'success': False, 'error': '规则不存在'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/defense/rules/<int:rule_id>', methods=['DELETE'])
    def delete_defense_rule(rule_id):
        err = require_dev()
        if err:
            return err

        try:
            if not rule_engine:
                return jsonify({'success': False, 'error': '规则引擎未初始化'}), 503

            if rule_engine.delete_rule(rule_id):
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': '规则不存在'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ==================== Phase 3: 进化分析 ====================

    @monitor_bp.route('/evolution/analyze', methods=['POST'])
    def run_evolution_analysis():
        err = require_dev()
        if err:
            return err

        try:
            if not evolution_analyzer:
                return jsonify({'success': False, 'error': '进化分析引擎未初始化'}), 503

            report = evolution_analyzer.generate_report()
            return jsonify({'success': True, 'data': report})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/evolution/report', methods=['GET'])
    def get_evolution_report():
        err = require_dev()
        if err:
            return err

        try:
            if not evolution_analyzer:
                return jsonify({'success': False, 'error': '进化分析引擎未初始化'}), 503

            report = evolution_analyzer.get_latest_report()
            if report:
                return jsonify({'success': True, 'data': report})

            report = evolution_analyzer.generate_report()
            return jsonify({'success': True, 'data': report})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @monitor_bp.route('/health-score', methods=['GET'])
    def get_health_score():
        err = require_dev()
        if err:
            return err

        try:
            if not evolution_analyzer:
                return jsonify({'success': False, 'error': '进化分析引擎未初始化'}), 503

            score = evolution_analyzer.calculate_health_score()
            return jsonify({'success': True, 'data': score})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
