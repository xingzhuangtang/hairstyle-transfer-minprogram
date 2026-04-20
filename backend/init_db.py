#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建数据库和表结构
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import get_config

# 导入模型
from models import (
    User, RechargeRecord, MemberOrder,
    ConsumptionRecord, HistoryRecord, MemberReminder,
    InsufficientReminder, GuestBonusRecord
)


def create_database():
    """创建数据库"""
    config = get_config()
    
    # 构建数据库连接URL（不指定数据库）
    db_url_without_db = (
        f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}"
        f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/"
    )
    
    # 使用原生SQL创建数据库
    import pymysql
    connection = pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD
    )
    
    try:
        with connection.cursor() as cursor:
            # 检查数据库是否存在
            cursor.execute(f"SHOW DATABASES LIKE '{config.MYSQL_DATABASE}'")
            result = cursor.fetchone()
            
            if result:
                print(f"✅ 数据库 '{config.MYSQL_DATABASE}' 已存在")
            else:
                # 创建数据库
                cursor.execute(
                    f"CREATE DATABASE `{config.MYSQL_DATABASE}` "
                    f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                print(f"✅ 数据库 '{config.MYSQL_DATABASE}' 创建成功")
        
        connection.commit()
    finally:
        connection.close()


def init_tables():
    """初始化表结构"""
    config = get_config()
    
    # 构建数据库连接URL
    db_url = (
        f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}"
        f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )
    
    # 创建Flask应用
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True
    
    # 初始化数据库
    from models import db
    db.init_app(app)
    
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("✅ 数据库表创建成功")
        
        # 显示创建的表
        tables = [
            'users', 'recharge_records', 'member_orders',
            'consumption_records', 'history_records', 'member_reminders',
            'insufficient_reminders', 'guest_bonus_records'
        ]
        print("\n📋 创建的表:")
        for table in tables:
            print(f"   - {table}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 开始初始化数据库")
    print("="*60 + "\n")
    
    try:
        # 创建数据库
        create_database()
        
        # 创建表结构
        init_tables()
        
        print("\n" + "="*60)
        print("🎉 数据库初始化完成！")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
