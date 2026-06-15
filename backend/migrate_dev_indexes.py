#!/usr/bin/env python3
"""
开发者端客户档案功能 - 数据库索引迁移
为 consumption_records 表添加复合索引 idx_user_created_at (user_id, created_at)
用于优化客户详情查询中的消费记录分页/排序
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db


def migrate():
    with app.app_context():
        print("开始开发者端客户档案索引迁移...")

        # ========== 1. 检查 consumption_records 表是否存在 ==========
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if 'consumption_records' not in tables:
            print("❌ consumption_records 表不存在，请先运行 init_db.py")
            return

        # ========== 2. 检查现有索引 ==========
        existing_indexes = inspector.get_indexes('consumption_records')
        existing_index_names = [idx['name'] for idx in existing_indexes]

        # ========== 3. 添加复合索引 idx_user_created_at ==========
        index_name = 'idx_user_created_at'

        if index_name in existing_index_names:
            print(f"ℹ️  索引 {index_name} 已存在，跳过")
        else:
            sql = "CREATE INDEX idx_user_created_at ON consumption_records (user_id, created_at)"
            print(f"执行: {sql}")
            db.session.execute(db.text(sql))
            db.session.commit()
            print(f"✅ 索引 {index_name} 创建成功")

        print("\n🎉 开发者端客户档案索引迁移完成！")


if __name__ == '__main__':
    migrate()
