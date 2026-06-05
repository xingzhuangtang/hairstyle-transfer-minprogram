#!/usr/bin/env python3
"""
退款申请系统数据库迁移
创建 refund_applications 表 + 更新 member_orders 表退款字段
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db

def migrate():
    with app.app_context():
        print("开始退款申请系统数据库迁移...")
        
        # ========== 1. 创建 refund_applications 表 ==========
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'refund_applications' not in tables:
            sql = """
            CREATE TABLE refund_applications (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NOT NULL,
                applicant_name VARCHAR(50) NOT NULL COMMENT '申请人姓名',
                applicant_phone VARCHAR(20) NOT NULL COMMENT '申请人电话',
                applicant_wechat_id VARCHAR(100) COMMENT '申请人微信号',
                refund_type ENUM('recharge', 'membership') NOT NULL COMMENT '退款类型',
                refund_amount DECIMAL(10,2) NOT NULL COMMENT '申请退款金额',
                reason TEXT NOT NULL COMMENT '退款原因',
                consumption_summary JSON COMMENT '消费使用情况摘要',
                suggestions TEXT COMMENT '对本项目的建议',
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending' COMMENT '审批状态',
                approved_by BIGINT NULL COMMENT '审批人ID',
                approved_at DATETIME NULL COMMENT '审批时间',
                rejection_reason TEXT NULL COMMENT '拒绝原因',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
                FOREIGN KEY (user_id) REFERENCES users(id),
                INDEX idx_user_id (user_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) COMMENT='退款申请表'
            """
            print("执行: CREATE TABLE refund_applications")
            db.session.execute(db.text(sql))
            db.session.commit()
            print("✅ refund_applications 表创建成功")
        else:
            print("ℹ️  refund_applications 表已存在")
        
        # ========== 2. 更新 member_orders 表 ==========
        columns = [col['name'] for col in inspector.get_columns('member_orders')]
        
        fields_to_add = []
        if 'refund_amount' not in columns:
            fields_to_add.append(('refund_amount', 'DECIMAL(10,2) NULL COMMENT "退款金额"'))
        if 'refunded_at' not in columns:
            fields_to_add.append(('refunded_at', 'DATETIME NULL COMMENT "退款时间"'))
        if 'refund_days' not in columns:
            fields_to_add.append(('refund_days', 'INT NULL COMMENT "退款天数(会员剩余天数)"'))
        
        for field_name, field_type in fields_to_add:
            sql = f"ALTER TABLE member_orders ADD COLUMN {field_name} {field_type}"
            print(f"执行: ALTER TABLE member_orders ADD COLUMN {field_name}")
            db.session.execute(db.text(sql))
        
        if fields_to_add:
            db.session.commit()
            print(f"✅ member_orders 表成功添加 {len(fields_to_add)} 个退款字段")
        else:
            print("ℹ️  member_orders 退款字段已存在")
        
        # ========== 3. 更新 payment_status ENUM 添加 'refunded' ==========
        # 检查当前 ENUM 是否已包含 'refunded'
        result = db.session.execute(db.text(
            "SHOW COLUMNS FROM member_orders LIKE 'payment_status'"
        )).fetchone()
        if result:
            column_type = result[1]  # e.g. "enum('pending','success','failed')"
            if 'refunded' not in column_type:
                sql = """
                ALTER TABLE member_orders 
                MODIFY COLUMN payment_status ENUM('pending', 'success', 'failed', 'refunded') 
                DEFAULT 'pending' COMMENT '支付状态'
                """
                print("执行: 更新 payment_status ENUM 添加 'refunded'")
                db.session.execute(db.text(sql))
                db.session.commit()
                print("✅ payment_status ENUM 更新成功")
            else:
                print("ℹ️  payment_status ENUM 已包含 'refunded'")
        
        print("\n🎉 退款申请系统数据库迁移完成！")

if __name__ == '__main__':
    migrate()
