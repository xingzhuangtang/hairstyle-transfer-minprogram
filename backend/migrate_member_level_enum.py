"""
迁移脚本：将 member_orders.member_level 枚举类型扩展为支持 'vip'
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', 'hairstyle_transfer'),
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    try:
        # 更新 member_orders 表的 member_level 枚举
        print("Updating member_orders.member_level...")
        cursor.execute("""
            ALTER TABLE member_orders 
            MODIFY COLUMN member_level ENUM('normal', 'premium', 'vip') NOT NULL DEFAULT 'vip'
        """)
        print("✅ member_orders.member_level updated")
        
        # 同样更新 users 表的 member_level 枚举
        print("Updating users.member_level...")
        cursor.execute("""
            ALTER TABLE users 
            MODIFY COLUMN member_level ENUM('normal', 'premium', 'vip') NOT NULL DEFAULT 'normal'
        """)
        print("✅ users.member_level updated")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate()
