#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：创建 messages 表
用于客户留言功能
"""

import os
import sys
from flask import Flask
from config import get_config

def migrate():
    """创建 messages 表"""
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
    
    # 导入模型
    from models import db, Message
    db.init_app(app)
    
    with app.app_context():
        # 创建 messages 表
        db.create_all()
        print("✅ messages 表创建成功")
        
        # 验证表结构
        import pymysql
        connection = pymysql.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE
        )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("DESCRIBE messages")
                columns = cursor.fetchall()
                print("\n📋 messages 表结构:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]}")
        finally:
            connection.close()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 开始迁移：创建 messages 表")
    print("="*60 + "\n")
    
    try:
        migrate()
        print("\n" + "="*60)
        print("🎉 迁移完成！")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
