#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
添加访客模式相关字段到 users 表
"""

from models import db, User
from flask import Flask
from config import get_config
from sqlalchemy import inspect


def add_guest_fields_to_users():
    """给 users 表添加访客模式字段"""
    config = get_config()
    db_url = (
        f'mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}'
        f'@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}'
        f'?charset=utf8mb4'
    )

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True

    db.init_app(app)

    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]

        # 检查并添加 user_type 字段
        if 'user_type' not in columns:
            print("添加 user_type 字段...")
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE users ADD COLUMN user_type "
                    "ENUM('guest', 'registered', 'member') DEFAULT 'registered' "
                    "COMMENT '用户类型：guest=游客，registered=已注册，member=会员'"
                ))
                conn.commit()
            print("✅ user_type 字段添加成功")
        else:
            print("ℹ️ user_type 字段已存在")

        # 检查并添加 guest_bonus_used_count 字段
        if 'guest_bonus_used_count' not in columns:
            print("添加 guest_bonus_used_count 字段...")
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE users ADD COLUMN guest_bonus_used_count "
                    "INTEGER DEFAULT 0 COMMENT '游客免费额度使用次数'"
                ))
                conn.commit()
            print("✅ guest_bonus_used_count 字段添加成功")
        else:
            print("ℹ️ guest_bonus_used_count 字段已存在")

        # 检查并添加 last_guest_bonus_time 字段
        if 'last_guest_bonus_time' not in columns:
            print("添加 last_guest_bonus_time 字段...")
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE users ADD COLUMN last_guest_bonus_time "
                    "DATETIME COMMENT '上次游客赠送时间'"
                ))
                conn.commit()
            print("✅ last_guest_bonus_time 字段添加成功")
        else:
            print("ℹ️ last_guest_bonus_time 字段已存在")

        # 验证结果
        columns = [col['name'] for col in inspector.get_columns('users')]
        print("\n✅ users 表字段更新完成")
        print(f"   现有字段数量：{len(columns)}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 开始数据库迁移 - 添加访客模式字段")
    print("="*60 + "\n")

    try:
        add_guest_fields_to_users()

        print("\n" + "="*60)
        print("🎉 数据库迁移完成！")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ 数据库迁移失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
