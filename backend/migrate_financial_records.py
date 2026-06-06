#!/usr/bin/env python3
"""
财务流水记录系统数据库迁移
创建 financial_records 表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db


def migrate():
    with app.app_context():
        print("开始财务流水记录系统数据库迁移...")

        # ========== 1. 创建 financial_records 表 ==========
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if 'financial_records' not in tables:
            sql = """
            CREATE TABLE financial_records (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NOT NULL COMMENT '用户ID',
                record_type ENUM('recharge', 'member_purchase', 'refund', 'commission', 'withdrawal', 'cash_consumption') NOT NULL COMMENT '记录类型',
                amount DECIMAL(10,2) NOT NULL COMMENT '金额(元)，正数=收入，负数=支出',
                description VARCHAR(255) NOT NULL COMMENT '描述',
                payment_method VARCHAR(50) COMMENT '支付方式(wechat/alipay/wechat_virtual)',
                related_id BIGINT COMMENT '关联记录ID(订单号/申请号等)',
                related_type VARCHAR(50) COMMENT '关联记录类型(recharge_record/member_order/refund_application等)',
                hairs_changed INT COMMENT '关联发丝变动数量(正=获得，负=消耗)',
                status ENUM('success', 'pending', 'failed') DEFAULT 'success' COMMENT '状态',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                FOREIGN KEY (user_id) REFERENCES users(id),
                INDEX idx_user_created (user_id, created_at),
                INDEX idx_user_type (user_id, record_type),
                INDEX idx_status (status)
            ) COMMENT='财务流水记录表'
            """
            print("执行: CREATE TABLE financial_records")
            db.session.execute(db.text(sql))
            db.session.commit()
            print("✅ financial_records 表创建成功")
        else:
            print("ℹ️  financial_records 表已存在")

        print("\n🎉 财务流水记录系统数据库迁移完成！")


if __name__ == '__main__':
    migrate()
