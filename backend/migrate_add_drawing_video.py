"""
迁移脚本：为 consumption_records 和 history_records 的 service_type 枚举
新增 'drawing_video' 和 'drawing_video_creative' 值
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
        new_enum = "'hair_segment','face_merge','sketch','combined','fm_step','sk_step','drawing_video','drawing_video_creative'"

        print("Updating consumption_records.service_type...")
        cursor.execute(f"""
            ALTER TABLE consumption_records
            MODIFY COLUMN service_type ENUM({new_enum}) NOT NULL
        """)
        print("✅ consumption_records.service_type updated")

        print("Updating history_records.service_type...")
        cursor.execute(f"""
            ALTER TABLE history_records
            MODIFY COLUMN service_type ENUM({new_enum}) NOT NULL
        """)
        print("✅ history_records.service_type updated")

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
