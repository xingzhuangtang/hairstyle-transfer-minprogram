#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移 User 表：添加 refund_enabled 字段
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
    cursor.execute("SHOW COLUMNS FROM users LIKE 'refund_enabled'")
    if not cursor.fetchone():
        print("添加 refund_enabled 列...")
        cursor.execute(
            "ALTER TABLE users ADD COLUMN refund_enabled TINYINT(1) "
            "DEFAULT 0 COMMENT '退款申请权限' "
            "AFTER last_registered_bonus_time"
        )

    conn.commit()
    print("迁移完成")

except Exception as e:
    conn.rollback()
    print(f"迁移失败: {e}")
    raise
finally:
    cursor.close()
    conn.close()
