#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统指标采集器
后台线程定期采集 CPU、内存、磁盘、DB/Redis 状态等指标
"""

import logging
import os
import platform
import threading
import time
from datetime import datetime

logger = logging.getLogger('self_healing')


class MetricsCollector:
    """系统指标采集器"""

    def __init__(self, app, config, db=None, redis_client=None):
        self.app = app
        self.config = config
        self.db = db
        self.redis = redis_client

        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = config.get('HEALTH_CACHE_TTL', 10)
        self._thread = None
        self._running = False

        # 请求统计
        self._request_count = 0
        self._error_count = 0
        self._total_response_time = 0
        self._today = datetime.now().strftime('%Y-%m-%d')

    def start(self):
        """启动后台采集线程"""
        self._running = True
        self._thread = threading.Thread(
            target=self._collect_loop,
            daemon=True,
            name='self_healing_metrics_collector'
        )
        self._thread.start()
        logger.info('Metrics Collector 线程已启动')

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _collect_loop(self):
        interval = self.config.get('METRICS_COLLECT_INTERVAL', 30)
        while self._running:
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f'指标采集失败: {e}')
            time.sleep(interval)

    def _collect_metrics(self):
        """采集系统指标"""
        metrics = {
            'system': self._get_system_metrics(),
            'database': self._get_db_status(),
            'redis': self._get_redis_status(),
            'app': self._get_app_metrics(),
            'collected_at': datetime.now().isoformat(),
        }

        self._cache = metrics
        self._cache_time = time.time()

        # 日期变更时重置计数器
        today = datetime.now().strftime('%Y-%m-%d')
        if today != self._today:
            self._today = today
            self._request_count = 0
            self._error_count = 0
            self._total_response_time = 0

    def get_metrics(self):
        """获取最新指标（带缓存）"""
        if time.time() - self._cache_time > self._cache_ttl:
            self._collect_metrics()
        return self._cache

    def record_request(self, response_time_ms, is_error=False):
        """记录一次请求（由 probe 调用）"""
        self._request_count += 1
        self._total_response_time += response_time_ms
        if is_error:
            self._error_count += 1

    def _get_system_metrics(self):
        """系统资源指标"""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process = psutil.Process(os.getpid())
            return {
                'cpu_percent': cpu,
                'memory_percent': memory.percent,
                'memory_used_mb': round(memory.used / 1024 / 1024, 1),
                'memory_total_mb': round(memory.total / 1024 / 1024, 1),
                'disk_percent': disk.percent,
                'disk_used_gb': round(disk.used / 1024 / 1024 / 1024, 1),
                'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 1),
                'process_memory_mb': round(process.memory_info().rss / 1024 / 1024, 1),
                'platform': platform.system(),
                'python_version': platform.python_version(),
            }
        except ImportError:
            return {'error': 'psutil 未安装，无法采集系统指标'}
        except Exception as e:
            return {'error': str(e)}

    def _get_db_status(self):
        """数据库状态"""
        if not self.db:
            return {'status': 'not_configured'}
        try:
            with self.app.app_context():
                start = time.time()
                self.db.session.execute(self.db.text('SELECT 1'))
                latency = round((time.time() - start) * 1000, 1)
                return {
                    'status': 'ok',
                    'latency_ms': latency,
                }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_redis_status(self):
        """Redis 状态"""
        if not self.redis:
            return {'status': 'not_configured'}
        try:
            start = time.time()
            self.redis.ping()
            latency = round((time.time() - start) * 1000, 1)
            info = self.redis.info('memory')
            return {
                'status': 'ok',
                'latency_ms': latency,
                'used_memory_mb': round(info.get('used_memory', 0) / 1024 / 1024, 1),
                'hit_rate': round(info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1) * 100, 1),
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_app_metrics(self):
        """应用指标"""
        avg_response = (
            round(self._total_response_time / self._request_count, 1)
            if self._request_count > 0 else 0
        )
        return {
            'uptime_seconds': round(time.time() - self._start_time, 0) if hasattr(self, '_start_time') else 0,
            'today_requests': self._request_count,
            'today_errors': self._error_count,
            'avg_response_ms': avg_response,
        }

    def set_start_time(self, ts):
        self._start_time = ts
