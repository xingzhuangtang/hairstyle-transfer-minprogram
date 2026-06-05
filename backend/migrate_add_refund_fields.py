#!/usr/bin/env python3
"""
添加充值记录退款字段
为 recharge_records 表添加 refund_no, refund_amount, refunded_at 字段
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db

def migrate():
    with app.app_context():
        # 检查字段是否已存在
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('recharge_records')]
        
        fields_to_add = []
        
        if 'refund_no' not in columns:
            fields_to_add.append(('refund_no', 'VARCHAR(64) NULL COMMENT "退款单号"'))
        
        if 'refund_amount' not in columns:
            fields_to_add.append(('refund_amount', 'DECIMAL(10,2) NULL COMMENT "退款金额"'))
        
        if 'refunded_at' not in columns:
            fields_to_add.append(('refunded_at', 'DATETIME NULL COMMENT "退款时间"'))
        
        if not fields_to_add:
            print("✅ 所有退款字段已存在，无需迁移")
            return
        
        for field_name, field_type in fields_to_add:
            sql = f"ALTER TABLE recharge_records ADD COLUMN {field_name} {field_type}"
            print(f"执行: {sql}")
            db.session.execute(db.text(sql))
        
        db.session.commit()
        print(f"✅ 成功添加 {len(fields_to_add)} 个退款字段")

if __name__ == '__main__':
    migrate()
