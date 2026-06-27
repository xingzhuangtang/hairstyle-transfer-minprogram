#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bug 知识库数据库迁移
创建 bug_knowledge 表
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

    ddl = """
        CREATE TABLE IF NOT EXISTS bug_knowledge (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bug_id VARCHAR(64) NOT NULL UNIQUE COMMENT 'Bug唯一标识',
            title VARCHAR(256) NOT NULL COMMENT 'Bug标题',
            category VARCHAR(32) NOT NULL COMMENT '分类: data_type/deployment/security/performance/logic',
            severity VARCHAR(16) NOT NULL COMMENT '严重级别: low/medium/high/critical',
            root_cause TEXT COMMENT '根因分析',
            affected_files TEXT COMMENT '受影响文件列表JSON',
            fix_description TEXT COMMENT '修复方案',
            prevention TEXT COMMENT '预防措施',
            related_alert_id INT COMMENT '关联告警ID',
            related_evolution_log_id INT COMMENT '关联进化日志ID',
            status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态: active/archived',
            discovered_at DATETIME COMMENT '发现时间',
            fixed_at DATETIME COMMENT '修复时间',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            INDEX idx_bug_category (category),
            INDEX idx_bug_status (status),
            INDEX idx_bug_severity (severity)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Bug知识库表'
    """

    if table_exists(cursor, 'bug_knowledge'):
        print('  [跳过] bug_knowledge 已存在')
    else:
        cursor.execute(ddl)
        print('  [创建] bug_knowledge')

    conn.commit()
    cursor.close()
    conn.close()

    print('\n迁移完成: bug_knowledge 表已就绪')


if __name__ == '__main__':
    print('Bug 知识库数据库迁移')
    print(f'数据库: {DB_CONFIG["host"]}:{DB_CONFIG["port"]}/{DB_CONFIG["database"]}')
    print()
    migrate()
