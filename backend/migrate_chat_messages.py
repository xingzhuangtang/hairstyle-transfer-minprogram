#!/usr/bin/env python3
"""
实时聊天系统数据库迁移
创建 chat_messages 表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db


def migrate():
    with app.app_context():
        print("开始实时聊天系统数据库迁移...")

        # ========== 1. 创建 chat_messages 表 ==========
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if 'chat_messages' not in tables:
            sql = """
            CREATE TABLE chat_messages (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NOT NULL COMMENT '关联用户ID',
                sender_type ENUM('user', 'admin') NOT NULL COMMENT '发送者类型',
                content TEXT NOT NULL COMMENT '消息内容',
                is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读（对admin消息而言）',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                FOREIGN KEY (user_id) REFERENCES users(id),
                INDEX idx_user_created (user_id, created_at),
                INDEX idx_user_unread (user_id, sender_type, is_read)
            ) COMMENT='实时聊天消息表'
            """
            print("执行: CREATE TABLE chat_messages")
            db.session.execute(db.text(sql))
            db.session.commit()
            print("✅ chat_messages 表创建成功")
        else:
            print("ℹ️  chat_messages 表已存在")

        print("\n🎉 实时聊天系统数据库迁移完成！")


if __name__ == '__main__':
    migrate()
