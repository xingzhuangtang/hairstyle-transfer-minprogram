"""
迁移脚本：将 payment_method 枚举类型扩展为支持 'wechat_virtual'
需要更新 recharge_records 和 member_orders 两张表
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
        # 更新 recharge_records 表
        print("Updating recharge_records.payment_method...")
        cursor.execute("""
            ALTER TABLE recharge_records 
            MODIFY COLUMN payment_method ENUM('wechat', 'alipay', 'unionpay', 'wechat_virtual') NOT NULL
        """)
        print("✅ recharge_records updated")
        
        # 更新 member_orders 表
        print("Updating member_orders.payment_method...")
        cursor.execute("""
            ALTER TABLE member_orders 
            MODIFY COLUMN payment_method ENUM('wechat', 'alipay', 'unionpay', 'wechat_virtual') NOT NULL
        """)
        print("✅ member_orders updated")
        
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
