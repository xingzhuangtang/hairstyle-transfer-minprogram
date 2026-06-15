#!/usr/bin/env python3
"""
数据库表结构自动修复脚本
自动创建缺失表、添加缺失字段
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import text, inspect


def fix_tables():
    """自动修复数据库表结构问题"""
    with app.app_context():
        print("=" * 70)
        print("数据库表结构自动修复")
        print("=" * 70)
        print()

        inspector = inspect(db.engine)
        db_tables = set(inspector.get_table_names())
        model_tables = set(db.metadata.tables.keys())

        fixed_count = 0

        # 1. 创建缺失的表
        missing_tables = model_tables - db_tables
        if missing_tables:
            print("【创建缺失表】")
            for table_name in sorted(missing_tables):
                try:
                    table = db.metadata.tables[table_name]
                    table.create(db.engine, checkfirst=True)
                    print(f"  ✓ 创建表: {table_name}")
                    fixed_count += 1
                except Exception as e:
                    print(f"  ✗ 创建表 {table_name} 失败: {e}")
            print()
        else:
            print("✓ 所有表已存在，无需创建")
            print()

        # 2. 添加缺失的字段
        print("【添加缺失字段】")
        has_missing_columns = False

        for table_name in sorted(model_tables & db_tables):
            model_columns = {col.name: col for col in db.metadata.tables[table_name].columns}
            db_columns = {col['name']: col for col in inspector.get_columns(table_name)}

            missing_cols = set(model_columns.keys()) - set(db_columns.keys())

            if missing_cols:
                has_missing_columns = True
                print(f"\n  表 {table_name}:")

                for col_name in sorted(missing_cols):
                    col = model_columns[col_name]
                    try:
                        # 构建 ALTER TABLE 语句
                        col_type = _get_column_type(col)
                        nullable = "NULL" if col.nullable else "NOT NULL"
                        comment = f"COMMENT '{col.comment}'" if col.comment else ""

                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {comment}"
                        db.session.execute(text(sql))
                        print(f"    ✓ 添加字段: {col_name} ({col_type})")
                        fixed_count += 1
                    except Exception as e:
                        print(f"    ✗ 添加字段 {col_name} 失败: {e}")

        if not has_missing_columns:
            print("  ✓ 所有字段已存在，无需添加")

        db.session.commit()

        # 3. 修复枚举类型
        print()
        print("【修复枚举类型】")
        enum_fixes = [
            ("recharge_records", "payment_method", "'wechat','alipay','unionpay','wechat_virtual'"),
            ("member_orders", "payment_method", "'wechat','alipay','unionpay','wechat_virtual'"),
        ]

        for table, column, enum_values in enum_fixes:
            try:
                sql = f"ALTER TABLE {table} MODIFY COLUMN {column} ENUM({enum_values}) NOT NULL"
                db.session.execute(text(sql))
                print(f"  ✓ {table}.{column} 枚举已更新")
                fixed_count += 1
            except Exception as e:
                print(f"  ⚠ {table}.{column} 枚举更新失败（可能已是最新）: {e}")

        db.session.commit()

        # 结论
        print()
        print("=" * 70)
        print("【修复结论】")
        print("=" * 70)
        print()

        if fixed_count > 0:
            print(f"✓ 共修复 {fixed_count} 个问题")
            print()
            print("建议:")
            print("  1. 运行 python check_db_schema.py 验证修复结果")
            print("  2. 重启后端服务使更改生效")
        else:
            print("✓ 数据库表结构已是最新，无需修复")


def _get_column_type(col):
    """获取列的 SQL 类型字符串"""
    col_type = col.type
    type_class = col_type.__class__.__name__

    # 类型映射
    type_map = {
        'BigInteger': 'BIGINT',
        'Integer': 'INT',
        'SmallInteger': 'SMALLINT',
        'String': 'VARCHAR',
        'Text': 'TEXT',
        'DateTime': 'DATETIME',
        'Date': 'DATE',
        'Numeric': 'DECIMAL',
        'Float': 'FLOAT',
        'Boolean': 'TINYINT(1)',
        'LargeBinary': 'BLOB',
    }

    # 处理 ENUM 类型
    if type_class == 'Enum':
        values = ','.join([f"'{v}'" for v in col_type.enums])
        return f"ENUM({values})"

    # 获取基础类型
    base_type = type_map.get(type_class, type_class.upper())

    # 处理带长度的类型
    if type_class == 'String' and hasattr(col_type, 'length') and col_type.length:
        return f"VARCHAR({col_type.length})"

    # 处理 DECIMAL 类型
    if type_class == 'Numeric' and hasattr(col_type, 'precision') and hasattr(col_type, 'scale'):
        if col_type.precision and col_type.scale:
            return f"DECIMAL({col_type.precision},{col_type.scale})"

    return base_type


if __name__ == '__main__':
    fix_tables()
