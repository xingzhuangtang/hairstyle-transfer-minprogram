#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
添加普通用户/会员 4 小时赠送相关字段
"""

from models import db, User
from flask import Flask
from config import get_config
from sqlalchemy import inspect


def add_user_bonus_fields():
    """给 users 表添加普通用户/会员赠送字段"""
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

        # 检查并添加 registered_bonus_used_count 字段
        if 'registered_bonus_used_count' not in columns:
            print("添加 registered_bonus_used_count 字段...")
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE users ADD COLUMN registered_bonus_used_count "
                    "INTEGER DEFAULT 0 COMMENT '普通用户/会员免费额度使用次数'"
                ))
                conn.commit()
            print("✅ registered_bonus_used_count 字段添加成功")
        else:
            print("ℹ️ registered_bonus_used_count 字段已存在")

        # 检查并添加 last_registered_bonus_time 字段
        if 'last_registered_bonus_time' not in columns:
            print("添加 last_registered_bonus_time 字段...")
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE users ADD COLUMN last_registered_bonus_time "
                    "DATETIME COMMENT '上次普通用户/会员赠送时间'"
                ))
                conn.commit()
            print("✅ last_registered_bonus_time 字段添加成功")
        else:
            print("ℹ️ last_registered_bonus_time 字段已存在")

        # 验证结果
        columns = [col['name'] for col in inspector.get_columns('users')]
        print("\n✅ users 表字段更新完成")
        print(f"   现有字段数量：{len(columns)}")


def create_user_bonus_records_table():
    """创建 user_bonus_records 表"""
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
        tables = inspector.get_table_names()

        if 'user_bonus_records' not in tables:
            print("创建 user_bonus_records 表...")
            # 使用 SQLAlchemy 创建表
            from models import UserBonusRecord
            UserBonusRecord.__table__.create(db.engine)
            print("✅ user_bonus_records 表创建成功")
        else:
            print("ℹ️ user_bonus_records 表已存在")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 开始数据库迁移 - 添加普通用户/会员 4 小时赠送字段")
    print("="*60 + "\n")

    try:
        create_user_bonus_records_table()
        add_user_bonus_fields()

        print("\n" + "="*60)
        print("🎉 数据库迁移完成！")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ 数据库迁移失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
