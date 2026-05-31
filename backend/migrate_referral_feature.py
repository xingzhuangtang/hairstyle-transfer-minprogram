#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 推广返佣功能
创建推广关系表、佣金记录表、提现记录表、本地消费记录表
添加用户表推广相关字段
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db
from app import app


def create_tables():
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        with db.engine.connect() as conn:
            if 'referral_relations' not in tables:
                conn.execute(db.text("""
                    CREATE TABLE `referral_relations` (
                        `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                        `referrer_id` BIGINT NOT NULL COMMENT '推广人用户ID',
                        `referee_id` BIGINT NOT NULL COMMENT '被推广人用户ID',
                        `scene` VARCHAR(128) NOT NULL COMMENT '小程序码scene参数',
                        `status` ENUM('pending', 'active', 'rewarded') DEFAULT 'pending' COMMENT '状态',
                        `referee_registered_at` DATETIME DEFAULT NULL,
                        `commission_paid_at` DATETIME DEFAULT NULL,
                        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY `uk_referee_id` (`referee_id`),
                        KEY `idx_referrer_id` (`referrer_id`),
                        KEY `idx_scene` (`scene`),
                        KEY `idx_status` (`status`),
                        FOREIGN KEY (`referrer_id`) REFERENCES `users`(`id`),
                        FOREIGN KEY (`referee_id`) REFERENCES `users`(`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推广关系表'
                """))
                conn.commit()
                print("✅ referral_relations 表创建成功")
            else:
                print("ℹ️ referral_relations 表已存在")

            if 'commission_records' not in tables:
                conn.execute(db.text("""
                    CREATE TABLE `commission_records` (
                        `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                        `user_id` BIGINT NOT NULL COMMENT '推广人用户ID',
                        `referee_id` BIGINT NOT NULL COMMENT '好友用户ID',
                        `referral_id` BIGINT NOT NULL COMMENT '推广关系ID',
                        `amount` DECIMAL(10,2) NOT NULL DEFAULT 0.03,
                        `reason` VARCHAR(100) NOT NULL DEFAULT 'friend_completed_2_sketches',
                        `status` ENUM('pending', 'paid') DEFAULT 'paid',
                        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                        KEY `idx_user_id` (`user_id`),
                        KEY `idx_referral_id` (`referral_id`),
                        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`),
                        FOREIGN KEY (`referee_id`) REFERENCES `users`(`id`),
                        FOREIGN KEY (`referral_id`) REFERENCES `referral_relations`(`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='佣金记录表'
                """))
                conn.commit()
                print("✅ commission_records 表创建成功")
            else:
                print("ℹ️ commission_records 表已存在")

            if 'cash_withdrawal_records' not in tables:
                conn.execute(db.text("""
                    CREATE TABLE `cash_withdrawal_records` (
                        `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                        `user_id` BIGINT NOT NULL,
                        `amount` DECIMAL(10,2) NOT NULL,
                        `status` ENUM('pending', 'processing', 'success', 'failed') DEFAULT 'pending',
                        `wechat_batch_no` VARCHAR(64) DEFAULT NULL,
                        `wechat_payment_no` VARCHAR(64) DEFAULT NULL,
                        `fail_reason` VARCHAR(255) DEFAULT NULL,
                        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                        `processed_at` DATETIME DEFAULT NULL,
                        KEY `idx_user_id` (`user_id`),
                        KEY `idx_status` (`status`),
                        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提现记录表'
                """))
                conn.commit()
                print("✅ cash_withdrawal_records 表创建成功")
            else:
                print("ℹ️ cash_withdrawal_records 表已存在")

            if 'cash_consumption_records' not in tables:
                conn.execute(db.text("""
                    CREATE TABLE `cash_consumption_records` (
                        `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                        `user_id` BIGINT NOT NULL,
                        `cash_spent` DECIMAL(10,2) NOT NULL,
                        `hairs_received` INT NOT NULL,
                        `exchange_rate` VARCHAR(50) DEFAULT NULL,
                        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                        KEY `idx_user_id` (`user_id`),
                        FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存钱罐本地消费记录表'
                """))
                conn.commit()
                print("✅ cash_consumption_records 表创建成功")
            else:
                print("ℹ️ cash_consumption_records 表已存在")


def add_user_fields():
    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]

        new_columns = {
            'cash_balance': "DECIMAL(10,2) DEFAULT 0.00 COMMENT '存钱罐余额(元)'",
            'total_referral_earnings': "DECIMAL(10,2) DEFAULT 0.00 COMMENT '累计推广收益(元)'",
            'referral_code': "VARCHAR(32) DEFAULT NULL COMMENT '用户专属推广码'",
            'referral_count': "INT DEFAULT 0 COMMENT '成功推广人数'",
        }

        with db.engine.connect() as conn:
            for col_name, col_def in new_columns.items():
                if col_name not in columns:
                    print(f"添加 {col_name} 字段...")
                    conn.execute(db.text(
                        f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                    ))
                    conn.commit()
                    print(f"✅ {col_name} 字段添加成功")
                else:
                    print(f"ℹ️ {col_name} 字段已存在")

            indexes = [idx['name'] for idx in inspector.get_indexes('users')]
            if 'idx_referral_code' not in indexes:
                print("添加 idx_referral_code 索引...")
                conn.execute(db.text(
                    "ALTER TABLE users ADD INDEX idx_referral_code (referral_code)"
                ))
                conn.commit()
                print("✅ idx_referral_code 索引添加成功")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("开始数据库迁移 - 推广返佣功能")
    print("=" * 60 + "\n")

    try:
        add_user_fields()
        create_tables()
        print("\n" + "=" * 60)
        print("数据库迁移完成！")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n数据库迁移失败：{e}")
        import traceback
        traceback.print_exc()
