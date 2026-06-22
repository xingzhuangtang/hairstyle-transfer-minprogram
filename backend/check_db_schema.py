#!/usr/bin/env python3
"""
数据库表结构完整性检查脚本
检查所有模型定义的表是否存在，字段是否完整
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import text, inspect


def check_tables():
    """检查所有模型定义的表是否存在"""
    with app.app_context():
        print("=" * 70)
        print("数据库表结构完整性检查")
        print("=" * 70)
        print()

        # 获取模型定义的表
        model_tables = sorted(db.metadata.tables.keys())

        # 获取数据库实际表
        inspector = inspect(db.engine)
        db_tables = set(inspector.get_table_names())

        missing_tables = []
        extra_tables = []

        print("【表存在性检查】")
        print(f"模型定义表数: {len(model_tables)}")
        print(f"数据库实际表数: {len(db_tables)}")
        print()

        for table in model_tables:
            if table in db_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} [缺失]")
                missing_tables.append(table)

        # 检查数据库额外表
        extra_tables = db_tables - set(model_tables)
        if extra_tables:
            print()
            print("数据库额外表（非模型定义）:")
            for t in sorted(extra_tables):
                print(f"  - {t}")

        print()
        print("=" * 70)
        print("【字段完整性检查】")
        print("=" * 70)
        print()

        missing_columns = {}

        for table_name in model_tables:
            if table_name not in db_tables:
                continue

            # 获取模型定义的字段
            model_columns = {col.name: col for col in db.metadata.tables[table_name].columns}

            # 获取数据库实际字段
            db_columns = {col['name'] for col in inspector.get_columns(table_name)}

            table_missing = set(model_columns.keys()) - db_columns
            if table_missing:
                missing_columns[table_name] = list(table_missing)
                print(f"  ✗ {table_name}: 缺少字段 {table_missing}")
            else:
                print(f"  ✓ {table_name}: 字段完整")

        print()
        print("=" * 70)
        print("【检查结论】")
        print("=" * 70)
        print()

        issues = []
        if missing_tables:
            issues.append(f"缺失表: {missing_tables}")
        if missing_columns:
            for table, cols in missing_columns.items():
                issues.append(f"{table} 缺少字段: {cols}")

        if issues:
            print(f"发现 {len(issues)} 个问题:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            print()
            print("运行 python fix_db_schema.py 自动修复")
            return False
        else:
            print("✓ 数据库表结构完整，与模型定义一致")
            return True


if __name__ == '__main__':
    success = check_tables()
    sys.exit(0 if success else 1)
