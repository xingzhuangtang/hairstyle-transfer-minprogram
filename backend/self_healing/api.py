#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控面板 API 蓝图
所有接口仅开发者可访问
"""

from flask import Blueprint, jsonify, request

monitor_bp = Blueprint('self_healing_monitor', __name__, url_prefix='/api/dev/monitor')


def _init_api(app, alert_manager, collector, db, is_developer_func):
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
