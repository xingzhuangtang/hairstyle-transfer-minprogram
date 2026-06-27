#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bug 知识库 V2 迁移
- system_alerts: 新增验证相关字段 + similar_bugs
- bug_knowledge: 新增验证统计字段
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


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        f"SHOW COLUMNS FROM `{table_name}` LIKE '{column_name}'"
    )
    return cursor.fetchone() is not None


def migrate():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    alert_columns = [
        ("verification_status", "VARCHAR(32) DEFAULT NULL COMMENT '验证状态: pending/verified/failed'"),
        ("verified_at", "DATETIME DEFAULT NULL COMMENT '验证时间'"),
        ("bug_knowledge_id", "VARCHAR(64) DEFAULT NULL COMMENT '关联Bug知识库ID'"),
        ("similar_bugs", "TEXT DEFAULT NULL COMMENT '相似历史Bug JSON'"),
    ]

    print('迁移 system_alerts 表...')
    for col_name, col_def in alert_columns:
        if column_exists(cursor, 'system_alerts', col_name):
            print(f'  [跳过] system_alerts.{col_name} 已存在')
        else:
            cursor.execute(f"ALTER TABLE `system_alerts` ADD COLUMN `{col_name}` {col_def}")
            print(f'  [新增] system_alerts.{col_name}')

    bug_columns = [
        ("verification_count", "INT NOT NULL DEFAULT 0 COMMENT '验证次数'"),
        ("success_count", "INT NOT NULL DEFAULT 0 COMMENT '验证成功次数'"),
        ("confidence", "FLOAT NOT NULL DEFAULT 0 COMMENT '置信度'"),
    ]

    print('\n迁移 bug_knowledge 表...')
    for col_name, col_def in bug_columns:
        if column_exists(cursor, 'bug_knowledge', col_name):
            print(f'  [跳过] bug_knowledge.{col_name} 已存在')
        else:
            cursor.execute(f"ALTER TABLE `bug_knowledge` ADD COLUMN `{col_name}` {col_def}")
            print(f'  [新增] bug_knowledge.{col_name}')

    conn.commit()
    cursor.close()
    conn.close()

    print('\n迁移完成: bug_knowledge V2 字段已就绪')


if __name__ == '__main__':
    print('Bug 知识库 V2 数据库迁移')
    print(f'数据库: {DB_CONFIG["host"]}:{DB_CONFIG["port"]}/{DB_CONFIG["database"]}')
    print()
    migrate()
