#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发型迁移Flask应用 - Web简化版本
使用头发分割API和人脸融合API实现专业发型迁移
不依赖数据库，适合本地开发测试
"""

import os
import time
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ 已加载.env环境变量")
except ImportError:
    print("⚠️  未安装python-dotenv，使用系统环境变量")

# 导入阿里云发型迁移模块(修复版)
from aliyun_hair_transfer_fixed import AliyunHairTransferFixed

# 导入头发分割模块
try:
    from hair_segmentation import HairSegmentation
    HAIR_SEG_AVAILABLE = True
except ImportError as e:
    HAIR_SEG_AVAILABLE = False
    HairSegmentation = None
    print(f"⚠️  头发分割模块不可用: {e}")

# 导入可选模块(容错)
try:
    from image_preprocessor import ImagePreprocessor
    PREPROCESSOR_AVAILABLE = True
except ImportError as e:
    PREPROCESSOR_AVAILABLE = False
    ImagePreprocessor = None
    print(f"⚠️  图像预处理模块不可用: {e}")

try:
    from sketch_converter import SketchConverter
    SKETCH_AVAILABLE = True
except ImportError as e:
    SKETCH_AVAILABLE = False
    SketchConverter = None
    print(f"⚠️  素描转换模块不可用: {e}")

# Flask应用配置
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULT_FOLDER'] = 'static/results'
app.config['HAIR_EXTRACTED_FOLDER'] = 'static/hair_extracted'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}


def get_full_url(relative_path):
    """
    生成完整的URL（用于返回给小程序）
    
    Args:
        relative_path: 相对路径，如 '/static/hair_extracted/file.png'
    
    Returns:
        str: 完整URL，如 'http://localhost:5003/static/hair_extracted/file.png'
    """
    # 在请求上下文中获取协议和主机
    try:
        protocol = request.scheme
        host = request.host
        return f'{protocol}://{host}{relative_path}'
    except RuntimeError:
        # 如果不在请求上下文中（如测试），返回默认URL
        return f'http://localhost:5003{relative_path}'

# 创建必要的目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
os.makedirs(app.config['HAIR_EXTRACTED_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload_file(file, prefix='image'):
    """保存上传的文件并预处理"""
    if not file or not allowed_file(file.filename):
        raise ValueError("不支持的文件格式")
    
    # 生成唯一文件名
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # 保存原始文件
    file.save(filepath)
    
    # 图像预处理(如果可用)
    if PREPROCESSOR_AVAILABLE:
        try:
            preprocessor = ImagePreprocessor()
            processed_path, info = preprocessor.preprocess_image(filepath)
            
            print(f"✅ 图像预处理完成:")
            print(f"   原始: {info['original_size']/1024:.1f}KB")
            print(f"   最终: {info['final_size']/1024:.1f}KB")
            
            # 如果进行了处理,删除原始文件
            if info['resized'] or info['compressed']:
                if os.path.exists(filepath) and filepath != processed_path:
                    os.remove(filepath)
                return processed_path
            else:
                return filepath
        except Exception as e:
            print(f"⚠️  图像预处理失败: {e}")
            print(f"   使用原始文件")
            return filepath
    else:
        print(f"   跳过预处理(模块不可用)")
        return filepath


def upload_to_oss(local_path: str, max_retries: int = 3) -> str:
    """
    上传文件到阿里云OSS并返回公网可访问的URL
    
    配置信息:
    - 区域: 上海 (oss-cn-shanghai)
    - Bucket: hair-transfer-bucket
    - 超时设置: 180秒连接 + 120秒读取 (企业网络优化)
    - 重试机制: 最多重试3次 (网络超时友好)
    
    Args:
        local_path: 本地文件路径
        max_retries: 最大重试次数
    
    Returns:
        oss_url: OSS公网URL地址
    
    Raises:
        Exception: 上传失败时抛出异常
    """
    import oss2
    from datetime import datetime
    import uuid
    import requests
    import urllib3
    
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
    
    # ===== 重试上传机制 =====
    for attempt in range(max_retries):
        try:
            print(f"📤 上传文件到OSS... (尝试 {attempt + 1}/{max_retries})")
            print(f"   本地路径: {local_path}")
            print(f"   对象名称: {object_name}")
            
            # ===== 创建OSS客户端 =====
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            
            # 企业网络优化：通过会话配置超时
            # 在重试机制中处理网络超时问题
            print(f"   启用企业网络模式：3次重试 + 指数退避")
            
            # 上传文件到OSS
            result = bucket.put_object_from_file(object_name, local_path)
            
            # 检查上传结果
            if result.status != 200:
                raise Exception(f"上传失败: HTTP {result.status}")
            
            # ===== 生成公网URL =====
            # 直接拼接URL (需要Bucket设置为公共读)
            public_url = f'https://{bucket_name}.{endpoint}/{object_name}'
            
            print(f"✅ 上传成功!")
            print(f"   公网URL: {public_url}")
            
            return public_url
            
        except (oss2.exceptions.RequestError, 
                requests.exceptions.ReadTimeout,
                requests.exceptions.Timeout,
                urllib3.exceptions.ReadTimeoutError,
                urllib3.exceptions.ConnectTimeoutError) as e:
            
            error_msg = str(e)
            print(f"❌ 上传尝试 {attempt + 1} 失败: {error_msg}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # 5, 10, 15秒
                print(f"   等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                # 最后一次尝试失败
                raise Exception(
                    f"上传失败 (已重试{max_retries}次): {error_msg}\n"
                    f"可能原因:\n"
                    f"1. 网络连接不稳定\n"
                    f"2. 文件过大\n"
                    f"3. 企业网络/代理设置问题\n"
                    f"4. OSS服务暂时不可用\n"
                    f"\n建议:\n"
                    f"- 检查网络连接\n"
                    f"- 尝试较小尺寸的图片\n"
                    f"- 稍后重试"
                )
                
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
        except ImportError as e:
            raise Exception(
                "未安装必要的库!\n"
                f"错误: {e}\n"
                "请运行: pip3 install oss2 requests urllib3"
            )
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 上传尝试 {attempt + 1} 失败: {error_msg}")
            
            # 非网络错误不重试
            if 'NoSuchBucket' in error_msg or 'AccessDenied' in error_msg:
                raise Exception(f"配置错误: {error_msg}")
            
            # 其他未知错误，最后一次尝试失败时抛出
            if attempt == max_retries - 1:
                raise Exception(f"上传失败 (已重试{max_retries}次): {error_msg}")
            
            # 等待后重试
            wait_time = (attempt + 1) * 3
            print(f"   等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/extract-hair', methods=['POST'])
def extract_hair():
    """提取发型API（简化版本，无需认证）"""
    try:
        # 检查头发分割模块是否可用
        if not HAIR_SEG_AVAILABLE:
            return jsonify({
                'error': '头发分割功能不可用',
                'message': '请检查hair_segmentation模块是否正确安装'
            }), 503
        
        # 检查文件
        if 'hairstyle_image' not in request.files:
            return jsonify({'error': '缺少发型参考图'}), 400
        
        hairstyle_file = request.files['hairstyle_image']
        
        # 保存上传的文件
        print(f"\n📤 保存发型参考图...")
        hairstyle_path = save_upload_file(hairstyle_file, 'hairstyle')
        print(f"   发型图: {hairstyle_path}")
        
        # 上传到OSS获取URL
        print(f"\n☁️  上传到OSS...")
        try:
            hairstyle_url = upload_to_oss(hairstyle_path)
        except Exception as e:
            return jsonify({
                'error': 'OSS上传失败',
                'message': str(e)
            }), 500
        
        # 提取发型
        print(f"\n✂️  提取发型...")
        hair_seg = HairSegmentation()
        
        # 调用头发分割API
        result = hair_seg.segment_hair(image_url=hairstyle_url)
        
        if not result['success']:
            return jsonify({
                'error': '发型提取失败',
                'message': result['message']
            }), 500
        
        # 下载提取的发型图
        print(f"\n📥 下载提取的发型...")
        output_filename = f"hair_extracted_{uuid.uuid4().hex[:8]}.png"
        extracted_path = os.path.join(app.config['HAIR_EXTRACTED_FOLDER'], output_filename)
        
        download_success = hair_seg.download_hair_image(result['hair_url'], extracted_path)
        
        # 检查下载是否成功
        if not download_success or not os.path.exists(extracted_path):
            return jsonify({
                'error': '发型图片下载失败',
                'message': '阿里云API返回的图片无法下载，请稍后重试'
            }), 500
        
        print(f"✅ 发型提取成功!")
        print(f"   提取的发型: {extracted_path}")
        
        # 返回结果
        original_filename = os.path.basename(hairstyle_path)
        extracted_filename = os.path.basename(extracted_path)
        
        # 生成完整URL
        original_url = get_full_url(f'/static/uploads/{original_filename}')
        extracted_url = get_full_url(f'/static/hair_extracted/{extracted_filename}')
        
        return jsonify({
            'success': True,
            'original_url': original_url,
            'extracted_url': extracted_url,
            'message': '发型提取成功'
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"❌ 发型提取失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'发型提取失败: {str(e)}'}), 500


@app.route('/api/transfer', methods=['POST'])
def transfer_hairstyle():
    """发型迁移API（简化版本，无需认证）"""
    try:
        # 检查文件
        if 'customer_image' not in request.files:
            return jsonify({'error': '缺少客户照片'}), 400
        
        # 检查是否提供了原始发型图路径
        original_hair_url = request.form.get('original_hair_url')
        if not original_hair_url:
            return jsonify({'error': '缺少原始发型图'}), 400
        
        customer_file = request.files['customer_image']
        
        # 保存客户照片
        print(f"\n📤 保存客户照片...")
        customer_path = save_upload_file(customer_file, 'customer')
        print(f"   客户图: {customer_path}")
        
        # 从URL获取原始发型图本地路径
        # original_hair_url格式: /static/uploads/xxxx.jpg
        original_filename = original_hair_url.split('/')[-1]
        hairstyle_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        
        if not os.path.exists(hairstyle_path):
            return jsonify({'error': '原始发型图不存在,请重新上传'}), 400
        
        print(f"   发型图(原始): {hairstyle_path}")
        
        # 上传到OSS获取URL
        print(f"\n☁️  上传到OSS...")
        try:
            hairstyle_url = upload_to_oss(hairstyle_path)  # 使用原始发型图
            customer_url = upload_to_oss(customer_path)
        except NotImplementedError as e:
            return jsonify({
                'error': '请先配置OSS上传功能',
                'message': str(e),
                'help': '阿里云API需要公网可访问的图像URL,请配置OSS后重试'
            }), 501
        
        # 获取参数
        model_version = request.form.get('model_version', 'v1')
        face_blend_ratio = float(request.form.get('face_blend_ratio', '0.5'))
        enable_sketch = request.form.get('enable_sketch', 'false').lower() == 'true'
        sketch_style = request.form.get('sketch_style', 'artistic')
        
        # 检查素描功能是否可用
        if enable_sketch and not SKETCH_AVAILABLE:
            print(f"\n⚠️  素描模块不可用,将跳过素描转换")
            enable_sketch = False
        
        print(f"\n⚙️  处理参数:")
        print(f"   模型版本: {model_version}")
        print(f"   脸型融合权重: {face_blend_ratio}")
        print(f"   素描效果: {enable_sketch}")
        if enable_sketch:
            print(f"   素描风格: {sketch_style}")
        
        # 创建发型迁移服务(修复版)
        print(f"\n🔧 初始化服务...")
        service = AliyunHairTransferFixed()
        
        # 执行发型迁移
        result_image, info = service.transfer_hairstyle(
            hairstyle_image_url=hairstyle_url,
            customer_image_url=customer_url,
            model_version=model_version,
            face_blend_ratio=face_blend_ratio,
            save_dir=app.config['RESULT_FOLDER'],
            enable_sketch=enable_sketch,
            sketch_style=sketch_style
        )
        
        # 返回结果
        result_filename = os.path.basename(info['save_path'])
        result_url = get_full_url(f'/static/results/{result_filename}')
        
        # 构建返回信息
        response_data = {
            'success': True,
            'result_url': result_url,
            'info': {
                'elapsed_time': info['elapsed_time'],
                'template_id': info['template_id'],
                'model_version': model_version
            }
        }
        
        # 添加素描信息
        if enable_sketch:
            response_data['info']['sketch_enabled'] = True
            response_data['info']['sketch_style'] = sketch_style
            response_data['info']['sketch_method'] = info.get('sketch_method', 'unknown')
            
            # 如果有素描图片，添加URL
            if 'sketch_path' in info and info['sketch_path']:
                sketch_filename = os.path.basename(info['sketch_path'])
                response_data['sketch_url'] = get_full_url(f'/static/results/{sketch_filename}')
                print(f"✅ 素描图片URL: {response_data['sketch_url']}")
            elif 'sketch_error' in info:
                # 素描失败但启用了，添加错误信息
                print(f"⚠️  素描转换失败: {info['sketch_error']}")
                response_data['info']['sketch_error'] = info['sketch_error']
            else:
                print(f"⚠️  素描功能未启用或不可用")
        
        return jsonify(response_data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 检查环境变量
        has_access_key = bool(os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'))
        has_secret = bool(os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET'))
        
        return jsonify({
            'status': 'ok' if (has_access_key and has_secret) else 'warning',
            'access_key_configured': has_access_key,
            'secret_configured': has_secret,
            'message': '服务正常' if (has_access_key and has_secret) else '请配置AccessKey'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 发型迁移系统 - Web简化版本")
    print("="*60)
    
    # 检查环境变量
    if not os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'):
        print("\n❌ 错误: 未设置阿里云AccessKey")
        print("\n请设置环境变量:")
        print("export ALIBABA_CLOUD_ACCESS_KEY_ID='your-key-id'")
        print("export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your-key-secret'")
        print("\n然后重新启动应用")
        sys.exit(1)
    
    print("\n✅ 环境变量配置正确")
    print(f"   AccessKey ID: {os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')[:8]}...")
    
    print("\n⚠️  重要提示:")
    print("   1. 请确保已开通阿里云视觉智能服务")
    print("   2. 请配置OSS上传功能(修改upload_to_oss函数)")
    print("   3. 图像必须上传到OSS并使用公网URL")
    
    print("\n🌐 启动Flask应用...")
    print("   访问地址: http://localhost:5003")
    print("="*60 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=5003,
        debug=True
    )
