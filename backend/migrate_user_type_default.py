#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：修改 users 表 user_type 字段的默认值

修改内容：
1. 将 user_type 的默认值从 'registered' 改为 'guest'
2. 移除未使用的 'member' 枚举值（可选）

注意：此脚本只修改数据库默认值，不影响现有数据
"""

import pymysql
from dotenv import load_dotenv
import os

load_dotenv()


def migrate_user_type_default():
    """修改 user_type 字段默认值"""

    # 数据库配置
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", 3306))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "hairstyle_transfer")

    # 连接数据库
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )

    try:
        with connection.cursor() as cursor:
            print(f"📡 已连接到数据库：{database}")

            # 步骤 1：检查当前表结构
            print("\n📋 检查当前 user_type 字段定义...")
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, EXTRA
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'user_type'
            """, (database,))

            result = cursor.fetchone()
            if result:
                col_name, col_type, col_default, extra = result
                print(f"   当前定义:")
                print(f"   - 字段名：{col_name}")
                print(f"   - 类型：{col_type}")
                print(f"   - 默认值：{col_default}")
            else:
                print("   ⚠️ 未找到 user_type 字段")
                return

            # 步骤 2：统计当前各 user_type 的数据分布
            print("\n📊 统计当前 user_type 数据分布...")
            cursor.execute("""
                SELECT user_type, COUNT(*) as count
                FROM users
                GROUP BY user_type
            """)

            results = cursor.fetchall()
            for row in results:
                print(f"   - {row[0]}: {row[1]} 条记录")

            # 步骤 3：修改 ENUM 类型（移除 'member'，保留 'guest' 和 'registered'）
            print("\n🔧 修改 user_type 字段类型（移除未使用的 'member' 枚举值）...")
            cursor.execute("""
                ALTER TABLE users
                MODIFY COLUMN user_type ENUM('guest', 'registered')
                DEFAULT 'guest'
                COMMENT '用户类型：guest=游客（未注册），registered=已注册用户（含 VIP 会员）'
            """)

            print("✅ user_type 字段修改成功")

            # 步骤 4：验证修改结果
            print("\n✅ 验证修改结果...")
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'user_type'
            """, (database,))

            result = cursor.fetchone()
            if result:
                print(f"   - 字段名：{result[0]}")
                print(f"   - 类型：{result[1]}")
                print(f"   - 默认值：{result[2]}")
                print(f"   - 注释：{result[3]}")

            connection.commit()

            print("\n" + "="*60)
            print("🎉 数据库迁移完成！")
            print("="*60)
            print("\n修改内容：")
            print("   1. user_type 枚举值：('guest', 'registered', 'member') → ('guest', 'registered')")
            print("   2. 默认值：'registered' → 'guest'")
            print("\n注意：现有数据的 user_type 值不会改变，新插入记录默认值为 'guest'")

    except Exception as e:
        connection.rollback()
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    migrate_user_type_default()
