#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自愈系统 Phase 2/3 数据库迁移
新增: fix_executions, approval_records, defense_rules 三张表
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import pymysql

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'hairstyle_transfer'),
    'charset': 'utf8mb4',
}


def table_exists(cursor, table_name):
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    return cursor.fetchone() is not None


def migrate():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    tables = {
        'fix_executions': """
            CREATE TABLE IF NOT EXISTS fix_executions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fix_id VARCHAR(64) NOT NULL COMMENT '修复器ID',
                fix_name VARCHAR(128) COMMENT '修复器名称',
                alert_id INT COMMENT '关联告警ID',
                fix_type VARCHAR(16) NOT NULL COMMENT '类型: auto/manual/approved',
                risk_level VARCHAR(16) COMMENT '风险级别: low/medium/high',
                status VARCHAR(16) NOT NULL DEFAULT 'running' COMMENT '状态: running/success/failed/skipped',
                result_detail TEXT COMMENT '执行结果JSON',
                duration_ms INT COMMENT '执行耗时(毫秒)',
                executed_by VARCHAR(128) COMMENT '执行人',
                executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
                INDEX idx_fix_alert (alert_id),
                INDEX idx_fix_status (status),
                INDEX idx_fix_executed_at (executed_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='修复执行记录'
        """,
        'approval_records': """
            CREATE TABLE IF NOT EXISTS approval_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fix_id VARCHAR(64) NOT NULL COMMENT '修复器ID',
                fix_name VARCHAR(128) COMMENT '修复器名称',
                alert_id INT COMMENT '关联告警ID',
                risk_level VARCHAR(16) COMMENT '风险级别',
                fix_description TEXT COMMENT '修复方案描述',
                status VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/approved/rejected/expired',
                requested_by VARCHAR(128) COMMENT '发起人',
                approved_by VARCHAR(128) COMMENT '审批人',
                approved_at DATETIME COMMENT '审批时间',
                fix_result TEXT COMMENT '修复结果JSON',
                executed_at DATETIME COMMENT '执行时间',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                expires_at DATETIME COMMENT '过期时间',
                INDEX idx_approval_status (status),
                INDEX idx_approval_alert (alert_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批记录'
        """,
        'defense_rules': """
            CREATE TABLE IF NOT EXISTS defense_rules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(128) NOT NULL COMMENT '规则名称',
                enabled TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用: 0/1',
                priority INT NOT NULL DEFAULT 100 COMMENT '优先级(越小越高)',
                pattern_type VARCHAR(32) NOT NULL COMMENT '模式类型: title_contains/regex/source_module/frequency',
                pattern_value VARCHAR(512) NOT NULL COMMENT '模式值',
                action VARCHAR(16) NOT NULL COMMENT '动作: auto_fix/warn/suppress',
                action_config TEXT COMMENT '动作配置JSON',
                cooldown_seconds INT NOT NULL DEFAULT 300 COMMENT '冷却时间(秒)',
                hit_count INT NOT NULL DEFAULT 0 COMMENT '命中次数',
                last_hit_at DATETIME COMMENT '最后命中时间',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_rule_enabled (enabled, priority)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='防御规则表'
        """,
    }

    created = 0
    for name, ddl in tables.items():
        if table_exists(cursor, name):
            print(f'  [跳过] {name} 已存在')
        else:
            cursor.execute(ddl)
            print(f'  [创建] {name}')
            created += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f'\n迁移完成: 新建 {created} 张表')


if __name__ == '__main__':
    print('自愈系统 Phase 2/3 数据库迁移')
    print(f'数据库: {DB_CONFIG["host"]}:{DB_CONFIG["port"]}/{DB_CONFIG["database"]}')
    print()
    migrate()
