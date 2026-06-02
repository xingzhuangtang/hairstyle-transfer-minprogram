#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 device_id 为 NULL 的用户数据
为所有 device_id 为空的用户生成唯一 device_id 并创建 Device 记录
"""

import sys
import os
import uuid

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Device


def fix_null_device_ids():
    """修复所有 device_id 为 NULL 的用户"""
    with app.app_context():
        # 查找所有 device_id 为 NULL 的用户
        null_device_users = User.query.filter(
            User.device_id.is_(None)
        ).all()

        if not null_device_users:
            print("✅ 所有用户都已有 device_id，无需修复")
            return

        print(f"🔍 发现 {len(null_device_users)} 个用户 device_id 为 NULL")

        fixed_count = 0
        for user in null_device_users:
            # 生成新的 device_id
            new_device_id = str(uuid.uuid4().hex)
            user.device_id = new_device_id

            # 检查是否已有该用户的设备记录
            existing_device = Device.query.filter_by(user_id=user.id).first()
            if not existing_device:
                # 创建默认设备记录
                device = Device(
                    user_id=user.id,
                    device_id=new_device_id,
                    device_name='自动生成设备',
                    device_type='unknown',
                    is_primary=True
                )
                db.session.add(device)
                print(f"  ✅ 用户 {user.id} (phone={user.phone}): device_id={new_device_id}")
            else:
                print(f"  ⚠️ 用户 {user.id} (phone={user.phone}): device_id={new_device_id} (已有Device记录)")

            fixed_count += 1

        db.session.commit()
        print(f"\n✅ 成功修复 {fixed_count} 个用户的 device_id")


if __name__ == '__main__':
    fix_null_device_ids()
