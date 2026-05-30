#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移：为 users 表添加 device_id 字段

device_id 是贯穿用户全生命周期的追踪标识，从游客到会员永不改变。
使用纯 SQL 批量更新，避免 ORM 循环导致的性能问题。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User, Device
from app import app

def migrate():
    with app.app_context():
        # 检查列是否已存在
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'device_id' in columns:
            print("✅ device_id 列已存在，跳过创建")
        else:
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE users ADD COLUMN device_id VARCHAR(64) NULL COMMENT '主设备追踪ID（永不改变）'"
                ))
                conn.execute(db.text(
                    "ALTER TABLE users ADD INDEX idx_device_id (device_id)"
                ))
                conn.commit()
            print("✅ device_id 列已创建")
        
        # 纯 SQL 批量回填已有用户的 device_id
        # 策略：优先取 is_primary=True 的设备，否则取最早的设备（按 id 排序）
        with db.engine.connect() as conn:
            # 第一步：回填有主设备的用户
            result1 = conn.execute(db.text("""
                UPDATE users u
                JOIN devices d ON u.id = d.user_id
                SET u.device_id = d.device_id
                WHERE d.is_primary = 1 AND (u.device_id IS NULL OR u.device_id = '')
            """))
            conn.commit()
            count1 = result1.rowcount if hasattr(result1, 'rowcount') else 0
            
            # 第二步：回填没有主设备的用户（取最早的 device）
            result2 = conn.execute(db.text("""
                UPDATE users u
                JOIN devices d ON u.id = d.user_id
                SET u.device_id = d.device_id
                WHERE (u.device_id IS NULL OR u.device_id = '')
                  AND d.id = (SELECT MIN(d2.id) FROM devices d2 WHERE d2.user_id = u.id)
            """))
            conn.commit()
            count2 = result2.rowcount if hasattr(result2, 'rowcount') else 0
        
        total_updated = count1 + count2
        if total_updated > 0:
            print(f"✅ 已回填 {total_updated} 个用户的 device_id（主设备: {count1}, 最早设备: {count2}）")
        else:
            print("ℹ️ 没有需要回填的用户")
        
        # 统计
        with db.engine.connect() as conn:
            total = conn.execute(db.text("SELECT COUNT(*) FROM users")).scalar()
            with_device = conn.execute(db.text(
                "SELECT COUNT(*) FROM users WHERE device_id IS NOT NULL AND device_id != ''"
            )).scalar()
        
        print(f"📊 总用户数: {total}, 已有 device_id: {with_device}, 无 device_id: {total - with_device}")

if __name__ == '__main__':
    migrate()
