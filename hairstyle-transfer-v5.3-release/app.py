#!/usr/bin/env python3
"""
发型迁移Flask应用 - 阿里云API版本
使用头发分割API和人脸融合API实现专业发型迁移
"""

import os
import sys
import time
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image

# 导入阿里云发型迁移模块
from aliyun_hair_transfer import AliyunHairTransfer

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
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULT_FOLDER'] = 'static/results'
app.config['HAIR_EXTRACTED_FOLDER'] = 'static/hair_extracted'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}

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
        import oss2
        from datetime import datetime
        import uuid
        
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
        # 直接拼接URL (需要Bucket设置为公共读)
        public_url = f'https://{bucket_name}.{endpoint}/{object_name}'
        
        # 如果需要签名URL (更安全),使用下面的代码:
        # signed_url = bucket.sign_url('GET', object_name, 3600)  # 有效期3600秒
        # return signed_url
        
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
    except ImportError:
        raise Exception(
            "未安装oss2库!\n"
            "请运行: pip3 install oss2"
        )
    except Exception as e:
        raise Exception(f"上传失败: {e}")


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/extract-hair', methods=['POST'])
def extract_hair():
    """提取发型API"""
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
        
        hair_seg.download_hair_image(result['hair_url'], extracted_path)
        
        print(f"✅ 发型提取成功!")
        print(f"   提取的发型: {extracted_path}")
        
        # 返回结果
        original_filename = os.path.basename(hairstyle_path)
        extracted_filename = os.path.basename(extracted_path)
        
        return jsonify({
            'success': True,
            'original_url': f'/static/uploads/{original_filename}',
            'extracted_url': f'/static/hair_extracted/{extracted_filename}',
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
    """发型迁移API"""
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
        
        # 创建发型迁移服务
        print(f"\n🔧 初始化服务...")
        service = AliyunHairTransfer()
        
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
        result_url = f'/static/results/{result_filename}'
        
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
            if 'sketch_path' in info:
                sketch_filename = os.path.basename(info['sketch_path'])
                response_data['sketch_url'] = f'/static/results/{sketch_filename}'
                print(f"✅ 素描图片URL: {response_data['sketch_url']}")
        
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
    print("🚀 发型迁移系统 - 阿里云API版本")
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
    print("   访问地址: http://localhost:5002")
    print("="*60 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=5002,
        debug=True
    )
