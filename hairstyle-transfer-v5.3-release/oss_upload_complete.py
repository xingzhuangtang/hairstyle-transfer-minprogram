#!/usr/bin/env python3
"""
OSS上传完整实现 - 针对上海区域和hair-transfer-bucket
用于替换 app_aliyun.py 中的 upload_to_oss 函数
"""

import os
import oss2
from datetime import datetime
import uuid


def upload_to_oss(local_path: str) -> str:
    """
    上传文件到阿里云OSS并返回公网可访问的URL
    
    配置信息:
    - 区域: 上海 (oss-cn-shanghai)
    - Bucket: hair-transfer-bucket
    
    Args:
        local_path: 本地文件路径
    
    Returns:
        oss_url: OSS公网URL地址
    
    Raises:
        Exception: 上传失败时抛出异常
    """
    try:
        # ===== OSS配置 =====
        # 从环境变量获取AccessKey
        access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        
        # OSS配置
        endpoint = 'oss-cn-shanghai.aliyuncs.com'  # 上海区域
        bucket_name = 'hair-transfer-bucket'        # Bucket名称
        
        # 检查配置
        if not access_key_id or not access_key_secret:
            raise ValueError(
                "未设置阿里云AccessKey环境变量!\n"
                "请设置: ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET"
            )
        
        # ===== 创建OSS客户端 =====
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        
        # ===== 生成对象名称 =====
        # 获取文件扩展名
        filename = os.path.basename(local_path)
        file_ext = os.path.splitext(filename)[1]
        
        # 生成唯一的对象名称
        # 格式: hairstyle-transfer/YYYYMMDD/uuid_timestamp.ext
        date_str = datetime.now().strftime('%Y%m%d')
        unique_id = uuid.uuid4().hex[:8]
        timestamp = int(datetime.now().timestamp())
        object_name = f'hairstyle-transfer/{date_str}/{unique_id}_{timestamp}{file_ext}'
        
        # ===== 上传文件 =====
        print(f"📤 上传文件到OSS...")
        print(f"   本地路径: {local_path}")
        print(f"   对象名称: {object_name}")
        
        # 上传文件到OSS
        result = bucket.put_object_from_file(object_name, local_path)
        
        # 检查上传结果
        if result.status != 200:
            raise Exception(f"上传失败: HTTP {result.status}")
        
        # ===== 生成公网URL =====
        # 方式1: 直接拼接URL (需要Bucket设置为公共读)
        public_url = f'https://{bucket_name}.{endpoint}/{object_name}'
        
        # 方式2: 生成签名URL (推荐,更安全)
        # 有效期: 3600秒 (1小时)
        # signed_url = bucket.sign_url('GET', object_name, 3600)
        
        print(f"✅ 上传成功!")
        print(f"   公网URL: {public_url}")
        
        return public_url
        
    except oss2.exceptions.NoSuchBucket:
        raise Exception(
            f"Bucket不存在: {bucket_name}\n"
            f"请先创建Bucket或检查Bucket名称是否正确"
        )
    except oss2.exceptions.AccessDenied:
        raise Exception(
            "访问被拒绝!\n"
            "请检查:\n"
            "1. AccessKey是否正确\n"
            "2. 是否有OSS操作权限\n"
            "3. Bucket是否在当前账号下"
        )
    except oss2.exceptions.OssError as e:
        raise Exception(f"OSS错误: {e}")
    except Exception as e:
        raise Exception(f"上传失败: {e}")


def upload_to_oss_with_signed_url(local_path: str, expires: int = 3600) -> str:
    """
    上传文件到OSS并返回签名URL (更安全的方式)
    
    Args:
        local_path: 本地文件路径
        expires: URL有效期(秒),默认3600秒(1小时)
    
    Returns:
        signed_url: 带签名的临时URL
    """
    try:
        # OSS配置
        access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        endpoint = 'oss-cn-shanghai.aliyuncs.com'
        bucket_name = 'hair-transfer-bucket'
        
        if not access_key_id or not access_key_secret:
            raise ValueError("未设置阿里云AccessKey环境变量!")
        
        # 创建OSS客户端
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        
        # 生成对象名称
        filename = os.path.basename(local_path)
        file_ext = os.path.splitext(filename)[1]
        date_str = datetime.now().strftime('%Y%m%d')
        unique_id = uuid.uuid4().hex[:8]
        timestamp = int(datetime.now().timestamp())
        object_name = f'hairstyle-transfer/{date_str}/{unique_id}_{timestamp}{file_ext}'
        
        # 上传文件
        print(f"📤 上传文件到OSS...")
        print(f"   对象名称: {object_name}")
        
        result = bucket.put_object_from_file(object_name, local_path)
        
        if result.status != 200:
            raise Exception(f"上传失败: HTTP {result.status}")
        
        # 生成签名URL
        signed_url = bucket.sign_url('GET', object_name, expires)
        
        print(f"✅ 上传成功!")
        print(f"   签名URL: {signed_url[:80]}...")
        print(f"   有效期: {expires}秒")
        
        return signed_url
        
    except Exception as e:
        raise Exception(f"上传失败: {e}")


def test_oss_connection():
    """测试OSS连接"""
    try:
        print("="*60)
        print("测试OSS连接")
        print("="*60)
        
        # 获取配置
        access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        endpoint = 'oss-cn-shanghai.aliyuncs.com'
        bucket_name = 'hair-transfer-bucket'
        
        if not access_key_id or not access_key_secret:
            print("❌ 未设置AccessKey环境变量")
            return False
        
        print(f"✅ AccessKey ID: {access_key_id[:8]}...")
        print(f"✅ Endpoint: {endpoint}")
        print(f"✅ Bucket: {bucket_name}")
        
        # 创建客户端
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        
        # 测试连接
        print(f"\n🔍 测试Bucket访问...")
        bucket_info = bucket.get_bucket_info()
        
        print(f"✅ Bucket访问成功!")
        print(f"   创建时间: {bucket_info.creation_date}")
        print(f"   存储类型: {bucket_info.storage_class}")
        print(f"   访问权限: {bucket_info.acl.grant}")
        
        # 列出前5个对象
        print(f"\n📋 列出对象...")
        count = 0
        for obj in oss2.ObjectIterator(bucket, prefix='hairstyle-transfer/', max_keys=5):
            print(f"   - {obj.key}")
            count += 1
        
        if count == 0:
            print(f"   (暂无对象)")
        
        print(f"\n✅ OSS连接测试成功!")
        return True
        
    except oss2.exceptions.NoSuchBucket:
        print(f"\n❌ Bucket不存在: {bucket_name}")
        print(f"   请先创建Bucket")
        return False
    except oss2.exceptions.AccessDenied:
        print(f"\n❌ 访问被拒绝")
        print(f"   请检查AccessKey权限")
        return False
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        return False


if __name__ == '__main__':
    # 测试OSS连接
    test_oss_connection()
