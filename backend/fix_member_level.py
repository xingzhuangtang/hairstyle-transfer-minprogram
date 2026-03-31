#!/usr/bin/env python3
"""
修复 member_level 字段类型
将 ENUM 改为 VARCHAR
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from models import db
from flask import Flask

# 创建 Flask 应用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root@localhost/hairstyle_transfer')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # 执行 SQL 修改列类型
    try:
        db.session.execute(db.text("""
            ALTER TABLE member_orders
            MODIFY COLUMN member_level VARCHAR(20) NOT NULL DEFAULT 'vip' COMMENT '会员等级'
        """))
        db.session.commit()
        print("✅ member_orders.member_level 已修改为 VARCHAR(20)")
    except Exception as e:
        print(f"⚠️ member_orders 修改失败：{e}")
        db.session.rollback()

    # 检查 users 表的 member_level 字段
    try:
        db.session.execute(db.text("""
            ALTER TABLE users
            MODIFY COLUMN member_level VARCHAR(20) NOT NULL DEFAULT 'normal' COMMENT '会员等级'
        """))
        db.session.commit()
        print("✅ users.member_level 已修改为 VARCHAR(20)")
    except Exception as e:
        print(f"⚠️ users 修改失败：{e}")
        db.session.rollback()

print("✅ 数据库表结构更新完成!")
