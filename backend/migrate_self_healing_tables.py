#!/usr/bin/env python3
"""
自愈系统 - 数据库表迁移
创建 system_alerts 和 evolution_logs 表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db


def migrate():
    with app.app_context():
        print("开始自愈系统数据库表迁移...")

        # 读取 SQL 文件
        sql_path = os.path.join(os.path.dirname(__file__), 'self_healing', '..', '..',
                                'self_healing_standalone', 'migrations', 'init_tables.sql')
        # 如果独立包不存在，使用内联 SQL
        if not os.path.exists(sql_path):
            sql_path = None

        if sql_path:
            with open(sql_path, 'r') as f:
                sql = f.read()
        else:
            sql = """
CREATE TABLE IF NOT EXISTS system_alerts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    alert_type VARCHAR(32) NOT NULL COMMENT '类型: error/warning/performance/security',
    severity VARCHAR(16) NOT NULL DEFAULT 'medium' COMMENT '严重级别: low/medium/high/critical',
    title VARCHAR(256) NOT NULL COMMENT '告警标题',
    description TEXT COMMENT '详细描述',
    stack_trace TEXT COMMENT '异常堆栈（脱敏后）',
    request_url VARCHAR(512) COMMENT '请求URL',
    request_method VARCHAR(16) COMMENT '请求方法',
    request_params TEXT COMMENT '请求参数（脱敏后）',
    response_data TEXT COMMENT '响应数据摘要（脱敏后）',
    user_id INT COMMENT '关联用户ID',
    user_type VARCHAR(32) COMMENT '用户类型',
    environment_info TEXT COMMENT '环境信息JSON',
    source_module VARCHAR(128) COMMENT '来源模块',
    status VARCHAR(32) NOT NULL DEFAULT 'new' COMMENT '状态: new/acknowledged/resolved/ignored',
    resolved_by VARCHAR(128) COMMENT '解决人',
    resolved_at DATETIME COMMENT '解决时间',
    resolve_note TEXT COMMENT '解决备注',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_alert_type_status (alert_type, status),
    INDEX idx_severity_created (severity, created_at),
    INDEX idx_source_module (source_module),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统异常/预警记录';

CREATE TABLE IF NOT EXISTS evolution_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    log_type VARCHAR(32) NOT NULL COMMENT '类型: fix/rule/evolution',
    related_alert_id INT COMMENT '关联告警ID',
    title VARCHAR(256) COMMENT '标题',
    description TEXT COMMENT '描述',
    action_taken TEXT COMMENT '执行的修复动作',
    rule_pattern TEXT COMMENT '防御规则模式JSON',
    effect TEXT COMMENT '效果评估JSON',
    created_by VARCHAR(128) COMMENT '创建人',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_log_type (log_type),
    INDEX idx_related_alert (related_alert_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进化档案';
"""

        # 执行 SQL
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    db.session.execute(db.text(statement))
                except Exception as e:
                    if 'already exists' in str(e).lower() or 'Duplicate' in str(e):
                        print(f"  表已存在，跳过")
                    else:
                        raise

        db.session.commit()

        # 验证
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        has_alerts = 'system_alerts' in tables
        has_evolution = 'evolution_logs' in tables

        print(f"  system_alerts: {'OK' if has_alerts else 'FAIL'}")
        print(f"  evolution_logs: {'OK' if has_evolution else 'FAIL'}")

        if has_alerts and has_evolution:
            print("\n自愈系统数据库表迁移完成！")
        else:
            print("\n迁移部分失败，请检查日志")


if __name__ == '__main__':
    migrate()
