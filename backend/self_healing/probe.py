#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常捕获探针
在 Flask 应用中注册全局异常捕获和请求监控
"""

import functools
import logging
import time
import traceback
from datetime import datetime

logger = logging.getLogger('self_healing')


def init_probe(app, alert_manager, collector=None):
    """注册全局异常捕获和请求监控"""

    # 记录请求开始时间
    @app.before_request
    def _before_request():
        from flask import g
        g._sh_start_time = time.time()

    # 记录请求结束 + 耗时
    @app.after_request
    def _after_request(response):
        from flask import g
        start = getattr(g, '_sh_start_time', None)
        if start and collector:
            elapsed_ms = (time.time() - start) * 1000
            is_error = response.status_code >= 500
            collector.record_request(elapsed_ms, is_error)
        return response

    # 全局异常捕获（不拦截 HTTP 异常，保留 Flask 默认行为）
    @app.errorhandler(Exception)
    def _handle_exception(e):
        from flask import request, g
        from werkzeug.exceptions import HTTPException

        if isinstance(e, HTTPException):
            return e

        # 获取当前用户信息
        user_id = None
        user_type = None
        try:
            current_user = getattr(g, 'current_user', None)
            if current_user:
                user_id = getattr(current_user, 'id', None)
                user_type = getattr(current_user, 'user_type', None)
        except Exception:
            pass

        # 获取请求参数
        request_params = None
        try:
            if request.is_json:
                request_params = request.get_json(silent=True)
            elif request.args:
                request_params = dict(request.args)
            elif request.form:
                request_params = dict(request.form)
        except Exception:
            pass

        # 获取响应数据（如果有）
        response_data = None

        # 获取环境信息
        env_info = {
            'path': request.path,
            'method': request.method,
            'remote_addr': request.remote_addr,
            'user_agent': str(request.user_agent)[:200] if request.user_agent else None,
            'timestamp': datetime.now().isoformat(),
        }

        # 判断严重级别
        severity = _classify_severity(e)
        alert_type = 'error'

        # 记录告警
        alert_manager.record_alert(
            alert_type=alert_type,
            severity=severity,
            title=f'{type(e).__name__}: {str(e)[:100]}',
            description=str(e),
            stack_trace=traceback.format_exc(),
            request_url=request.url,
            request_method=request.method,
            request_params=request_params,
            response_data=response_data,
            user_id=user_id,
            user_type=user_type,
            environment_info=env_info,
            source_module=_guess_source_module(),
        )

        # 返回原始错误响应（不拦截）
        from flask import jsonify
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


def monitor_business(source_module=None):
    """
    业务函数监控装饰器
    捕获业务异常并记录告警，不拦截原始异常

    用法:
        @monitor_business(source_module='hair_service')
        def process_transfer():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000

                # 尝试获取 alert_manager（从 Flask current_app）
                try:
                    from flask import current_app, request, g
                    am = getattr(current_app, '_alert_manager', None)
                    if am:
                        user_id = None
                        user_type = None
                        try:
                            current_user = getattr(g, 'current_user', None)
                            if current_user:
                                user_id = getattr(current_user, 'id', None)
                                user_type = getattr(current_user, 'user_type', None)
                        except Exception:
                            pass

                        request_params = None
                        try:
                            if request.is_json:
                                request_params = request.get_json(silent=True)
                            elif request.args:
                                request_params = dict(request.args)
                        except Exception:
                            pass

                        env_info = {
                            'function': func.__name__,
                            'module': source_module or func.__module__,
                            'elapsed_ms': round(elapsed_ms, 1),
                            'timestamp': datetime.now().isoformat(),
                        }

                        am.record_alert(
                            alert_type='error',
                            severity=_classify_severity(e),
                            title=f'[业务异常] {func.__name__}: {str(e)[:80]}',
                            description=str(e),
                            stack_trace=traceback.format_exc(),
                            request_url=request.url if request else None,
                            request_method=request.method if request else None,
                            request_params=request_params,
                            user_id=user_id,
                            user_type=user_type,
                            environment_info=env_info,
                            source_module=source_module or func.__module__,
                        )
                except Exception:
                    pass

                # 重新抛出原始异常
                raise
        return wrapper
    return decorator


def _classify_severity(exception):
    """根据异常类型判断严重级别"""
    name = type(exception).__name__
    msg = str(exception).lower()

    # Critical: 数据库连接失败、系统级错误
    if any(k in name.lower() for k in ['connection', 'timeout', 'operational']):
        return 'critical'
    if any(k in msg for k in ['connection refused', 'database down', 'redis down']):
        return 'critical'

    # High: 支付相关、认证相关
    if any(k in name.lower() for k in ['payment', 'auth', 'permission', 'forbidden']):
        return 'high'

    # Medium: 业务逻辑错误
    if any(k in name.lower() for k in ['value', 'type', 'key', 'attribute', 'index']):
        return 'medium'

    # Low: 其他
    return 'low'


def _guess_source_module():
    """猜测异常来源模块"""
    try:
        import inspect
        frame = inspect.currentframe()
        while frame:
            filename = frame.f_code.co_filename
            if 'site-packages' not in filename and 'self_healing' not in filename:
                import os
                basename = os.path.basename(filename)
                if basename.endswith('.py'):
                    return basename[:-3]
            frame = frame.f_back
    except Exception:
        pass
    return 'unknown'
