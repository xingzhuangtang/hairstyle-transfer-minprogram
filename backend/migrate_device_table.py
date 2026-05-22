#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备管理表迁移脚本
创建 devices 表用于设备管理功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def migrate():
    """执行数据库迁移"""
    with app.app_context():
        try:
            print("开始创建设备管理表...")

            # 创建 devices 表
            db.create_all()

            print("✅ 设备管理表创建成功！")
            print("\n表结构：")
            print("- id: 主键")
            print("- user_id: 用户 ID（外键关联 users 表）")
            print("- device_id: 设备唯一标识（固定不变）")
            print("- device_name: 设备名称")
            print("- device_type: 设备类型（mobile/tablet/desktop）")
            print("- is_primary: 是否为主设备")
            print("- bound_at: 绑定时间")
            print("- last_active_at: 最后活跃时间")

            return True

        except Exception as e:
            print(f"❌ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
