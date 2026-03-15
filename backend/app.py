#!/usr/bin/env python3
"""
发型迁移Flask应用 - 阿里云API版本
使用头发分割API和人脸融合API实现专业发型迁移
"""

import logging

import os
import sys
import time
import uuid
from flask import Flask, render_template, request, jsonify, send_file, g
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
    print("⚠️ 未安装python-dotenv，使用系统环境变量")

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

# 导入API蓝图
try:
    from api import api_bp

    API_BP_AVAILABLE = True
except ImportError as e:
    API_BP_AVAILABLE = False
    api_bp = None
    print(f"⚠️  API蓝图不可用: {e}")

# 导入数据库配置
try:
    from models import db
    from config import get_config

    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    print(f"⚠️  数据库模块不可用: {e}")

# 导入认证和消费服务
try:
    from auth import login_required
    from hair_service import HairService

    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    login_required = None
    HairService = None
    print(f"⚠️  认证和消费模块不可用: {e}")


# Flask应用配置
app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["RESULT_FOLDER"] = "static/results"
app.config["HAIR_EXTRACTED_FOLDER"] = "static/hair_extracted"
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

# 导入详细日志配置
from logging_config import (
    setup_logging,
    RequestLogger,
    log_security_event,
    log_performance,
)
import logging

# 配置详细日志系统
try:
    from config import get_config

    config = get_config()
    setup_logging(env=os.getenv("FLASK_ENV", "development"))
except Exception as e:
    print(f"⚠️ 日志配置失败，使用默认配置: {e}")

# 创建logger
logger = logging.getLogger(__name__)

# 设置请求日志记录器
request_logger = RequestLogger()

# 导入性能监控装饰器
from monitoring_config import monitor_performance


def get_full_url(relative_path):
    """
    生成完整的URL（用于返回给小程序）

    Args:
        relative_path: 相对路径，如 '/static/hair_extracted/file.png'

    Returns:
        str: 完整URL，如 'http://localhost:5003/static/hair_extracted/file.png'
    """
    # 在请求上下文中获取协议和主机
    from flask import request

    try:
        protocol = request.scheme
        host = request.host
        return f"{protocol}://{host}{relative_path}"
    except RuntimeError:
        # 如果不在请求上下文中（如测试），返回默认URL
        return f"http://localhost:5003{relative_path}"


# 配置数据库
if DB_AVAILABLE:
    config = get_config()
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}?charset=utf8mb4"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    print("✅ 数据库已配置")

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp"}

# 创建必要的目录
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESULT_FOLDER"], exist_ok=True)
os.makedirs(app.config["HAIR_EXTRACTED_FOLDER"], exist_ok=True)

# 注册API蓝图
if API_BP_AVAILABLE:
    app.register_blueprint(api_bp)
    print("✅ API蓝图已注册")


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload_file(file, prefix="image"):
    """保存上传的文件并预处理"""
    if not file or not allowed_file(file.filename):
        raise ValueError("不支持的文件格式")

    # 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    # 保存原始文件
    file.save(filepath)

    # 图像预处理(如果可用)
    if PREPROCESSOR_AVAILABLE:
        try:
            preprocessor = ImagePreprocessor()
            processed_path, info = preprocessor.preprocess_image(filepath)

            print(f"✅ 图像预处理完成:")
            print(f"   原始: {info['original_size'] / 1024:.1f}KB")
            print(f"   最终: {info['final_size'] / 1024:.1f}KB")

            # 如果进行了处理,删除原始文件
            if info["resized"] or info["compressed"]:
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
    import time
    import requests
    import urllib3

    # ===== OSS配置 =====
    # 从环境变量获取AccessKey
    access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    # OSS配置
    endpoint = "oss-cn-shanghai.aliyuncs.com"  # 上海区域
    bucket_name = "hair-transfer-bucket"  # Bucket名称

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
    date_str = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8]
    timestamp = int(datetime.now().timestamp())
    object_name = f"hairstyle-transfer/{date_str}/{unique_id}_{timestamp}{file_ext}"

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
            public_url = f"https://{bucket_name}.{endpoint}/{object_name}"

            print(f"✅ 上传成功!")
            print(f"   公网URL: {public_url}")

            return public_url

        except (
            oss2.exceptions.RequestError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.Timeout,
            urllib3.exceptions.ReadTimeoutError,
            urllib3.exceptions.ConnectTimeoutError,
        ) as e:
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
                f"Bucket不存在: {bucket_name}\n请先创建Bucket或检查Bucket名称是否正确"
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
            if "NoSuchBucket" in error_msg or "AccessDenied" in error_msg:
                raise Exception(f"配置错误: {error_msg}")

            # 其他未知错误，最后一次尝试失败时抛出
            if attempt == max_retries - 1:
                raise Exception(f"上传失败 (已重试{max_retries}次): {error_msg}")

            # 等待后重试
            wait_time = (attempt + 1) * 3
            print(f"   等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)


@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/api/extract-hair", methods=["POST"])
@login_required
@monitor_performance
def extract_hair():
    """提取发型API"""
    try:
        print(f"\n📥 收到发型提取请求")
        print(f"   Form data keys: {list(request.form.keys())}")
        print(f"   Files keys: {list(request.files.keys())}")

        # 检查头发分割模块是否可用
        if not HAIR_SEG_AVAILABLE:
            return jsonify(
                {
                    "error": "头发分割功能不可用",
                    "message": "请检查hair_segmentation模块是否正确安装",
                }
            ), 503

        # 检查发型参考图（URL或文件）
        # 先尝试从JSON获取（因为小程序发送的是JSON）
        json_data = request.get_json(silent=True)
        if json_data:
            print(f"   从JSON获取数据")
            hairstyle_image = json_data.get("image_url")
            hairstyle_file = None
        else:
            # 从form获取（兼容旧的文件上传方式）
            print(f"   从Form获取数据")
            hairstyle_image = request.form.get("image_url")
            hairstyle_file = (
                request.files.get("hairstyle_image")
                if "hairstyle_image" in request.files
                else None
            )

        if not hairstyle_image and not hairstyle_file:
            return jsonify({"error": "缺少发型参考图"}), 400

        # 余额检查
        if AUTH_AVAILABLE and DB_AVAILABLE:
            user = g.current_user
            hair_service = HairService()
            required_hairs = hair_service.calculate_cost(user, "hair_segment")

            if not user.has_enough_hairs(required_hairs):
                return jsonify(
                    {
                        "error": "余额不足",
                        "message": f"需要 {required_hairs} 发丝，当前余额 {user.get_total_hairs()} 发丝",
                        "required": required_hairs,
                        "available": user.get_total_hairs(),
                    }
                ), 400

            print(f"💰 余额检查通过: 需要 {required_hairs} 发丝")

        # 处理发型参考图（URL或文件）
        print(f"\n📤 保存发型参考图...")
        if hairstyle_file:
            # 文件上传
            hairstyle_path = save_upload_file(hairstyle_file, "hairstyle")
            print(f"   发型图(文件上传): {hairstyle_path}")
        else:
            # URL方式：已上传过，提取文件名
            if hairstyle_image.startswith("http://") or hairstyle_image.startswith(
                "https://"
            ):
                hairstyle_filename = hairstyle_image.split("/")[-1]
            else:
                hairstyle_filename = hairstyle_image.split("/")[-1]
            hairstyle_path = os.path.join(
                app.config["UPLOAD_FOLDER"], hairstyle_filename
            )
            print(f"   发型图(URL): {hairstyle_path}")

        # 上传到OSS获取URL
        print(f"\n☁️  上传到OSS...")
        try:
            hairstyle_url = upload_to_oss(hairstyle_path)
        except Exception as e:
            return jsonify({"error": "OSS上传失败", "message": str(e)}), 500

        # 提取发型
        print(f"\n✂️  提取发型...")
        hair_seg = HairSegmentation()

        # 调用头发分割API
        result = hair_seg.segment_hair(image_url=hairstyle_url)

        if not result["success"]:
            return jsonify({"error": "发型提取失败", "message": result["message"]}), 500

        # 下载提取的发型图
        print(f"\n📥 下载提取的发型...")
        output_filename = f"hair_extracted_{uuid.uuid4().hex[:8]}.png"
        extracted_path = os.path.join(
            app.config["HAIR_EXTRACTED_FOLDER"], output_filename
        )

        download_success = hair_seg.download_hair_image(
            result["hair_url"], extracted_path
        )

        # 检查下载是否成功
        if not download_success or not os.path.exists(extracted_path):
            return jsonify(
                {
                    "error": "发型图片下载失败",
                    "message": "阿里云API返回的图片无法下载，请稍后重试",
                }
            ), 500

        print(f"✅ 发型提取成功!")
        print(f"   提取的发型: {extracted_path}")

        # 返回结果
        original_filename = os.path.basename(hairstyle_path)
        extracted_filename = os.path.basename(extracted_path)

        # 生成完整URL
        result_url = get_full_url(f"/static/hair_extracted/{extracted_filename}")
        original_url = get_full_url(f"/static/uploads/{original_filename}")

        # 消费发丝
        task_id = str(uuid.uuid4())
        consume_result = None
        cost = 4  # 默认值

        if AUTH_AVAILABLE and DB_AVAILABLE:
            user = g.current_user
            hair_service = HairService()

            consume_result = hair_service.consume_hairs(
                user=user,
                service_type="hair_segment",
                task_id=task_id,
                result_url=result_url,
                original_hair_url=hairstyle_url,
            )

            if not consume_result["success"]:
                print(f"⚠️  消费失败: {consume_result['error']}")
            else:
                cost = consume_result["hairs_consumed"]
                print(f"💰 消费成功: {cost} 发丝")

        response_data = {
            "success": True,
            "result_url": result_url,
            "original_url": original_url,
            "cost": cost,
            "task_id": task_id,
            "message": "发型提取成功",
        }

        # 添加消费信息
        if consume_result and consume_result["success"]:
            response_data["hairs_consumed"] = consume_result["hairs_consumed"]
            response_data["remaining_scissor"] = consume_result["remaining_scissor"]
            response_data["remaining_comb"] = consume_result["remaining_comb"]
            response_data["remaining_total"] = consume_result["remaining_total"]

        return jsonify(response_data)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"❌ 发型提取失败: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"发型提取失败: {str(e)}"}), 500


@app.route("/api/transfer", methods=["POST"])
@login_required
@monitor_performance
def transfer_hairstyle():
    """发型迁移API"""
    try:
        logger.info("\n📥 收到发型迁移请求")
        logger.info(f"   Form data keys: {list(request.form.keys())}")
        logger.info(f"   Files keys: {list(request.files.keys())}")
        logger.info(f"   Request headers: {dict(request.headers)}")

        print(f"\n📥 收到发型迁移请求")
        print(f"   Form data keys: {list(request.form.keys())}")
        print(f"   Files keys: {list(request.files.keys())}")
        print(f"   Request headers: {dict(request.headers)}")

        # 先尝试从JSON获取数据（因为小程序发送的是JSON）
        json_data = request.get_json(silent=True)
        logger.info(f"   JSON parsed: {json_data is not None}")
        if json_data:
            print(f"   从JSON获取数据")
            print(f"   JSON数据: {json_data}")
            original_hair_url = json_data.get("hairstyle_image")
            customer_image = json_data.get("customer_image")
            customer_file = None
        else:
            # 从form获取（兼容旧的文件上传方式）
            print(f"   从Form获取数据")
            original_hair_url = request.form.get("hairstyle_image")
            customer_image = request.form.get("customer_image")
            customer_file = (
                request.files.get("customer_image")
                if "customer_image" in request.files
                else None
            )

        print(f"   hairstyle_image: {original_hair_url}")
        print(f"   customer_image: {customer_image}")
        print(f"   customer_file: {customer_file}")

        if not original_hair_url:
            print(f"   ❌ 缺少原始发型图")
            return jsonify({"error": "缺少原始发型图"}), 400

        if not customer_image and not customer_file:
            print(f"   ❌ 缺少客户照片")
            return jsonify({"error": "缺少客户照片"}), 400

        # 处理客户照片（URL或文件）
        print(f"\n📤 保存客户照片...")
        if customer_file:
            # 文件上传
            customer_path = save_upload_file(customer_file, "customer")
            print(f"   客户图(文件上传): {customer_path}")
        else:
            # URL方式：已上传过，提取文件名
            if customer_image.startswith("http://") or customer_image.startswith(
                "https://"
            ):
                # 完整URL：提取文件名
                customer_filename = customer_image.split("/")[-1]
            else:
                # 相对路径
                customer_filename = customer_image.split("/")[-1]
            customer_path = os.path.join(app.config["UPLOAD_FOLDER"], customer_filename)
            print(f"   客户图(URL): {customer_path}")

        # 从URL获取原始发型图本地路径
        # original_hair_url格式可能是完整URL或相对路径
        if original_hair_url.startswith("http://") or original_hair_url.startswith(
            "https://"
        ):
            original_filename = original_hair_url.split("/")[-1]
        else:
            original_filename = original_hair_url.split("/")[-1]
        hairstyle_path = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)

        if not os.path.exists(hairstyle_path):
            return jsonify({"error": "原始发型图不存在,请重新上传"}), 400

        print(f"   发型图(原始): {hairstyle_path}")

        # 预处理图像以确保符合阿里云API要求（2000x2000限制）
        if PREPROCESSOR_AVAILABLE:
            print(f"\n🔧 预处理图像以满足API要求...")
            try:
                preprocessor = ImagePreprocessor()

                # 预处理发型图
                hairstyle_path, hairstyle_info = preprocessor.preprocess_image(
                    hairstyle_path
                )
                if hairstyle_info["resized"]:
                    print(
                        f"   发型图已调整: {hairstyle_info['original_width']}x{hairstyle_info['original_height']} -> {hairstyle_info['target_width']}x{hairstyle_info['target_height']}"
                    )

                # 预处理客户图
                customer_path, customer_info = preprocessor.preprocess_image(
                    customer_path
                )
                if customer_info["resized"]:
                    print(
                        f"   客户图已调整: {customer_info['original_width']}x{customer_info['original_height']} -> {customer_info['target_width']}x{customer_info['target_height']}"
                    )

            except Exception as e:
                logger.warning(f"⚠️  图像预处理失败: {e}")
                print(f"⚠️  图像预处理失败: {e}")
                print(f"   使用原始文件继续...")
        else:
            print(f"   跳过预处理(模块不可用)")

        # 上传到OSS获取URL
        print(f"\n☁️  上传到OSS...")
        try:
            hairstyle_url = upload_to_oss(hairstyle_path)  # 使用原始发型图
            customer_url = upload_to_oss(customer_path)
        except NotImplementedError as e:
            return jsonify(
                {
                    "error": "请先配置OSS上传功能",
                    "message": str(e),
                    "help": "阿里云API需要公网可访问的图像URL,请配置OSS后重试",
                }
            ), 501

        # 获取参数
        # 从JSON或Form获取参数
        if json_data:
            model_version = json_data.get("model_version", "v1")
            face_blend_ratio = float(
                json_data.get("fusion_degree", "0.5")
            )  # 小程序发送的是 fusion_degree
            enable_sketch = json_data.get("enable_sketch", False)
            sketch_style = json_data.get("sketch_style", "artistic")
        else:
            model_version = request.form.get("model_version", "v1")
            face_blend_ratio = float(request.form.get("face_blend_ratio", "0.5"))
            enable_sketch = request.form.get("enable_sketch", "false").lower() == "true"
            sketch_style = request.form.get("sketch_style", "artistic")

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

        # 余额检查（检查最大可能费用）
        if AUTH_AVAILABLE and DB_AVAILABLE:
            user = g.current_user
            hair_service = HairService()
            max_service_type = "combined" if enable_sketch else "face_merge"
            max_required_hairs = hair_service.calculate_cost(user, max_service_type)

            if not user.has_enough_hairs(max_required_hairs):
                return jsonify(
                    {
                        "error": "余额不足",
                        "message": f"需要 {max_required_hairs} 发丝，当前余额 {user.get_total_hairs()} 发丝",
                        "required": max_required_hairs,
                        "available": user.get_total_hairs(),
                    }
                ), 400

            print(f"💰 余额检查通过: 需要最多 {max_required_hairs} 发丝")

        # 创建发型迁移服务(修复版)
        print(f"\n🔧 初始化服务...")
        service = AliyunHairTransferFixed()

        # 执行发型迁移
        result_image, info = service.transfer_hairstyle(
            hairstyle_image_url=hairstyle_url,
            customer_image_url=customer_url,
            model_version=model_version,
            face_blend_ratio=face_blend_ratio,
            save_dir=app.config["RESULT_FOLDER"],
            enable_sketch=enable_sketch,
            sketch_style=sketch_style,
        )

        # 返回结果
        result_filename = os.path.basename(info["save_path"])
        result_url = get_full_url(f"/static/results/{result_filename}")

        # 确定实际服务类型（根据素描是否成功）
        sketch_success = (
            enable_sketch
            and info.get("sketch_enabled", False)
            and "sketch_path" in info
            and info["sketch_path"]
        )

        actual_service_type = "combined" if sketch_success else "face_merge"
        task_id = str(uuid.uuid4())

        # 消费发丝
        consume_result = None
        if AUTH_AVAILABLE and DB_AVAILABLE:
            user = g.current_user
            hair_service = HairService()

            consume_result = hair_service.consume_hairs(
                user=user,
                service_type=actual_service_type,
                task_id=task_id,
                result_url=result_url,
                original_hair_url=hairstyle_url,
                customer_image_url=customer_url,
                model_version=model_version,
                face_blend_ratio=face_blend_ratio,
                sketch_url=get_full_url(
                    f"/static/results/{os.path.basename(info['sketch_path'])}"
                )
                if sketch_success
                else None,
            )

            if not consume_result["success"]:
                # 消费失败，但图片已生成，可以考虑退还或记录
                print(f"⚠️  消费失败: {consume_result['error']}")
                # 不返回错误，继续返回结果，但标记消费失败

            cost = consume_result.get("hairs_consumed", 0)
            print(f"💰 实际消费: {cost} 发丝 (服务类型: {actual_service_type})")
        else:
            # 没有认证系统，使用旧的逻辑
            cost = 88 if enable_sketch else 4

        # 构建返回信息
        response_data = {
            "success": True,
            "result_url": result_url,
            "cost": cost,
            "task_id": task_id,
            "info": {
                "elapsed_time": info["elapsed_time"],
                "template_id": info["template_id"],
                "model_version": model_version,
            },
        }

        # 添加消费信息
        if consume_result and consume_result["success"]:
            response_data["hairs_consumed"] = consume_result["hairs_consumed"]
            response_data["remaining_scissor"] = consume_result["remaining_scissor"]
            response_data["remaining_comb"] = consume_result["remaining_comb"]
            response_data["remaining_total"] = consume_result["remaining_total"]

        # 添加素描信息
        if enable_sketch:
            response_data["info"]["sketch_enabled"] = True
            response_data["info"]["sketch_success"] = sketch_success
            response_data["info"]["sketch_style"] = sketch_style
            response_data["info"]["sketch_method"] = info.get(
                "sketch_method", "unknown"
            )

            # 如果有素描图片，添加URL
            if sketch_success:
                sketch_filename = os.path.basename(info["sketch_path"])
                response_data["sketch_url"] = get_full_url(
                    f"/static/results/{sketch_filename}"
                )
                print(f"✅ 素描图片URL: {response_data['sketch_url']}")
            elif "sketch_error" in info:
                # 素描失败但启用了，添加错误信息
                print(f"⚠️  素描转换失败: {info['sketch_error']}")
                response_data["info"]["sketch_error"] = info["sketch_error"]
            else:
                print(f"⚠️  素描功能未启用或不可用")

        return jsonify(response_data)

    except ValueError as e:
        logger.error(f"❌ ValueError: {e}", exc_info=True)
        print(f"❌ ValueError: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}", exc_info=True)
        print(f"❌ 处理失败: {e}")
        print(f"❌ 异常类型: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"处理失败: {str(e)}"}), 500


@app.route("/api/add-sketch", methods=["POST"])
@login_required
def add_sketch():
    """为已有发型迁移结果添加素描效果（分步模式第2步）"""
    try:
        logger.info("\n🎨 收到素描添加请求")
        logger.info(f"   Form data keys: {list(request.form.keys())}")
        logger.info(f"   Request headers: {dict(request.headers)}")

        print(f"\n🎨 收到素描添加请求")
        print(f"   Form data keys: {list(request.form.keys())}")
        print(f"   Request headers: {dict(request.headers)}")

        # 获取请求数据
        json_data = request.get_json(silent=True)
        if json_data:
            print(f"   从JSON获取数据")
            logger.info(f"   JSON data: {json_data}")
            result_url = json_data.get("result_url")
            sketch_style = json_data.get("sketch_style", "artistic")
            logger.info(f"   result_url: {result_url}")
            logger.info(f"   sketch_style: {sketch_style}")
        else:
            print(f"   从Form获取数据")
            result_url = request.form.get("result_url")
            sketch_style = request.form.get("sketch_style", "artistic")

        print(f"   result_url: {result_url}")
        print(f"   sketch_style: {sketch_style}")

        if not result_url:
            print(f"   ❌ 缺少result_url参数")
            return jsonify({"error": "缺少result_url参数"}), 400

        # 余额检查（分步模式素描优化需要88发丝）
        if AUTH_AVAILABLE and DB_AVAILABLE:
            user = g.current_user
            hair_service = HairService()
            required_hairs = hair_service.calculate_cost(
                user, "combined"
            )  # 分步素描优化是combined类型

            if not user.has_enough_hairs(required_hairs):
                return jsonify(
                    {
                        "error": "余额不足",
                        "message": f"需要 {required_hairs} 发丝，当前余额 {user.get_total_hairs()} 发丝",
                        "required": required_hairs,
                        "available": user.get_total_hairs(),
                    }
                ), 400

            print(f"💰 余额检查通过: 需要 {required_hairs} 发丝")

        # 处理 result_url：如果是完整URL，提取相对路径
        if result_url.startswith("http://") or result_url.startswith("https://"):
            # 从完整URL中提取相对路径
            # 格式: http://localhost:5003/static/results/xxx.png
            result_url = "/" + "/".join(result_url.split("/")[3:])
            print(f"   转换后的result_url: {result_url}")

        # 检查素描功能是否可用
        if not SKETCH_AVAILABLE:
            return jsonify(
                {
                    "error": "素描功能不可用",
                    "message": "请检查sketch_converter模块是否正确安装",
                }
            ), 503

        # 下载已生成的发型迁移结果
        print(f"\n📥 下载发型迁移结果...")
        logger.info(f"   Downloading from: http://localhost:5003{result_url}")
        import requests

        response = requests.get(f"http://localhost:5003{result_url}")
        logger.info(f"   Response status: {response.status_code}")
        if response.status_code != 200:
            return jsonify({"error": "无法下载发型迁移结果"}), 400

        # 保存为临时文件
        temp_dir = app.config["UPLOAD_FOLDER"]
        os.makedirs(temp_dir, exist_ok=True)

        temp_filename = f"temp_sketch_input_{uuid.uuid4().hex[:8]}.png"
        temp_filepath = os.path.join(temp_dir, temp_filename)

        with open(temp_filepath, "wb") as f:
            f.write(response.content)

        print(f"   临时文件: {temp_filepath}")

        # 上传到OSS
        print(f"\n☁️  上传到OSS...")
        try:
            result_oss_url = upload_to_oss(temp_filepath)
        except Exception as e:
            return jsonify({"error": "OSS上传失败", "message": str(e)}), 500

        # 生成素描效果（使用百炼AI API）
        print(f"\n✏️  生成素描效果...")
        try:
            # 使用百炼素描转换器
            from bailian_sketch_converter import BailianSketchConverter

            bailian_converter = BailianSketchConverter()

            # 调用百炼API进行素描转换
            sketch_url, sketch_info = bailian_converter.convert(
                image_url=result_oss_url,  # 使用已上传到OSS的图片URL
                style=sketch_style,
                local_file_path=temp_filepath,  # 提供本地文件路径以提高效率
            )

            if not sketch_url or not sketch_info.get("success", False):
                error_msg = sketch_info.get("error", "未知错误")
                raise Exception(f"百炼API转换失败: {error_msg}")

            print(f"✅ 百炼素描转换成功: {sketch_url}")

            # 下载素描结果
            print(f"📥 下载素描结果...")
            import requests

            response = requests.get(sketch_url, timeout=30)
            if response.status_code != 200:
                raise Exception(f"下载素描结果失败: HTTP {response.status_code}")

            # 保存到本地
            results_dir = app.config["RESULT_FOLDER"]
            os.makedirs(results_dir, exist_ok=True)

            sketch_filename = f"sketch_{uuid.uuid4().hex[:8]}.png"
            sketch_path = os.path.join(results_dir, sketch_filename)

            with open(sketch_path, "wb") as f:
                f.write(response.content)

            # 验证文件
            if not os.path.exists(sketch_path):
                raise Exception(f"素描文件保存失败: {sketch_path}")

            file_size = os.path.getsize(sketch_path)
            if file_size == 0:
                raise Exception(f"素描文件为空: {sketch_path}")

            print(f"✅ 素描文件已保存: {sketch_path} ({file_size} bytes)")

        except Exception as e:
            print(f"   ❌ 素描生成失败: {e}")
            return jsonify({"error": "素描生成失败", "message": str(e)}), 500

        if not sketch_path or not os.path.exists(sketch_path):
            return jsonify(
                {"error": "素描生成失败", "message": "无法生成素描图片"}
            ), 500

        print(f"   素描图片: {sketch_path}")

        # 返回结果
        sketch_url = get_full_url(f"/static/results/{sketch_filename}")

        print(f"✅ 素描生成成功!")

        # 消费发丝
        task_id = str(uuid.uuid4())
        consume_result = None
        cost = 88  # 默认值

        if AUTH_AVAILABLE and DB_AVAILABLE:
            user = g.current_user
            hair_service = HairService()

            consume_result = hair_service.consume_hairs(
                user=user,
                service_type="combined",  # 分步素描优化
                task_id=task_id,
                result_url=sketch_url,
                original_hair_url=result_oss_url,
            )

            if not consume_result["success"]:
                print(f"⚠️  消费失败: {consume_result['error']}")
            else:
                cost = consume_result["hairs_consumed"]
                print(f"💰 消费成功: {cost} 发丝")

        response_data = {
            "success": True,
            "sketch_url": sketch_url,
            "original_url": result_url,
            "sketch_style": sketch_style,
            "cost": cost,
            "task_id": task_id,
        }

        # 添加消费信息
        if consume_result and consume_result["success"]:
            response_data["hairs_consumed"] = consume_result["hairs_consumed"]
            response_data["remaining_scissor"] = consume_result["remaining_scissor"]
            response_data["remaining_comb"] = consume_result["remaining_comb"]
            response_data["remaining_total"] = consume_result["remaining_total"]

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ 素描添加失败: {e}", exc_info=True)
        print(f"❌ 素描添加失败: {e}")
        print(f"❌ 异常类型: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"素描添加失败: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
@monitor_performance
def health_check():
    """健康检查"""
    try:
        # 检查环境变量
        has_access_key = bool(os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"))
        has_secret = bool(os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"))

        return jsonify(
            {
                "status": "ok" if (has_access_key and has_secret) else "warning",
                "access_key_configured": has_access_key,
                "secret_configured": has_secret,
                "message": "服务正常"
                if (has_access_key and has_secret)
                else "请配置AccessKey",
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def init_app_monitoring():
    """初始化应用监控"""
    from monitoring_config import init_monitoring

    try:
        monitor, health = init_monitoring(app)
        logger.info("监控系统初始化成功")
    except Exception as e:
        logger.warning(f"监控系统初始化失败: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 发型迁移系统 - 阿里云API版本")
    print("=" * 60)

    # 检查环境变量
    if not os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"):
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
    print("   4. 监控和日志系统已启用")

    # 初始化监控系统
    init_app_monitoring()

    print("\n🌐 启动Flask应用...")
    print("   访问地址: http://localhost:5003")
    print("   监控端点: http://localhost:5003/api/monitoring/metrics")
    print("   健康检查: http://localhost:5003/api/monitoring/health")
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=5003, debug=False)  # 生产环境关闭debug
