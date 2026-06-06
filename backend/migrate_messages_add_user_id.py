#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移留言表：添加 user_id 和 status 字段
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'hairstyle_transfer'),
    charset='utf8mb4'
)

cursor = conn.cursor()

try:
    # 检查列是否存在
    cursor.execute("SHOW COLUMNS FROM messages LIKE 'user_id'")
    if not cursor.fetchone():
        print("添加 user_id 列...")
        cursor.execute(
            "ALTER TABLE messages ADD COLUMN user_id BIGINT NULL "
            "COMMENT '关联用户ID（如果已绑定）' AFTER id"
        )

    cursor.execute("SHOW COLUMNS FROM messages LIKE 'status'")
    if not cursor.fetchone():
        print("添加 status 列...")
        cursor.execute(
            "ALTER TABLE messages ADD COLUMN status ENUM('pending','processing','resolved') "
            "DEFAULT 'pending' COMMENT '处理状态' AFTER content"
        )

    # 添加索引（如果不存在）
    cursor.execute("SHOW INDEX FROM messages WHERE Key_name='idx_user_id'")
    if not cursor.fetchone():
        print("添加 idx_user_id 索引...")
        cursor.execute("ALTER TABLE messages ADD INDEX idx_user_id (user_id)")

    conn.commit()
    print("迁移完成")

except Exception as e:
    conn.rollback()
    print(f"迁移失败: {e}")
    raise
finally:
    cursor.close()
    conn.close()
