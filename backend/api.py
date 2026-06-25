#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由模块
商业化相关API接口
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import json
import re
import time
import config
from auth import AuthService, login_required, vip_required, optional_login, is_developer
from sms_service import SMSService
from payment_service import PaymentService
from hair_service import HairService
from member_service import MemberService
from account_service import AccountService
from financial_service import FinancialService
from models import db, User, ConsumptionRecord, HistoryRecord, Device, Message, FinancialRecord, RechargeRecord
from sqlalchemy import func as sql_func

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')


# ============================================
# 限流工具
# ============================================

_rate_limit_store = {}

def check_rate_limit(key, max_requests=5, window_seconds=60):
    """
    简单的内存限流检查
    
    Args:
        key: 限流键（如 IP 或手机号）
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）
    
    Returns:
        tuple: (allowed: bool, remaining: int, retry_after: int)
    """
    now = time.time()
    store_key = f"rate_limit:{key}"
    
    if store_key not in _rate_limit_store:
        _rate_limit_store[store_key] = []
    
    timestamps = _rate_limit_store[store_key]
    # 清理过期记录
    timestamps[:] = [t for t in timestamps if now - t < window_seconds]
    
    if len(timestamps) >= max_requests:
        oldest = min(timestamps)
        retry_after = int(window_seconds - (now - oldest)) + 1
        return False, 0, retry_after
    
    timestamps.append(now)
    remaining = max_requests - len(timestamps)
    return True, remaining, 0


def get_client_ip():
    """获取客户端真实IP"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'


# ============================================
# 认证相关接口
# ============================================

@api_bp.route('/auth/wechat/login', methods=['POST'])
def wechat_login():
    """微信登录"""
    try:
        data = request.get_json()
        code = data.get('code')

        if not code:
            return jsonify({'error': '缺少code参数'}), 400

        # 获取设备信息（可选）
        device_info = data.get('device_info')
        
        # 获取微信昵称和头像（可选）
        nickname = data.get('nickname')
        avatar_url = data.get('avatar_url')

        auth_service = AuthService()
        result = auth_service.wechat_login(code, device_info=device_info, nickname=nickname, avatar_url=avatar_url)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/phone/send-code', methods=['POST'])
def send_sms_code():
    """发送短信验证码"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return jsonify({'error': '缺少phone参数'}), 400
        
        # 限流：同一手机号每分钟最多5次
        allowed, _, retry_after = check_rate_limit(f"sms_phone:{phone}", max_requests=5, window_seconds=60)
        if not allowed:
            return jsonify({'error': f'发送过于频繁，请{retry_after}秒后重试'}), 429
        
        # 限流：同一IP每分钟最多10次
        client_ip = get_client_ip()
        allowed, _, retry_after = check_rate_limit(f"sms_ip:{client_ip}", max_requests=10, window_seconds=60)
        if not allowed:
            return jsonify({'error': f'请求过于频繁，请{retry_after}秒后重试'}), 429
        
        sms_service = SMSService()
        result = sms_service.send_code(phone)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/phone/login', methods=['POST'])
def phone_login():
    """手机号登录"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        code = data.get('code')
        device_info = data.get('device_info')
        
        if not phone or not code:
            return jsonify({'error': '缺少phone或code参数'}), 400
        
        auth_service = AuthService()
        result = auth_service.phone_login(phone, code, device_info=device_info)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/bind-phone', methods=['POST'])
@login_required
def bind_phone():
    """绑定手机号（支持账号合并）"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        code = data.get('code')
        
        if not phone or not code:
            return jsonify({'error': '缺少phone或code参数'}), 400
        
        user = g.current_user
        auth_service = AuthService()
        result = auth_service.bind_phone_with_merge(user.id, phone, code)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/merge-account', methods=['POST'])
@login_required
def merge_account():
    """合并账号（当手机号已被其他用户绑定时）"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        code = data.get('code')
        
        if not phone or not code:
            return jsonify({'error': '缺少phone或code参数'}), 400
        
        user = g.current_user
        auth_service = AuthService()
        result = auth_service.bind_phone_with_merge(user.id, phone, code)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/get-session-key', methods=['POST'])
@login_required
def get_session_key():
    """用 wx.login 的 code 换取 session_key（用于虚拟支付签名）"""
    try:
        import requests as http_requests
        from config import get_config
        
        data = request.get_json()
        code = data.get('code')
        
        if not code:
            return jsonify({'success': False, 'error': '缺少 code 参数'}), 400
        
        cfg = get_config()
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": cfg.WECHAT_APP_ID,
            "secret": cfg.WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
        
        response = http_requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if "errcode" in result:
            return jsonify({'success': False, 'error': result['errmsg']}), 400
        
        session_key = result.get("session_key")
        if not session_key:
            return jsonify({'success': False, 'error': '获取 session_key 失败'}), 500
        
        return jsonify({
            'success': True,
            'session_key': session_key
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 用户相关接口
# ============================================

@api_bp.route('/user/info', methods=['GET'])
@optional_login
def get_user_info():
    """获取用户信息（支持游客）"""
    try:
        user = g.current_user

        # 游客或未登录用户
        if not user:
            return jsonify({
                'success': True,
                'user': None,
                'balance': {'scissor_hairs': 0, 'comb_hairs': 0, 'total': 0},
                'is_guest': True
            })

        hair_service = HairService()
        member_service = MemberService()

        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'balance': hair_service.get_user_balance(user),
            'member': member_service.get_member_info(user)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/account/check-guest-bonus', methods=['POST'])
@login_required
def check_guest_bonus():
    """游客检查是否符合 4 小时续赠条件"""
    try:
        user = g.current_user
        account_service = AccountService()
        result = account_service.check_and_grant_guest_bonus(user)

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/guest/bonus-status', methods=['GET'])
@login_required
def guest_bonus_status():
    """获取游客额度使用状态"""
    try:
        user = g.current_user
        account_service = AccountService()

        return jsonify({
            'success': True,
            'user_type': user.user_type,
            'bonus_used_count': user.guest_bonus_used_count,
            'max_bonus_per_year': account_service.guest_max_bonus_per_year,
            'remaining_bonus': account_service.guest_max_bonus_per_year - user.guest_bonus_used_count,
            'last_bonus_time': user.last_guest_bonus_time.isoformat() if user.last_guest_bonus_time else None
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/user/update', methods=['PUT'])
@login_required
def update_user_info():
    """更新用户信息"""
    try:
        data = request.get_json()
        user = g.current_user
        
        # 更新允许的字段
        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/user/test-recharge', methods=['POST'])
@login_required
def test_recharge():
    """
    测试充值接口（仅开发环境）
    用于开发测试时快速给用户充值发丝
    """
    try:
        # 检查是否为开发环境
        from config import get_config
        config = get_config()
        if not config.DEBUG:
            return jsonify({'error': '此接口仅在开发环境可用'}), 403

        data = request.get_json()
        user = g.current_user

        # 获取充值数量（默认88根）
        comb_hairs = data.get('comb_hairs', 88)
        scissor_hairs = data.get('scissor_hairs', 0)

        # 充值到用户账户
        user.comb_hairs += comb_hairs
        user.scissor_hairs += scissor_hairs

        db.session.commit()

        print(f"✅ 测试充值成功: user_id={user.id}, comb_hairs=+{comb_hairs}, scissor_hairs=+{scissor_hairs}")

        return jsonify({
            'success': True,
            'message': f'测试充值成功！获得{comb_hairs}根梳子发丝和{scissor_hairs}根剪刀发丝',
            'user': user.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================
# 设备管理相关接口
# ============================================

@api_bp.route('/device/list', methods=['GET'])
@optional_login
def list_devices():
    """获取用户绑定的设备列表（支持游客）"""
    try:
        user = g.current_user

        # 游客模式返回空设备列表
        if not user:
            return jsonify({
                'success': True,
                'devices': [],
                'device_count': 0,
                'max_devices': 2,
                'is_guest': True
            })

        devices = Device.query.filter_by(user_id=user.id).order_by(Device.bound_at.desc()).all()

        return jsonify({
            'success': True,
            'devices': [d.to_dict() for d in devices],
            'device_count': len(devices),
            'max_devices': 2
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/device/bind', methods=['POST'])
@login_required
def bind_device():
    """绑定设备（游客首次访问自动调用）"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        device_name = data.get('device_name', '未知设备')
        device_type = data.get('device_type', 'unknown')

        if not device_id:
            return jsonify({'error': '缺少device_id参数'}), 400

        user = g.current_user

        # 检查设备是否已被当前用户绑定
        existing_device = Device.query.filter_by(user_id=user.id, device_id=device_id).first()
        if existing_device:
            # 更新最后活跃时间
            existing_device.last_active_at = datetime.now()
            db.session.commit()
            return jsonify({
                'success': True,
                'message': '设备已绑定',
                'device': existing_device.to_dict()
            })

        # 检查是否已达到最大设备数
        device_count = Device.query.filter_by(user_id=user.id).count()
        if device_count >= 2:
            return jsonify({
                'success': False,
                'error': '已达到最大设备绑定数量（2个）',
                'code': 'MAX_DEVICES_REACHED'
            }), 400

        # 检查设备是否已被其他用户绑定
        other_user_device = Device.query.filter_by(device_id=device_id).first()
        if other_user_device and other_user_device.user_id != user.id:
            return jsonify({
                'success': False,
                'error': '该设备已被其他账户绑定',
                'code': 'DEVICE_ALREADY_BOUND'
            }), 400

        # 创建新设备记录
        new_device = Device(
            user_id=user.id,
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            is_primary=(device_count == 0)  # 第一个设备设为主设备
        )
        db.session.add(new_device)
        db.session.commit()

        # 如果用户还没有 device_id，设置它（永不改变的金线）
        if not user.device_id:
            user.device_id = device_id
            db.session.commit()

        return jsonify({
            'success': True,
            'message': '设备绑定成功',
            'device': new_device.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/device/unbind', methods=['POST'])
@login_required
def unbind_device():
    """解绑设备"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')

        if not device_id:
            return jsonify({'error': '缺少device_id参数'}), 400

        user = g.current_user

        # 查找设备
        device = Device.query.filter_by(user_id=user.id, device_id=device_id).first()
        if not device:
            return jsonify({'error': '设备不存在'}), 404

        # 检查是否至少保留一个设备
        device_count = Device.query.filter_by(user_id=user.id).count()
        if device_count <= 1:
            return jsonify({
                'success': False,
                'error': '至少需要保留一个设备',
                'code': 'MIN_DEVICES_REQUIRED'
            }), 400

        db.session.delete(device)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '设备解绑成功'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 充值相关接口
# ============================================

@api_bp.route('/recharge/rules', methods=['GET'])
def get_recharge_rules():
    """获取充值规则"""
    try:
        from config import RECHARGE_RULES, NORMAL_RECHARGE_RULES, VIP_RECHARGE_RULES

        # 返回两种规则
        rules = {
            'normal': [],
            'vip': []
        }

        for amount, rule in NORMAL_RECHARGE_RULES.items():
            rules['normal'].append({
                'amount': amount,
                'scissor_hairs': rule['scissor_hairs'],
                'comb_hairs': rule['comb_hairs'],
                'total_hairs': rule['scissor_hairs'] + rule['comb_hairs']
            })

        for amount, rule in VIP_RECHARGE_RULES.items():
            rules['vip'].append({
                'amount': amount,
                'scissor_hairs': rule['scissor_hairs'],
                'comb_hairs': rule['comb_hairs'],
                'total_hairs': rule['scissor_hairs'] + rule['comb_hairs']
            })

        return jsonify({'success': True, 'rules': rules})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recharge/create-order', methods=['POST'])
@login_required
def create_recharge_order():
    """创建充值订单"""
    try:
        data = request.get_json()
        amount = data.get('amount')
        payment_method = data.get('payment_method')
        
        if not amount or not payment_method:
            return jsonify({'error': '缺少amount或payment_method参数'}), 400
        
        user = g.current_user
        payment_service = PaymentService()
        result = payment_service.create_recharge_order(user.id, amount, payment_method, user=user)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recharge/pay', methods=['POST'])
@login_required
def pay_recharge():
    """支付充值 - 支持微信支付"""
    try:
        data = request.get_json()
        order_no = data.get('order_no')
        payment_method = data.get('payment_method')

        if not order_no or not payment_method:
            return jsonify({'error': '缺少order_no或payment_method参数'}), 400

        user = g.current_user

        # 根据支付方式调用对应的支付接口
        if payment_method == 'wechat':
            from payment_service import WeChatPayService
            from models import RechargeRecord

            # 查询订单信息
            order = RechargeRecord.query.filter_by(order_no=order_no).first()

            if not order:
                return jsonify({'error': '订单不存在'}), 404

            # 验证订单所属用户
            if order.user_id != user.id:
                return jsonify({'error': '无权操作此订单'}), 403

            # 验证订单状态
            if order.payment_status == 'success':
                return jsonify({'error': '订单已支付'}), 400

            if order.payment_status == 'cancelled':
                return jsonify({'error': '订单已取消'}), 400

            # 创建微信支付订单
            if not user.openid:
                return jsonify({
                    'error': '充值功能需要绑定微信账号，请先通过微信登录',
                    'code': 'NEED_WECHAT_BIND'
                }), 400

            wechat_service = WeChatPayService()
            result = wechat_service.create_jsapi_order(
                order_no=order_no,
                amount=float(order.amount),
                openid=user.openid,
                body='发型迁移充值'
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'prepay_id': result['prepay_id'],
                    'wxpay_params': result['wxpay_params']
                })
            else:
                return jsonify({'error': result['error']}), 400

        elif payment_method == 'alipay':
            # 支付宝H5支付
            from payment_service import AlipayService
            from models import RechargeRecord

            # 查询订单信息
            order = RechargeRecord.query.filter_by(order_no=order_no).first()

            if not order:
                return jsonify({'error': '订单不存在'}), 404

            # 验证订单所属用户
            if order.user_id != user.id:
                return jsonify({'error': '无权操作此订单'}), 403

            # 验证订单状态
            if order.payment_status == 'success':
                return jsonify({'error': '订单已支付'}), 400

            if order.payment_status == 'cancelled':
                return jsonify({'error': '订单已取消'}), 400

            # 创建支付宝H5支付订单
            alipay_service = AlipayService()
            result = alipay_service.create_wap_pay_order(
                order_no=order_no,
                amount=float(order.amount),
                subject='发型迁移充值'
            )

            if result['success']:
                # 返回支付URL
                pay_url = result['pay_url']

                # 构建H5支付页面的完整URL
                from config import get_config
                config = get_config()
                base_url = config.get_config_by_prefix('FLASK_').get('SERVER_NAME', 'localhost:5003')

                # 如果是本地开发，使用http；生产环境使用https
                if 'localhost' in base_url or '127.0.0.1' in base_url:
                    base_url = 'http://' + base_url
                else:
                    base_url = 'https://' + base_url

                h5_pay_url = f"{base_url}/pay/alipay/h5?order_no={order_no}&amount={order.amount}&pay_url={pay_url}"

                return jsonify({
                    'success': True,
                    'h5_pay_url': h5_pay_url,
                    'pay_url': pay_url
                })
            else:
                return jsonify({'error': result['error']}), 400

        else:
            # 不支持的支付方式
            return jsonify({'error': '不支持的支付方式，仅支持微信支付'}), 400

    except Exception as e:
        print(f"❌ 支付充值失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recharge/orders', methods=['GET'])
@login_required
def get_recharge_orders():
    """获取充值订单列表"""
    try:
        user = g.current_user
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        from models import RechargeRecord
        query = RechargeRecord.query.filter_by(user_id=user.id).order_by(
            RechargeRecord.created_at.desc()
        )
        
        total = query.count()
        orders = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return jsonify({
            'orders': [o.to_dict() for o in orders],
            'total': total,
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recharge/order/status', methods=['GET'])
@login_required
def get_recharge_order_status():
    """查询单个充值订单状态"""
    try:
        user = g.current_user
        order_no = request.args.get('order_no')

        if not order_no:
            return jsonify({'error': '缺少订单号'}), 400

        from models import RechargeRecord
        order = RechargeRecord.query.filter_by(
            user_id=user.id,
            order_no=order_no
        ).first()

        if not order:
            return jsonify({'error': '订单不存在'}), 404

        return jsonify({
            'success': True,
            'order_no': order.order_no,
            'amount': float(order.amount),
            'scissor_hairs': order.scissor_hairs,
            'comb_hairs': order.comb_hairs,
            'payment_method': order.payment_method,
            'payment_status': order.payment_status,
            'paid_at': order.paid_at.isoformat() if order.paid_at else None,
            'created_at': order.created_at.isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recharge/query-wechat/<order_no>', methods=['GET'])
@login_required
def query_wechat_pay_status(order_no):
    """主动查询微信支付状态（当回调未到达时使用）"""
    try:
        from models import RechargeRecord
        from payment_service import WeChatPayService, PaymentService

        user = g.current_user
        order = RechargeRecord.query.filter_by(
            user_id=user.id,
            order_no=order_no
        ).first()

        if not order:
            return jsonify({'error': '订单不存在'}), 404

        # 如果订单已经是 success，直接返回
        if order.payment_status == 'success':
            return jsonify({
                'success': True,
                'payment_status': 'success',
                'source': 'local'
            })

        # 调用微信支付 API 查询订单状态
        wechat_service = WeChatPayService()
        result = wechat_service.wechat_pay.query_order(order_no)

        if result.get('success'):
            trade_state = result.get('trade_state')

            if trade_state == 'SUCCESS':
                # 支付成功，处理订单
                payment_service = PaymentService()
                transaction_id = result.get('transaction_id', f"QUERY_{order_no}")
                process_result = payment_service.process_recharge_success(
                    order_no=order_no,
                    transaction_id=transaction_id
                )

                if process_result['success']:
                    return jsonify({
                        'success': True,
                        'payment_status': 'success',
                        'source': 'wechat_query'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': process_result.get('error', '处理失败')
                    })
            elif trade_state in ['CLOSED', 'REVOKED', 'PAYERROR']:
                # 支付失败或关闭
                order.payment_status = 'failed'
                db.session.commit()
                return jsonify({
                    'success': True,
                    'payment_status': 'failed',
                    'source': 'wechat_query'
                })
            else:
                # 仍在支付中
                return jsonify({
                    'success': True,
                    'payment_status': 'pending',
                    'source': 'wechat_query'
                })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '查询失败')
            })

    except Exception as e:
        print(f"❌ 查询微信支付状态异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recharge/callback/wechat', methods=['POST'])
def wechat_pay_callback():
    """微信支付回调 - 统一处理充值和会员订单"""
    try:
        from payment_service import WeChatPayService, PaymentService

        # 获取回调数据
        request_data = request.get_json()

        # 验证签名并解密数据
        wechat_service = WeChatPayService()
        verify_result = wechat_service.verify_callback(request_data)

        if not verify_result['success']:
            print(f"❌ 微信支付回调验证失败：{verify_result['error']}")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=False,
                message=verify_result['error']
            ))

        # 处理订单
        order_no = verify_result['data']['order_no']
        transaction_id = verify_result['data']['transaction_id']

        print(f"\n📨 收到微信支付回调")
        print(f"   订单号：{order_no}")
        print(f"   微信订单号：{transaction_id}")

        payment_service = PaymentService()

        # 根据订单号前缀判断订单类型
        if order_no.startswith('MB'):
            # 会员订单
            print(f"   订单类型：会员订单")
            process_result = payment_service.process_member_success(
                order_no=order_no,
                transaction_id=transaction_id
            )
            order_type = '会员订单'
        else:
            # 充值订单（默认）
            print(f"   订单类型：充值订单")
            process_result = payment_service.process_recharge_success(
                order_no=order_no,
                transaction_id=transaction_id
            )
            order_type = '充值订单'

        if process_result['success']:
            print(f"✅ {order_type}处理成功")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=True,
                message='OK'
            ))
        else:
            print(f"❌ 处理{order_type}失败：{process_result['error']}")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=False,
                message=process_result['error']
            ))

    except Exception as e:
        print(f"❌ 微信支付回调处理异常：{e}")
        import traceback
        traceback.print_exc()
        from payment_service import WeChatPayService
        wechat_service = WeChatPayService()
        return jsonify(wechat_service.wechat_pay.generate_response(
            success=False,
            message=str(e)
        ))


@api_bp.route('/recharge/callback/refund', methods=['POST'])
def wechat_refund_callback():
    """微信退款回调 - 自动扣回发丝"""
    import logging
    import json
    from logging_config import log_security_event

    refund_logger = logging.getLogger('refund')
    refund_logger.setLevel(logging.INFO)

    # 退款回调独立日志文件
    if not refund_logger.handlers:
        handler = logging.FileHandler('logs/refund_callback.log', encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        ))
        refund_logger.addHandler(handler)

    try:
        from payment_service import WeChatPayService, PaymentService

        request_data = request.get_json()
        ip = request.remote_addr

        refund_logger.info(f"[REFUND_CALLBACK] 收到回调请求, IP={ip}")

        wechat_service = WeChatPayService()
        verify_result = wechat_service.verify_refund_callback(request_data)

        if not verify_result['success']:
            error_msg = verify_result.get('error', '未知错误')
            refund_logger.warning(f"[REFUND_CALLBACK] 验证失败: {error_msg}, IP={ip}")
            log_security_event(
                event_type='refund_callback_verify_failed',
                details={'error': error_msg, 'ip': ip}
            )
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=False,
                message=error_msg
            ))

        order_no = verify_result['data']['order_no']
        refund_no = verify_result['data']['refund_no']
        refund_amount = verify_result['data']['amount']
        refund_id = verify_result['data'].get('refund_id', '')

        refund_logger.info(
            f"[REFUND_CALLBACK] 验证通过: order_no={order_no}, refund_no={refund_no}, "
            f"refund_id={refund_id}, amount={refund_amount}"
        )

        # 带重试的退款处理（最多3次）
        payment_service = PaymentService()
        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                process_result = payment_service.process_refund_success(
                    order_no=order_no,
                    refund_no=refund_no,
                    refund_amount=refund_amount
                )

                if process_result['success']:
                    user_id = process_result.get('user_id')
                    deduct_scissor = process_result.get('deducted_scissor', 0)
                    deduct_comb = process_result.get('deducted_comb', 0)

                    refund_logger.info(
                        f"[REFUND_CALLBACK] 处理成功: user_id={user_id}, "
                        f"扣回 scissor={deduct_scissor}, comb={deduct_comb}, "
                        f"attempt={attempt}"
                    )

                    return jsonify(wechat_service.wechat_pay.generate_response(
                        success=True,
                        message='OK'
                    ))
                else:
                    last_error = process_result.get('error', '未知错误')
                    # 如果是"已退款"则认为是正常重复回调
                    if '已退款' in last_error:
                        refund_logger.info(
                            f"[REFUND_CALLBACK] 订单已退款（重复回调，正常）: order_no={order_no}"
                        )
                        return jsonify(wechat_service.wechat_pay.generate_response(
                            success=True,
                            message='OK'
                        ))
                    refund_logger.warning(
                        f"[REFUND_CALLBACK] 处理失败 (attempt {attempt}/{max_retries}): {last_error}"
                    )
                    if attempt < max_retries:
                        import time
                        time.sleep(1)
                        continue
                    break

            except Exception as e:
                last_error = str(e)
                refund_logger.warning(
                    f"[REFUND_CALLBACK] 处理异常 (attempt {attempt}/{max_retries}): {last_error}"
                )
                if attempt < max_retries:
                    import time
                    time.sleep(1)

        # 所有重试均失败
        refund_logger.error(
            f"[REFUND_CALLBACK] 退款处理最终失败: order_no={order_no}, "
            f"refund_no={refund_no}, error={last_error}"
        )
        log_security_event(
            event_type='refund_callback_process_failed',
            details={
                'order_no': order_no,
                'refund_no': refund_no,
                'refund_id': refund_id,
                'amount': refund_amount,
                'error': last_error
            },
            level='ERROR'
        )
        return jsonify(wechat_service.wechat_pay.generate_response(
            success=False,
            message=last_error or '处理失败'
        ))

    except Exception as e:
        refund_logger.error(f"[REFUND_CALLBACK] 回调处理异常: {e}")
        import traceback
        traceback.print_exc()
        log_security_event(
            event_type='refund_callback_exception',
            details={'error': str(e)},
            level='CRITICAL'
        )
        from payment_service import WeChatPayService
        wechat_service = WeChatPayService()
        return jsonify(wechat_service.wechat_pay.generate_response(
            success=False,
            message=str(e)
        ))


@api_bp.route('/recharge/callback/alipay', methods=['POST'])
def alipay_pay_callback():
    """支付宝支付回调 - 充值"""
    try:
        from payment_service import AlipayService, PaymentService

        # 获取回调数据（支付宝使用form-data）
        request_data = request

        print(f"\n📨 收到支付宝支付回调 (充值)")

        # 验证签名
        alipay_service = AlipayService()
        verify_result = alipay_service.verify_callback(request_data)

        if not verify_result['success']:
            print(f"❌ 支付宝回调验证失败: {verify_result['error']}")
            return 'failure'

        # 处理订单
        order_no = verify_result['data']['order_no']
        transaction_id = verify_result['data']['trade_no']

        print(f"   订单号: {order_no}")
        print(f"   支付宝交易号: {transaction_id}")

        payment_service = PaymentService()
        process_result = payment_service.process_recharge_success(
            order_no=order_no,
            transaction_id=transaction_id
        )

        if process_result['success']:
            print(f"✅ 充值订单处理成功")
            return 'success'
        else:
            print(f"❌ 处理充值失败: {process_result['error']}")
            return 'failure'

    except Exception as e:
        print(f"❌ 支付宝回调处理异常: {e}")
        import traceback
        traceback.print_exc()
        return 'failure'


# ============================================
# 会员相关接口
# ============================================

@api_bp.route('/member/info', methods=['GET'])
@login_required
def get_member_info():
    """获取会员信息"""
    try:
        user = g.current_user
        member_service = MemberService()
        result = member_service.get_member_info(user)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/member/buy', methods=['POST'])
@login_required
def buy_member():
    """购买会员"""
    try:
        data = request.get_json()
        payment_method = data.get('payment_method')
        
        if not payment_method:
            return jsonify({'error': '缺少payment_method参数'}), 400
        
        user = g.current_user
        payment_service = PaymentService()
        result = payment_service.create_member_order(user.id, payment_method)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/member/pay', methods=['POST'])
@login_required
def pay_member():
    """支付会员订单 - 支持微信支付"""
    try:
        data = request.get_json()
        order_no = data.get('order_no')
        payment_method = data.get('payment_method')

        if not order_no or not payment_method:
            return jsonify({'error': '缺少 order_no 或 payment_method 参数'}), 400

        user = g.current_user

        if payment_method == 'wechat':
            from payment_service import WeChatPayService
            from models import MemberOrder

            order = MemberOrder.query.filter_by(order_no=order_no).first()
            if not order:
                return jsonify({'error': '订单不存在'}), 404
            if order.user_id != user.id:
                return jsonify({'error': '无权操作此订单'}), 403
            if order.payment_status == 'success':
                return jsonify({'error': '订单已支付'}), 400

            wechat_service = WeChatPayService()
            result = wechat_service.create_jsapi_order(
                order_no=order_no,
                amount=float(order.amount),
                openid=user.openid,
                body='发型迁移陪跑会员'
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'prepay_id': result['prepay_id'],
                    'wxpay_params': result['wxpay_params']
                })
            else:
                return jsonify({'error': result['error']}), 400

        elif payment_method == 'alipay':
            from payment_service import AlipayService
            from models import MemberOrder

            order = MemberOrder.query.filter_by(order_no=order_no).first()
            if not order:
                return jsonify({'error': '订单不存在'}), 404
            if order.user_id != user.id:
                return jsonify({'error': '无权操作此订单'}), 403
            if order.payment_status == 'success':
                return jsonify({'error': '订单已支付'}), 400

            alipay_service = AlipayService()
            result = alipay_service.create_wap_pay_order(
                order_no=order_no,
                amount=float(order.amount),
                subject='发型迁移陪跑会员'
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'h5_pay_url': result['pay_url']
                })
            else:
                return jsonify({'error': result['error']}), 400

        else:
            return jsonify({'error': '不支持的支付方式'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/member/orders', methods=['GET'])
@login_required
def get_member_orders():
    """获取会员订单列表"""
    try:
        user = g.current_user
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        member_service = MemberService()
        result = member_service.get_member_orders(user, page, page_size)
        
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/member/callback/wechat', methods=['POST'])
def member_pay_callback():
    """微信支付回调 - 会员购买"""
    try:
        from payment_service import WeChatPayService, PaymentService

        # 获取回调数据
        request_data = request.get_json()

        print(f"\n📨 收到微信支付回调 (会员购买)")

        # 验证签名并解密数据
        wechat_service = WeChatPayService()
        verify_result = wechat_service.verify_callback(request_data)

        if not verify_result['success']:
            print(f"❌ 会员支付回调验证失败: {verify_result['error']}")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=False,
                message=verify_result['error']
            ))

        # 处理会员订单
        order_no = verify_result['data']['order_no']
        transaction_id = verify_result['data']['transaction_id']

        print(f"   订单号: {order_no}")
        print(f"   微信订单号: {transaction_id}")

        payment_service = PaymentService()
        process_result = payment_service.process_member_success(
            order_no=order_no,
            transaction_id=transaction_id
        )

        if process_result['success']:
            print(f"✅ 会员订单处理成功")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=True,
                message='OK'
            ))
        else:
            print(f"❌ 处理会员购买失败: {process_result['error']}")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=False,
                message=process_result['error']
            ))

    except Exception as e:
        print(f"❌ 会员支付回调处理异常: {e}")
        import traceback
        traceback.print_exc()
        from payment_service import WeChatPayService
        wechat_service = WeChatPayService()
        return jsonify(wechat_service.wechat_pay.generate_response(
            success=False,
            message=str(e)
        ))


# ============================================
# 头发丝消费相关接口
# ============================================

@api_bp.route('/consume/check', methods=['GET'])
@login_required
def check_hair_balance():
    """检查头发丝余额"""
    try:
        user = g.current_user
        hair_service = HairService()
        result = hair_service.get_user_balance(user)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/consume/records', methods=['GET'])
@login_required
def get_consumption_records():
    """获取消费记录列表"""
    try:
        user = g.current_user
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        hair_service = HairService()
        result = hair_service.get_consumption_records(user, page, page_size)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# 历史记录相关接口（vip 会员专属）
# ============================================

@api_bp.route('/history/list', methods=['GET'])
@vip_required
def get_history_records():
    """获取历史记录列表"""
    try:
        user = g.current_user
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        query = HistoryRecord.query.filter_by(user_id=user.id).order_by(
            HistoryRecord.created_at.desc()
        )

        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            'records': [r.to_dict() for r in records],
            'total': total,
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        import logging
        logging.error(f'History list error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


@api_bp.route('/history/download', methods=['GET'])
@vip_required
def download_history_record():
    """下载历史记录图片"""
    try:
        record_id = request.args.get('record_id')

        if not record_id:
            return jsonify({'error': '缺少record_id参数'}), 400

        user = g.current_user
        record = HistoryRecord.query.filter_by(
            id=record_id,
            user_id=user.id
        ).first()

        if not record:
            return jsonify({'error': '记录不存在'}), 404

        image_type = request.args.get('type', 'result')  # result, sketch, original, customer

        # 根据类型获取对应的图片 URL
        image_url = None
        if image_type == 'result':
            image_url = record.result_url
        elif image_type == 'sketch':
            image_url = record.sketch_url
        elif image_type == 'original':
            image_url = record.original_hair_url
        elif image_type == 'customer':
            image_url = record.customer_image_url
        else:
            return jsonify({'error': '不支持的图片类型'}), 400

        if not image_url:
            return jsonify({'error': '该类型图片不存在'}), 404

        # 这里需要返回图片URL或直接返回图片

        return jsonify({
            'success': True,
            'download_url': image_url,
            'image_type': image_type,
            'record_id': record_id
        })

    except Exception as e:
        import logging
        logging.error(f'History download error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


@api_bp.route('/history/delete', methods=['DELETE'])
@vip_required
def delete_history_record():
    """删除历史记录（包括图片）"""
    try:
        record_id = request.args.get('record_id')
        
        if not record_id:
            return jsonify({'error': '缺少record_id参数'}), 400
        
        user = g.current_user
        record = HistoryRecord.query.filter_by(
            id=record_id,
            user_id=user.id
        ).first()
        
        if not record:
            return jsonify({'error': '记录不存在'}), 404
        
        # 删除图片文件
        from member_service import MemberService
        member_service = MemberService()
        
        if record.result_url:
            member_service._delete_image_file(record.result_url)
        
        if record.sketch_url:
            member_service._delete_image_file(record.sketch_url)
        
        # 删除数据库记录
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f'History delete error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


# ============================================
# 账户服务相关接口
# ============================================

@api_bp.route('/account/register-bonus', methods=['POST'])
@login_required
def register_bonus():
    """注册时自动赠送头发丝"""
    try:
        from account_service import AccountService
        account_service = AccountService()
        user = g.current_user
        
        result = account_service.register_user(user)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/account/check-bonus', methods=['POST'])
@login_required
def check_bonus():
    """检查并添加余额不足时的自动赠送头发丝"""
    try:
        from account_service import AccountService
        from datetime import datetime, timedelta
        account_service = AccountService()
        user = g.current_user

        result = account_service.check_and_add_bonus_for_insufficient(user)

        if result['success']:
            # 添加提醒时间信息
            # 查找最近一次余额不足提醒
            from models import InsufficientReminder
            last_reminder = InsufficientReminder.query.filter_by(
                user_id=user.id
            ).order_by(InsufficientReminder.reminded_at.desc()).first()

            if last_reminder:
                # 计算可领取免费额度的时间
                available_at = last_reminder.reminded_at + timedelta(hours=4)
                result['reminder_time'] = last_reminder.reminded_at.isoformat()
                result['available_at'] = available_at.isoformat()

            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/account/deactivate', methods=['POST'])
@login_required
def deactivate_account():
    """注销账户"""
    try:
        from account_service import AccountService
        account_service = AccountService()
        user = g.current_user
        
        # 提醒用户一次
        return jsonify({
            'success': True,
            'message': '请确认注销账户，数字货币里面的财产将视作自动放弃并作废。'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/account/confirm-deactivate', methods=['POST'])
@login_required
def confirm_deactivate():
    """确认注销账户"""
    try:
        from account_service import AccountService
        account_service = AccountService()
        user = g.current_user
        
        result = account_service.deactivate_account(user)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/upload', methods=['POST'])
@optional_login
def upload_file():
    """上传图片"""
    try:
        print(f"\n📤 收到上传请求")
        print(f"   Files in request: {list(request.files.keys())}")
        print(f"   Request headers: {dict(request.headers)}")

        # 检查是否有文件
        if 'file' not in request.files:
            print(f"   ❌ 没有找到'file'字段")
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']
        print(f"   ✅ 文件名: {file.filename}")
        print(f"   ✅ 文件大小: {len(file.read())} bytes")
        file.seek(0)  # 重置文件指针

        # 检查文件名
        if file.filename == '':
            print(f"   ❌ 文件名为空")
            return jsonify({'error': '文件名为空'}), 400

        # 保存文件
        from werkzeug.utils import secure_filename
        import os
        import uuid

        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}
        UPLOAD_FOLDER = 'static/uploads'

        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400

        # 生成唯一文件名
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"upload_{uuid.uuid4().hex[:8]}.{ext}"

        # 使用绝对路径，基于 api.py 所在位置
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # 确保目录存在
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # 保存文件
        file.save(filepath)

        # 上传到阿里云 OSS，获取公网可访问的 URL
        try:
            from app import upload_to_oss
            oss_url = upload_to_oss(filepath)
            print(f"   ✅ OSS上传成功: {oss_url}")

            # 上传成功后删除本地临时文件
            import os
            os.remove(filepath)

            url = oss_url
        except Exception as oss_err:
            # OSS 上传失败时，降级为本地URL（仅用于开发调试）
            print(f"   ⚠️ OSS上传失败，使用本地URL: {oss_err}")
            protocol = request.scheme
            host = request.host
            url = f'{protocol}://{host}/static/uploads/{filename}'

        print(f"   ✅ 返回URL: {url}")

        return jsonify({
            'success': True,
            'url': url
        })

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500



# ============================================
# 开发者工具接口（仅本地开发启用）
# ============================================

@api_bp.route('/dev/toggle-vip', methods=['POST'])
@login_required
def toggle_vip():
    """
    切换会员等级（开发者/管理员专属）
    用于开发测试时快速切换会员状态

    注意：此接口仅在本机开发环境启用，生产环境访问返回 404
    """
    try:
        from auth import is_developer

        # 如果开发者功能未启用，直接返回 404（不暴露接口存在）
        if not is_developer():
            return jsonify({'error': 'Not Found'}), 404

        user = g.current_user

        # 二次检查是否为开发者账号
        if not is_developer(user.id):
            return jsonify({'error': '此功能仅限开发者账号使用'}), 403

        # 切换会员等级
        if user.member_level == 'vip':
            user.member_level = 'normal'
            user.member_expire_at = None
            message = '已切换为普通用户'
        else:
            user.member_level = 'vip'
            # 设置永久的会员到期时间
            from datetime import datetime
            user.member_expire_at = datetime(2099, 12, 31, 23, 59, 59)
            message = '已切换为 VIP 会员'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'user': user.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/dev/reset-test-user', methods=['POST'])
@login_required
def reset_test_user():
    """
    删除当前用户，清除所有数据（测试专用）
    用于开发者模拟新客户从零开始的体验
    下次登录时会创建全新的游客账户并授予首次福利

    注意：此接口仅限开发者账号使用，删除操作不可恢复
    """
    try:
        from auth import is_developer

        user = g.current_user

        # 检查是否为开发者账号
        if not is_developer(user.id):
            return jsonify({'error': '此功能仅限开发者账号使用'}), 403

        user_id = user.id
        openid = user.openid

        # 删除用户的所有关联数据
        from models import ConsumptionRecord, HistoryRecord, RechargeRecord, MemberOrder
        from models import InsufficientReminder, GuestBonusRecord, UserBonusRecord, Device, MemberReminder

        # 删除关联记录
        ConsumptionRecord.query.filter_by(user_id=user_id).delete()
        HistoryRecord.query.filter_by(user_id=user_id).delete()
        RechargeRecord.query.filter_by(user_id=user_id).delete()
        MemberOrder.query.filter_by(user_id=user_id).delete()
        InsufficientReminder.query.filter_by(user_id=user_id).delete()
        GuestBonusRecord.query.filter_by(user_id=user_id).delete()
        UserBonusRecord.query.filter_by(user_id=user_id).delete()
        Device.query.filter_by(user_id=user_id).delete()
        MemberReminder.query.filter_by(user_id=user_id).delete()

        # 删除用户本身
        db.session.delete(user)
        db.session.commit()

        print(f"✅ 测试用户已删除：user_id={user_id}, openid={openid}")

        return jsonify({
            'success': True,
            'message': '数据已清除，下次登录将创建全新游客账户'
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ 重置测试用户失败：{e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# 用户协议与隐私政策接口
# ============================================

@api_bp.route('/legal/user-agreement', methods=['GET'])
def get_user_agreement():
    """获取用户协议内容"""
    try:
        agreement = {
            'title': '用户协议',
            'version': '1.0.0',
            'update_date': '2026-04-01',
            'content': """
<h2>一、协议确认</h2>
<p>欢迎您使用发型迁移服务！在使用本产品前，请仔细阅读本用户协议（以下简称"本协议"）。当您注册、登录或使用本服务时，即表示您已阅读、理解并同意接受本协议的全部内容。</p>

<h2>二、服务内容</h2>
<p>1. 发型迁移服务利用人工智能技术，为用户提供发型虚拟试戴、素描转换等服务。</p>
<p>2. 本服务通过阿里巴巴云服务 API 实现发型分割、人脸融合等功能。</p>
<p>3. 用户需要充值购买"发丝"（虚拟货币）来使用各项服务。</p>

<h2>三、用户注册与账号</h2>
<p>1. 用户可以通过微信小程序授权登录或手机号验证码登录。</p>
<p>2. 用户应保证提供的信息真实、准确、完整。</p>
<p>3. 用户应妥善保管账号信息，不得将账号转让、出售或出租给他人。</p>
<p>4. 如发现账号被盗用，应立即通知平台。</p>

<h2>四、虚拟财产</h2>
<p>1. "发丝"是本服务内的虚拟货币，用于购买各项服务。</p>
<p>2. 发丝可通过充值购买或平台活动获得。</p>
<p>3. 发丝不可兑换为法定货币，不可转让。</p>
<p>4. 用户注销账号时，剩余发丝将自动作废。</p>

<h2>五、会员服务</h2>
<p>1. VIP 会员享受服务价格 50% 折扣优惠。</p>
<p>2. 会员有效期为 365 天，到期后自动降级为普通用户。</p>
<p>3. 会员到期前 30 天、15 天、7 天、3 天、1 天，平台将发送提醒通知。</p>
<p>4. 会员购买即赠送 1000 发丝。</p>

<h2>六、用户行为规范</h2>
<p>1. 用户不得上传违法、色情、暴力、侵权的图片内容。</p>
<p>2. 用户不得利用本服务从事任何违法犯罪活动。</p>
<p>3. 用户不得对本服务进行反向工程、反编译或试图提取源代码。</p>
<p>4. 用户不得利用平台漏洞获取不当利益。</p>

<h2>七、知识产权</h2>
<p>1. 本服务的软件、界面设计、代码等知识产权归平台所有。</p>
<p>2. 用户上传的图片著作权归用户或原权利人所有。</p>
<p>3. 平台生成的结果图片，用户拥有使用权。</p>

<h2>八、隐私保护</h2>
<p>1. 平台重视用户隐私保护，详细规则请见《隐私政策》。</p>
<p>2. 用户上传的图片仅用于服务处理，不做其他用途。</p>
<p>3. VIP 会员的历史记录保留 45 天，到期后自动删除。</p>

<h2>九、服务变更与中断</h2>
<p>1. 平台有权根据业务需要调整服务内容，调整前将提前公告。</p>
<p>2. 因系统维护、网络故障等原因导致服务中断，平台将尽快修复。</p>
<p>3. 因不可抗力导致的服务中断，平台不承担责任。</p>

<h2>十、免责声明</h2>
<p>1. 因用户操作不当导致的服务失败，平台不承担责任。</p>
<p>2. 因第三方服务（如阿里云 API）故障导致的服务问题，平台协助解决但不承担直接责任。</p>
<p>3. 用户使用服务生成的图片引发的版权纠纷，由用户自行承担。</p>

<h2>十一、协议变更</h2>
<p>平台有权根据法律法规变更或业务调整修改本协议，修改后将重新提示用户同意。</p>

<h2>十二、争议解决</h2>
<p>本协议适用中华人民共和国法律。因本协议引起的争议，双方应友好协商解决；协商不成的，可向平台所在地人民法院提起诉讼。</p>

<h2>十三、联系方式</h2>
<p>如您对本协议有任何疑问，请通过平台内客服渠道联系我们。</p>
"""
        }
        return jsonify(agreement)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/legal/privacy-policy', methods=['GET'])
def get_privacy_policy():
    """获取隐私政策内容"""
    try:
        policy = {
            'title': '隐私政策',
            'version': '1.0.0',
            'update_date': '2026-04-01',
            'content': """
<h2>一、引言</h2>
<p>发型迁移（以下简称"我们"）非常重视用户的隐私保护。本隐私政策（以下简称"本政策"）旨在向您说明我们在您使用服务过程中如何收集、使用、存储、共享和保护您的个人信息，以及您享有的权利。</p>
<p>请您在使用我们的产品前，仔细阅读并了解本隐私政策。</p>

<h2>二、信息收集</h2>
<p>我们可能收集以下类型的信息：</p>
<p><strong>1. 账号信息</strong></p>
<ul>
    <li>微信 openid、unionid（用于用户身份识别）</li>
    <li>手机号码（用于验证码登录）</li>
    <li>昵称、头像（用户自愿提供）</li>
</ul>
<p><strong>2. 使用服务产生的信息</strong></p>
<ul>
    <li>上传的原始发型图片、客户照片</li>
    <li>服务生成的结果图片、素描图片</li>
    <li>消费记录、充值记录</li>
    <li>历史记录（VIP 会员专属，保留 45 天）</li>
</ul>
<p><strong>3. 设备与日志信息</strong></p>
<ul>
    <li>设备型号、操作系统版本</li>
    <li>网络状态、IP 地址</li>
    <li>服务使用记录、操作日志</li>
</ul>

<h2>三、信息使用</h2>
<p>我们可能将收集的信息用于以下用途：</p>
<p>1. 提供发型迁移服务，处理用户上传图片。</p>
<p>2. 记录消费、充值历史，管理虚拟财产。</p>
<p>3. 会员到期提醒、余额不足提醒等服务通知。</p>
<p>4. 改进服务质量，优化用户体验。</p>
<p>5. 防范欺诈和滥用，保障服务安全。</p>

<h2>四、信息共享与披露</h2>
<p><strong>1. 第三方服务共享</strong></p>
<p>为实现特定功能，我们可能与以下第三方共享必要的信息：</p>
<ul>
    <li><strong>阿里巴巴云服务</strong>：上传的图片将传输至阿里云 API 进行发型分割、人脸融合处理。</li>
    <li><strong>微信支付</strong>：支付订单信息将与微信支付共享以完成支付。</li>
    <li><strong>短信服务商</strong>：手机号码将提供给短信服务商以发送验证码。</li>
</ul>
<p><strong>2. 法定披露</strong></p>
<p>在以下情况下，我们可能依法披露您的个人信息：</p>
<ul>
    <li>根据法律法规要求或政府部门要求。</li>
    <li>为执行本协议或保护我们及他人的合法权益。</li>
    <li>为防止欺诈或其他非法活动。</li>
</ul>

<h2>五、信息存储</h2>
<p><strong>1. 存储地点</strong></p>
<p>我们在中华人民共和国境内收集和产生的个人信息，将存储在境内阿里云服务器。</p>
<p><strong>2. 存储期限</strong></p>
<ul>
    <li>账号信息：存储至用户注销账号。</li>
    <li>消费/充值记录：根据相关法律法规要求保存。</li>
    <li>VIP 会员历史记录：保留 45 天后自动删除。</li>
    <li>日志信息：保留 6 个月后删除。</li>
</ul>
<p><strong>3. 安全措施</strong></p>
<p>我们采取加密传输、访问控制等技术措施保护您的信息安全。</p>

<h2>六、您的权利</h2>
<p><strong>1. 访问权</strong></p>
<p>您可以随时查看您的账号信息、消费记录、历史记录。</p>
<p><strong>2. 更正权</strong></p>
<p>您可以修改您的昵称、头像等个人信息。</p>
<p><strong>3. 删除权</strong></p>
<p>在以下情况下，您可以要求我们删除您的个人信息：</p>
<ul>
    <li>我们违反法律法规收集、使用信息。</li>
    <li>我们违反约定收集、使用信息。</li>
    <li>您注销账号。</li>
</ul>
<p><strong>4. 注销权</strong></p>
<p>您可以申请注销账号。注销后，我们将删除或匿名化处理您的个人信息，但法律法规另有规定的除外。</p>
<p><strong>5. 撤回同意</strong></p>
<p>您可以撤回对收集、使用个人信息的授权。撤回后，我们可能无法继续为您提供对应服务。</p>

<h2>七、未成年人保护</h2>
<p>1. 我们非常重视对未成年人个人信息的保护。</p>
<p>2. 若您是 14 周岁以下的未成年人，应在监护人监护、指导下使用本服务。</p>
<p>3. 若您是未成年人的监护人，请监督被监护人的使用行为。</p>

<h2>八、政策更新</h2>
<p>1. 我们可能适时修订本政策内容。</p>
<p>2. 对于重大变更，我们将在变更生效前通过页面提示、弹窗等方式另行告知。</p>
<p>3. 若您继续使用服务，即表示同意更新后的政策。</p>

<h2>九、联系我们</h2>
<p>如您对本隐私政策有任何疑问、意见或建议，或希望行使您的权利，请通过平台内客服渠道联系我们。</p>
"""
        }
        return jsonify(policy)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# 客户留言相关接口
# ============================================

@api_bp.route('/messages', methods=['POST'])
def submit_message():
    """提交客户留言（无需登录，游客可提交）"""
    try:
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        content = data.get('content')

        # 验证必填参数
        if not name:
            return jsonify({'error': '姓名不能为空'}), 400
        if not phone:
            return jsonify({'error': '联系电话不能为空'}), 400
        if not content:
            return jsonify({'error': '留言内容不能为空'}), 400

        # 验证姓名长度
        if len(name) > 20:
            return jsonify({'error': '姓名最多20个字符'}), 400

        # 验证电话格式（11位数字）
        if not phone.isdigit() or len(phone) != 11:
            return jsonify({'error': '请输入正确的11位手机号码'}), 400

        # 验证内容长度
        if len(content) > 500:
            return jsonify({'error': '留言内容最多500个字符'}), 400

        # 限流：同一IP每小时最多提交3次留言
        client_ip = get_client_ip()
        allowed, _, retry_after = check_rate_limit(f"msg_ip:{client_ip}", max_requests=3, window_seconds=3600)
        if not allowed:
            return jsonify({'error': f'提交过于频繁，请稍后再试'}), 429

        # 尝试关联用户（通过手机号查找已注册用户）
        matched_user = User.query.filter_by(phone=phone.strip()).first()
        user_id = matched_user.id if matched_user else None

        # 创建留言记录
        message = Message(
            user_id=user_id,
            name=name.strip(),
            phone=phone.strip(),
            content=content.strip()
        )
        db.session.add(message)
        db.session.commit()

        # 如果关联到用户，同时创建一条聊天消息并发送企业微信通知
        if matched_user:
            try:
                from chat_service import ChatService
                success, msg_text, chat_msg = ChatService.send_message(
                    user_id=matched_user.id,
                    content=f"[留言] {content.strip()}"
                )
                if success:
                    print(f"✅ 留言已同步到聊天系统: user_id={matched_user.id}")
            except Exception as e:
                print(f"⚠️ 留言同步到聊天系统失败: {e}")
        else:
            # 未关联到用户，直接发送企业微信通知（无聊天系统关联）
            try:
                from chat_notifier import ChatNotifier
                from chat_service import generate_reply_token
                # 使用手机号生成临时 token，管理员点击后可查看留言详情
                notifier = ChatNotifier()
                reply_token = generate_reply_token(phone)
                reply_url = f"{notifier.base_url}/api/chat/reply?token={reply_token}"
                preview = content[:100] + ("..." if len(content) > 100 else "")
                notifier.send_template_card(
                    title="新客户留言",
                    desc=f"{name.strip()} 发来了一条留言",
                    description=f"姓名: {name.strip()}\n电话: {phone.strip()}\n留言: {preview}",
                    reply_url=reply_url
                )
                print(f"✅ 未关联用户的留言已通知企业微信: phone={phone}")
            except Exception as e:
                print(f"⚠️ 留言企业微信通知失败: {e}")

        return jsonify({
            'success': True,
            'message': '留言提交成功，感谢您的反馈！'
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f'Message submit error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


@api_bp.route('/messages', methods=['GET'])
def get_messages():
    """获取留言列表（管理后台用，需要开发者权限）"""
    try:
        from auth import is_developer
        
        # 检查开发者权限
        if not is_developer():
            return jsonify({'error': '无权访问此接口'}), 403
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        # 限制 page_size 范围
        page_size = min(page_size, 100)
        
        # 查询留言，按创建时间倒序
        query = Message.query.order_by(Message.created_at.desc())
        total = query.count()
        messages = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return jsonify({
            'success': True,
            'messages': [m.to_dict() for m in messages],
            'total': total,
            'page': page,
            'page_size': page_size
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/refund/enable', methods=['POST'])
def admin_enable_refund():
    """管理员批准用户退款权限（开发者专用）"""
    try:
        from auth import is_developer

        # 检查开发者权限
        if not is_developer():
            return jsonify({'error': '无权访问此接口'}), 403

        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': '缺少user_id参数'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 开通退款权限
        user.refund_enabled = True
        db.session.commit()

        print(f"✅ 已为用户开通退款权限: user_id={user_id}, phone={user.phone}")

        return jsonify({
            'success': True,
            'message': f'已为用户 {user.nickname or user.phone} 开通退款权限'
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f'Admin enable refund error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


@api_bp.route('/admin/refund/users', methods=['GET'])
def admin_refund_users():
    """查询用户列表（退款权限管理，开发者专用）"""
    try:
        from auth import is_developer

        if not is_developer():
            return jsonify({'error': '无权访问此接口'}), 403

        phone = request.args.get('phone', '').strip()
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        query = User.query
        if phone:
            query = query.filter(User.phone.like(f'%{phone}%'))

        query = query.order_by(User.id.desc())
        pagination = query.offset((page - 1) * page_size).limit(page_size + 1).all()

        has_more = len(pagination) > page_size
        users = pagination[:page_size]

        return jsonify({
            'success': True,
            'users': [{
                'id': u.id,
                'nickname': u.nickname or '',
                'phone': u.phone or '',
                'scissor_hairs': u.scissor_hairs or 0,
                'comb_hairs': u.comb_hairs or 0,
                'member_level': u.member_level or 'normal',
                'refund_enabled': u.refund_enabled or False,
                'created_at': u.created_at.isoformat() if u.created_at else ''
            } for u in users],
            'has_more': has_more,
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        import logging
        logging.error(f'Admin refund users error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


@api_bp.route('/admin/refund/toggle', methods=['POST'])
def admin_refund_toggle():
    """切换用户退款权限（开发者专用）"""
    try:
        from auth import is_developer

        if not is_developer():
            return jsonify({'error': '无权访问此接口'}), 403

        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': '缺少user_id参数'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404

        user.refund_enabled = not user.refund_enabled
        db.session.commit()

        status = '开通' if user.refund_enabled else '关闭'
        print(f"{'✅' if user.refund_enabled else '🔒'} 已{status}用户退款权限: user_id={user_id}, phone={user.phone}")

        return jsonify({
            'success': True,
            'refund_enabled': user.refund_enabled,
            'message': f'已{status}用户 {user.nickname or user.phone} 的退款权限'
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f'Admin refund toggle error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


@api_bp.route('/admin/refund/applications', methods=['GET'])
def admin_refund_applications():
    """查看所有退款申请（开发者专用）"""
    try:
        from auth import is_developer
        from models import RefundApplication

        if not is_developer():
            return jsonify({'error': '无权访问此接口'}), 403

        status = request.args.get('status', 'all').strip()
        phone = request.args.get('phone', '').strip()
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        query = RefundApplication.query

        # 按状态筛选
        if status != 'all' and status in ('pending', 'approved', 'rejected'):
            query = query.filter_by(status=status)

        # 按手机号搜索
        if phone:
            query = query.join(User).filter(User.phone.like(f'%{phone}%'))

        query = query.order_by(RefundApplication.created_at.desc())
        pagination = query.offset((page - 1) * page_size).limit(page_size + 1).all()

        has_more = len(pagination) > page_size
        applications = pagination[:page_size]

        return jsonify({
            'success': True,
            'applications': [{
                'id': a.id,
                'user_id': a.user_id,
                'user_phone': a.user.phone if a.user else '',
                'user_nickname': a.user.nickname if a.user else '',
                'applicant_name': a.applicant_name,
                'applicant_phone': a.applicant_phone,
                'refund_type': a.refund_type,
                'refund_amount': float(a.refund_amount) if a.refund_amount else 0,
                'reason': a.reason,
                'status': a.status,
                'approved_at': a.approved_at.isoformat() if a.approved_at else None,
                'rejection_reason': a.rejection_reason,
                'created_at': a.created_at.isoformat() if a.created_at else ''
            } for a in applications],
            'total': query.count(),
            'has_more': has_more,
            'page': page,
            'page_size': page_size
        })

    except Exception as e:
        import logging
        logging.error(f'Admin refund applications error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


# ==================== 微信虚拟支付 API（iOS端）====================

@api_bp.route("/virtual-pay/create-order", methods=["POST"])
@login_required
def create_virtual_pay_order():
    """创建虚拟支付订单（iOS端），用于购买头发丝充值或VIP会员"""
    try:
        import uuid
        from datetime import timedelta
        from virtual_payment_service import WeChatVirtualPayService
        from models import RechargeRecord, MemberOrder
        from config import DEVELOPER_MODE_ENABLED, DEVELOPER_ACCOUNTS

        user = g.current_user
        data = request.get_json()

        if not data:
            return jsonify({"error": "请求参数不能为空"}), 400

        order_type = data.get("order_type")  # 'recharge' 或 'member'
        amount = data.get("amount")  # 金额（元）
        goods_key = data.get("goods_key")  # 商品键，如 recharge_10, member_vip
        session_key = data.get("session_key")  # 用户 session_key（从 wx.login 获取）

        if not order_type or not amount or not goods_key or not session_key:
            return jsonify({"error": "参数不完整，需要 session_key"}), 400

        # 检查虚拟支付是否已启用
        virtual_pay_service = WeChatVirtualPayService()
        if not virtual_pay_service.is_virtual_pay_enabled():
            return jsonify({
                "error": "虚拟支付功能暂未开通",
                "code": "VIRTUAL_PAY_NOT_ENABLED"
            }), 503

        # 获取虚拟商品 ID
        goods_id = virtual_pay_service.get_goods_id(goods_key)
        if not goods_id:
            return jsonify({"error": "商品配置错误"}), 400

        # 生成订单号
        order_no = f"VP{int(time.time())}{str(uuid.uuid4().hex[:8])}"

        # 开发者模式：直接标记为成功
        is_developer = DEVELOPER_MODE_ENABLED and user.id in DEVELOPER_ACCOUNTS
        payment_status = "success" if is_developer else "pending"

        # 根据订单类型创建记录
        if order_type == "recharge":
            # 根据用户类型和充值金额获取正确的发丝数量
            from config import RECHARGE_RULES
            user_level = user.member_level if hasattr(user, 'member_level') and user.member_level else "normal"
            recharge_rules = RECHARGE_RULES.get(user_level, RECHARGE_RULES["normal"])
            amount_int = int(amount)
            rule = recharge_rules.get(amount_int, {"scissor_hairs": int(amount * 10), "comb_hairs": 0})
            
            scissor_hairs = rule.get("scissor_hairs", int(amount * 10))
            comb_hairs = rule.get("comb_hairs", 0)
            
            order = RechargeRecord(
                user_id=user.id,
                order_no=order_no,
                amount=amount,
                scissor_hairs=scissor_hairs,
                comb_hairs=comb_hairs,
                payment_method="wechat_virtual",
                payment_status=payment_status,
            )
            db.session.add(order)
            
            # 开发者模式：立即充值（加到正确的卡槽）
            if is_developer:
                user.scissor_hairs += scissor_hairs
                user.comb_hairs += comb_hairs
        elif order_type == "member":
            order = MemberOrder(
                user_id=user.id,
                order_no=order_no,
                member_level="vip",
                amount=amount,
                bonus_hairs=1000,
                payment_method="wechat_virtual",
                payment_status=payment_status,
            )
            db.session.add(order)
            
            # 开发者模式：立即开通会员
            if is_developer:
                user.member_level = "vip"
                # 如果已经是未过期的会员，累计365天；否则从当前时间算365天
                if user.member_expire_at and user.member_expire_at > datetime.now():
                    user.member_expire_at = user.member_expire_at + timedelta(days=365)
                else:
                    user.member_expire_at = datetime.now() + timedelta(days=365)
                user.comb_hairs += 1000
        else:
            return jsonify({"error": "不支持的订单类型"}), 400

        db.session.commit()

        # 生成虚拟支付参数（开发者模式下也需要返回，前端逻辑保持一致）
        body = "发型迁移充值" if order_type == "recharge" else "发型迁移陪跑会员"
        pay_params = virtual_pay_service.create_virtual_pay_order(
            user_openid=user.openid,
            order_no=order_no,
            amount_yuan=amount,
            goods_id=goods_id,
            body=body,
            session_key=session_key,
        )

        return jsonify({
            "success": True,
            "order_no": order_no,
            "virtual_pay_params": pay_params,
            "is_developer_mode": is_developer,  # 前端可根据此字段决定是否轮询
        })

    except Exception as e:
        import logging
        logging.error(f"创建虚拟支付订单失败: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/virtual-pay/callback", methods=["POST"])
def virtual_pay_callback():
    """虚拟支付回调接口，微信服务器在用户完成支付后调用"""
    try:
        from virtual_payment_service import WeChatVirtualPayService
        from payment_service import PaymentService

        virtual_pay_service = WeChatVirtualPayService()
        payment_service = PaymentService()

        callback_data = request.get_json()

        # 验证回调签名
        verified_data = virtual_pay_service.verify_callback(callback_data)
        if not verified_data:
            return jsonify({"return_code": "FAIL", "return_msg": "签名验证失败"}), 400

        order_no = verified_data.get("out_trade_no")
        if not order_no:
            return jsonify({"return_code": "FAIL", "return_msg": "订单号缺失"}), 400

        # 检查支付状态
        pay_status = verified_data.get("result_code")  # SUCCESS 或 FAIL

        if pay_status == "SUCCESS":
            # 查找订单并处理成功
            transaction_id = verified_data.get("transaction_id", f"VIRTUAL_{order_no}")
            order = RechargeRecord.query.filter_by(order_no=order_no).first()
            if order:
                payment_service.process_recharge_success(order_no, transaction_id)
            else:
                order = MemberOrder.query.filter_by(order_no=order_no).first()
                if order:
                    payment_service.process_member_success(order_no, transaction_id)

            return jsonify({"return_code": "SUCCESS", "return_msg": "OK"})
        else:
            # 支付失败，更新状态
            order = RechargeRecord.query.filter_by(order_no=order_no).first() or \
                    MemberOrder.query.filter_by(order_no=order_no).first()
            if order:
                order.payment_status = "failed"
                db.session.commit()

            return jsonify({"return_code": "FAIL", "return_msg": "支付失败"})

    except Exception as e:
        import logging
        logging.error(f"虚拟支付回调处理失败: {e}")
        return jsonify({"return_code": "FAIL", "return_msg": str(e)}), 500


@api_bp.route("/virtual-pay/order-status/<order_no>", methods=["GET"])
@login_required
def get_virtual_pay_order_status(order_no):
    """查询虚拟支付订单状态，前端轮询使用"""
    try:
        from models import RechargeRecord, MemberOrder

        user = g.current_user

        # 查找订单
        order = RechargeRecord.query.filter_by(order_no=order_no, user_id=user.id).first()
        if not order:
            order = MemberOrder.query.filter_by(order_no=order_no, user_id=user.id).first()

        if not order:
            return jsonify({"error": "订单不存在"}), 404

        return jsonify({
            "success": True,
            "order_no": order.order_no,
            "payment_status": order.payment_status,
            "amount": float(order.amount),
            "created_at": order.created_at.isoformat() if order.created_at else None,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================
# 推广返佣相关接口
# ============================================

@api_bp.route('/referral/qrcode', methods=['POST'])
@login_required
def referral_qrcode():
    """生成或获取用户的推广小程序码"""
    try:
        from referral_service import ReferralService
        referral_service = ReferralService()
        user = g.current_user

        result = referral_service.get_or_create_qrcode(user.id)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', '生成失败')}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/referral/qrcode-image', methods=['GET'])
@login_required
def referral_qrcode_image():
    """代理二维码图片，通过服务器域名提供，解决 wx.getImageInfo 域名白名单问题"""
    try:
        from referral_service import ReferralService
        referral_service = ReferralService()
        user = g.current_user

        result = referral_service.get_or_create_qrcode(user.id)
        if not result.get('success'):
            return jsonify({'error': result.get('error', '生成失败')}), 500

        qrcode_url = result.get('qrcode_url')
        if not qrcode_url:
            return jsonify({'error': '二维码URL不存在'}), 404

        import requests as req
        resp = req.get(qrcode_url, timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': '图片获取失败'}), 500

        return resp.content, 200, {'Content-Type': 'image/png'}

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/proxy/resource', methods=['GET'])
@login_required
def proxy_resource():
    """
    通用资源代理接口
    通过服务器域名代理外部资源（如 OSS 图片），解决微信小程序域名白名单问题

    用法: GET /api/proxy/resource?url=<encoded_url>
    示例: /api/proxy/resource?url=https%3A%2F%2Foss.example.com%2Fimage.png
    """
    try:
        from urllib.parse import unquote
        target_url = request.args.get('url', '')

        if not target_url:
            return jsonify({'error': '缺少 url 参数'}), 400

        target_url = unquote(target_url)

        # 安全检查：只允许代理白名单中的域名
        allowed_domains = [
            'oss-cn-shanghai.aliyuncs.com',
            'hair-transfer-bucket.oss-cn-shanghai.aliyuncs.com',
        ]

        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        if parsed.hostname not in allowed_domains:
            return jsonify({'error': '域名不在白名单中'}), 403

        import requests as req
        resp = req.get(target_url, timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': '资源获取失败'}), 500

        content_type = resp.headers.get('Content-Type', 'application/octet-stream')
        return resp.content, 200, {'Content-Type': content_type}

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/referral/track', methods=['POST'])
def referral_track():
    """追踪扫码来源（新用户通过扫码进入时调用）"""
    try:
        from referral_service import ReferralService
        referral_service = ReferralService()
        data = request.get_json()
        scene = data.get('scene', '').strip()

        if not scene:
            return jsonify({'error': 'scene参数不能为空'}), 400

        # 尝试获取当前用户（如果已登录）
        from models import AuthService
        auth_service = AuthService()
        user = auth_service.get_current_user()

        if not user:
            return jsonify({'error': '请先登录', 'code': 401}), 401

        result = referral_service.track_referral(user.id, scene)
        if result.get('success'):
            return jsonify(result)
        else:
            # 推广关系不存在或无效时不报错，静默处理
            return jsonify({'success': False, 'message': result.get('error', '追踪失败')})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/referral/piggy-bank', methods=['GET'])
@login_required
def piggy_bank_stats():
    """获取存钱罐统计数据"""
    try:
        from referral_service import ReferralService
        referral_service = ReferralService()
        user = g.current_user

        result = referral_service.get_piggy_bank_stats(user.id)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/referral/consume-cash', methods=['POST'])
@login_required
def consume_cash():
    """本地消费：用现金余额购买发丝"""
    try:
        from referral_service import ReferralService
        referral_service = ReferralService()
        user = g.current_user
        data = request.get_json()
        amount = data.get('amount')

        if not amount or amount <= 0:
            return jsonify({'error': '请输入有效金额'}), 400

        result = referral_service.consume_cash_for_hairs(user.id, amount)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', '消费失败')}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/referral/withdraw', methods=['POST'])
@login_required
def withdraw_cash():
    """提现到微信零钱"""
    try:
        from referral_service import ReferralService
        referral_service = ReferralService()
        user = g.current_user
        data = request.get_json()
        amount = data.get('amount')

        if not amount or amount <= 0:
            return jsonify({'error': '请输入有效金额'}), 400

        result = referral_service.withdraw_cash(user.id, amount)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', '提现失败')}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/referral/withdrawal-records', methods=['GET'])
@login_required
def withdrawal_records():
    """获取提现记录列表"""
    try:
        from models import CashWithdrawalRecord
        user = g.current_user
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        page_size = min(page_size, 50)

        query = CashWithdrawalRecord.query.filter_by(user_id=user.id).order_by(
            CashWithdrawalRecord.created_at.desc()
        )
        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            'success': True,
            'records': [r.to_dict() for r in records],
            'total': total,
            'page': page
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# 退款申请相关接口
# ============================================

@api_bp.route('/refund/recharge-options', methods=['GET'])
@login_required
def get_refund_recharge_options():
    """
    获取充值退款可选金额列表
    返回用户的充值记录，标注是否可退（绿色=可退，灰色=不可退）
    """
    try:
        from models import RechargeRecord, RefundApplication

        user = g.current_user

        # 检查是否有待处理的退款申请
        has_pending = RefundApplication.query.filter_by(
            user_id=user.id, status='pending'
        ).first() is not None

        # 获取所有充值记录（按时间倒序）
        orders = RechargeRecord.query.filter_by(
            user_id=user.id
        ).order_by(RechargeRecord.created_at.desc()).all()

        # 获取用户当前剪刀发丝数
        scissor_hairs = user.scissor_hairs or 0

        options = []
        for order in orders:
            amount = float(order.amount)
            order_scissor = order.scissor_hairs or 0
            status_val = order.payment_status

            # 判断是否可退
            can_refund = False
            refundable_amount = 0.0
            reason = ''

            if has_pending:
                reason = '有待处理申请'
            elif status_val == 'refunded':
                reason = '已退款'
            elif status_val != 'success':
                reason = f'状态: {status_val}'
            elif order_scissor == 0:
                reason = '发丝已耗尽'
            else:
                # 计算可退金额：基于剩余剪刀发丝比例
                ratio = min(1.0, scissor_hairs / order_scissor) if order_scissor > 0 else 0
                refundable_amount = round(amount * ratio, 2)
                if refundable_amount > 0:
                    can_refund = True
                else:
                    reason = '发丝已耗尽'

            options.append({
                'id': order.id,
                'amount': amount,
                'scissor_hairs': order_scissor,
                'comb_hairs': order.comb_hairs or 0,
                'payment_status': status_val,
                'created_at': order.created_at.isoformat() if order.created_at else '',
                'can_refund': can_refund,
                'refundable_amount': refundable_amount,
                'reason': reason,
                'display': f"¥{amount}{' (可退¥' + f'{refundable_amount}' + ')' if can_refund else ' (' + reason + ')'}"
            })

        return jsonify({
            'success': True,
            'options': options,
            'has_pending_refund': has_pending,
            'current_scissor_hairs': scissor_hairs
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/refund/calculate', methods=['POST'])
@login_required
def calculate_refund():
    """
    计算退款核算清单
    
    根据退款类型和金额，计算：
    - 应扣回发丝
    - 剩余发丝
    - 差额（不足部分）
    - 现金抵扣金额
    - 最终退款金额
    """
    try:
        from models import RechargeRecord, MemberOrder
        from datetime import datetime
        
        data = request.get_json()
        refund_type = data.get('refund_type')
        refund_amount = data.get('refund_amount')
        notify_admin = data.get('notify_admin', False)  # 是否通知管理员
        
        if not refund_type or refund_type not in ('recharge', 'membership'):
            return jsonify({'error': '退款类型不合法'}), 400
        
        user = g.current_user
        total_hairs = (user.scissor_hairs or 0) + (user.comb_hairs or 0)
        
        result = {
            'refund_type': refund_type,
            'user_info': {
                'nickname': user.nickname or '未设置',
                'phone': user.phone or '未绑定',
                'user_id': user.id
            }
        }
        
        if refund_type == 'recharge':
            # 充值退款计算
            order = RechargeRecord.query.filter_by(
                user_id=user.id, payment_status='success'
            ).order_by(RechargeRecord.created_at.desc()).first()

            if not order:
                return jsonify({'error': '没有可退款的充值订单'}), 400

            # 按退款比例计算应扣回的发丝
            # 梳子卡槽发丝是赠送的，客户未付费，退款时只扣回剪刀卡槽发丝
            refund_ratio = float(refund_amount) / float(order.amount)
            need_scissor = int(order.scissor_hairs * refund_ratio)
            hairs_to_deduct = need_scissor

            scissor_hairs = user.scissor_hairs or 0
            cash_deduction = 0.0
            actual_refund = float(refund_amount)

            if scissor_hairs >= hairs_to_deduct:
                # 剪刀发丝充足，全额退款
                pass
            else:
                # 剪刀发丝不足，差额用现金抵扣（0.01元/发丝）
                missing_hairs = hairs_to_deduct - scissor_hairs
                cash_deduction = round(missing_hairs * 0.01, 2)
                actual_refund = max(0, float(refund_amount) - cash_deduction)

            result.update({
                'charge_amount': float(order.amount),
                'charge_hairs': order.scissor_hairs + order.comb_hairs,
                'refund_amount_requested': float(refund_amount),
                'hairs_to_deduct': hairs_to_deduct,
                'total_hairs': total_hairs,
                'scissor_hairs': scissor_hairs,
                'comb_hairs': user.comb_hairs or 0,
                'hairs_sufficient': scissor_hairs >= hairs_to_deduct,
                'missing_hairs': max(0, hairs_to_deduct - scissor_hairs),
                'cash_deduction': cash_deduction,
                'actual_refund': actual_refund
            })
            
        elif refund_type == 'membership':
            # 会员退款计算
            if user.member_level != 'vip' or not user.member_expire_at:
                return jsonify({'error': '当前非会员状态'}), 400
            
            if user.member_expire_at < datetime.now():
                return jsonify({'error': '会员已过期'}), 400
            
            # 计算剩余天数和退款金额
            remaining_days = (user.member_expire_at - datetime.now()).days
            calculated_refund = int(99 * remaining_days / 365 * 100) / 100
            
            # 会员退款固定扣回 1000 发丝
            hairs_to_deduct = 1000
            cash_deduction = 0.0
            actual_refund = calculated_refund
            
            if total_hairs >= hairs_to_deduct:
                deduct_scissor = user.scissor_hairs or 0
                deduct_comb = user.comb_hairs or 0
            else:
                deduct_scissor = user.scissor_hairs or 0
                deduct_comb = user.comb_hairs or 0
                missing_hairs = hairs_to_deduct - total_hairs
                cash_deduction = round(missing_hairs * 0.01, 2)
                actual_refund = max(0, calculated_refund - cash_deduction)
            
            result.update({
                'member_price': 99,
                'remaining_days': remaining_days,
                'refund_amount_requested': calculated_refund,
                'hairs_to_deduct': hairs_to_deduct,
                'total_hairs': total_hairs,
                'scissor_hairs': user.scissor_hairs or 0,
                'comb_hairs': user.comb_hairs or 0,
                'hairs_sufficient': total_hairs >= hairs_to_deduct,
                'missing_hairs': max(0, hairs_to_deduct - total_hairs),
                'cash_deduction': cash_deduction,
                'actual_refund': actual_refund
            })
        
        # 如果客户查看了清单，通知管理员
        if notify_admin:
            try:
                from refund_notifier import RefundNotifier
                notifier = RefundNotifier()
                notifier.send_calculation_preview_notification(user, result)
            except Exception as e:
                print(f"⚠️ 发送核算清单通知失败: {e}")
        
        return jsonify({'success': True, 'calculation': result})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/refund/apply', methods=['POST'])
@login_required
def apply_refund():
    """提交退款申请"""
    try:
        from refund_service import RefundService

        data = request.get_json()
        refund_type = data.get('refund_type')
        refund_amount = data.get('refund_amount')
        reason = data.get('reason')
        applicant_name = data.get('applicant_name')
        applicant_phone = data.get('applicant_phone')
        suggestions = data.get('suggestions')

        if not refund_type or refund_type not in ('recharge', 'membership'):
            return jsonify({'error': '退款类型不合法'}), 400

        if not refund_amount or float(refund_amount) <= 0:
            return jsonify({'error': '退款金额不合法'}), 400

        if not reason or not reason.strip():
            return jsonify({'error': '请填写退款原因'}), 400

        if not applicant_name or not applicant_name.strip():
            return jsonify({'error': '请填写姓名'}), 400

        if not applicant_phone or not re.match(r'^1\d{10}$', applicant_phone):
            return jsonify({'error': '请填写正确的手机号'}), 400

        user = g.current_user
        refund_service = RefundService()
        result = refund_service.create_application(
            user=user,
            refund_type=refund_type,
            refund_amount=float(refund_amount),
            reason=reason.strip(),
            applicant_name=applicant_name.strip(),
            applicant_phone=applicant_phone.strip(),
            suggestions=suggestions.strip() if suggestions else None
        )

        if result['success']:
            return jsonify({
                'success': True,
                'application_id': result['application_id']
            })
        else:
            return jsonify({'error': result['error']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/refund/approve', methods=['GET'])
def approve_refund():
    """管理员审批退款申请（通过企业微信链接访问）"""
    try:
        from refund_service import RefundService

        token = request.args.get('token')
        action = request.args.get('action')
        rejection_reason = request.args.get('reason', '')

        if not token or not action:
            return jsonify({'error': '参数不完整'}), 400

        if action not in ('approve', 'reject'):
            return jsonify({'error': '操作类型不合法'}), 400

        # 验证 token
        application_id, error = RefundService.verify_approval_token(token)
        if error:
            return jsonify({'error': error}), 400

        # 执行审批（admin_user_id=0 表示系统管理员）
        refund_service = RefundService()
        result = refund_service.approve_application(
            application_id=application_id,
            admin_user_id=0,
            rejection_reason=rejection_reason if action == 'reject' else None
        )

        if result['success']:
            status_text = "同意" if result['status'] == 'approved' else "拒绝"
            return f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>退款审批结果</title>
            <style>
                body {{ font-family: -apple-system, sans-serif; padding: 40px 20px; text-align: center; background: #f5f5f5; }}
                .card {{ background: white; border-radius: 12px; padding: 30px; max-width: 400px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .icon {{ font-size: 48px; margin-bottom: 16px; }}
                h2 {{ margin: 0 0 8px; color: #333; }}
                p {{ color: #666; margin: 0; }}
            </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">{'✅' if result['status'] == 'approved' else '❌'}</div>
                    <h2>审批{status_text}</h2>
                    <p>退款申请已{status_text}处理</p>
                </div>
            </body>
            </html>
            """
        else:
            return jsonify({'error': result['error']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/refund/status/<int:application_id>', methods=['GET'])
@login_required
def refund_status(application_id):
    """查询退款申请状态"""
    try:
        from models import RefundApplication

        user = g.current_user
        application = RefundApplication.query.filter_by(
            id=application_id, user_id=user.id
        ).first()

        if not application:
            return jsonify({'error': '申请不存在'}), 404

        return jsonify({
            'success': True,
            'application': application.to_dict()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/refund/applications', methods=['GET'])
@login_required
def refund_applications_list():
    """获取当前用户的退款申请列表"""
    try:
        from models import RefundApplication

        user = g.current_user
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        query = RefundApplication.query.filter_by(user_id=user.id)\
            .order_by(RefundApplication.created_at.desc())

        total = query.count()
        applications = query.offset((page - 1) * page_size).limit(page_size).all()

        return jsonify({
            'success': True,
            'applications': [a.to_dict() for a in applications],
            'total': total,
            'page': page
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 实时聊天 API ====================

@api_bp.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    """用户发送聊天消息"""
    try:
        from chat_service import ChatService

        user = g.current_user
        data = request.get_json()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'success': False, 'error': '消息内容不能为空'}), 400

        success, message, chat_message = ChatService.send_message(user.id, content)
        if success:
            return jsonify({
                'success': True,
                'message': chat_message.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/chat/messages', methods=['GET'])
@login_required
def chat_get_messages():
    """获取聊天消息（增量轮询）"""
    try:
        from chat_service import ChatService

        user = g.current_user
        since = request.args.get('since', None)
        limit = request.args.get('limit', 50, type=int)

        messages = ChatService.get_messages(user.id, since=since, limit=limit)
        unread_count = ChatService.get_unread_count(user.id)

        return jsonify({
            'success': True,
            'messages': [m.to_dict() for m in messages],
            'unread_count': unread_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/chat/unread-count', methods=['GET'])
@login_required
def chat_unread_count():
    """获取未读消息数"""
    try:
        from chat_service import ChatService

        user = g.current_user
        count = ChatService.get_unread_count(user.id)

        return jsonify({
            'success': True,
            'unread_count': count
        })

    except Exception as e:
        import logging
        logging.error(f'Chat unread count error: {e}')
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@api_bp.route('/chat/mark-read', methods=['POST'])
@login_required
def chat_mark_read():
    """标记所有未读消息为已读（清除角标）"""
    try:
        from models import Message
        from models import ChatMessage

        user = g.current_user

        # 1. 标记聊天消息为已读
        ChatMessage.query.filter_by(
            user_id=user.id,
            sender_type='admin',
            is_read=False
        ).update({'is_read': True})

        # 2. 标记留言为已处理（resolved）
        Message.query.filter_by(
            user_id=user.id,
            status='processing'
        ).update({'status': 'resolved'})

        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        import logging
        logging.error(f'Chat mark-read error: {e}')
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@api_bp.route('/chat/reply', methods=['GET', 'POST'])
def chat_reply():
    """
    管理员回复页面（H5）
    支持两种来源：
    1. 用户聊天消息（token = user_id）
    2. 客户留言（token = phone）
    GET: 显示回复表单
    POST: 提交回复
    """
    from chat_service import verify_reply_token, ChatService
    from flask import render_template_string

    token = request.args.get('token', '') or (request.form.get('token', '') if request.form else '')

    # 验证 token
    identifier, id_type = verify_reply_token(token)
    if not identifier:
        return render_template_string('''
            <html><head><meta charset="utf-8"><title>链接无效</title></head>
            <body style="padding:40px;text-align:center;font-family:sans-serif;">
                <h2>链接已过期或无效</h2>
                <p>请从企业微信中重新点击通知链接</p>
            </body></html>
        '''), 403

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            return render_template_string('''
                <html><head><meta charset="utf-8"><title>回复失败</title></head>
                <body style="padding:40px;text-align:center;font-family:sans-serif;">
                    <h2>回复内容不能为空</h2>
                    <a href="javascript:history.back()">返回</a>
                </body></html>
            '''), 400

        if id_type == 'user_id':
            # 回复聊天消息
            success, message, chat_message = ChatService.reply_message(identifier, content)
            if success:
                from models import User
                user = User.query.get(identifier)
                user_info = f"{user.nickname or '用户'}（{user.phone or '未绑定手机'}）" if user else '用户'
                return render_template_string('''
                    <html><head><meta charset="utf-8"><title>回复成功</title></head>
                    <body style="padding:40px;text-align:center;font-family:sans-serif;">
                        <h2 style="color:#07c160;">✅ 回复成功</h2>
                        <p>已回复给 {{ user_info }}</p>
                        <p style="margin-top:30px;"><a href="javascript:history.back()">继续回复</a></p>
                    </body></html>
                ''', user_info=user_info)
            else:
                return render_template_string('''
                    <html><head><meta charset="utf-8"><title>回复失败</title></head>
                    <body style="padding:40px;text-align:center;font-family:sans-serif;">
                        <h2 style="color:red;">回复失败</h2>
                        <p>{{ error }}</p>
                        <a href="javascript:history.back()">返回</a>
                    </body></html>
                ''', error=message), 500
        else:
            # 回复留言：标记为已处理
            from models import Message
            msg = Message.query.filter_by(phone=identifier, status='pending').order_by(
                Message.created_at.desc()
            ).first()
            if msg:
                msg.status = 'processing'
                db.session.commit()
                print(f"✅ 留言已标记为处理中: id={msg.id}, phone={identifier}")

            return render_template_string('''
                <html><head><meta charset="utf-8"><title>已收到回复</title></head>
                <body style="padding:40px;text-align:center;font-family:sans-serif;">
                    <h2 style="color:#07c160;">✅ 已收到回复</h2>
                    <p>该留言已标记为处理中，后续可通过电话 {{ phone }} 联系客户</p>
                </body></html>
            ''', phone=identifier)

    # GET: 显示回复表单
    from models import User, ChatMessage, Message

    if id_type == 'user_id':
        user = User.query.get(identifier)
        user_info = f"{user.nickname or '用户'}（{user.phone or '未绑定手机'}）" if user else '用户'
        source_type = 'chat'

        # 获取最近的聊天记录
        recent_messages = ChatMessage.query.filter_by(user_id=identifier)\
            .order_by(ChatMessage.created_at.desc()).limit(10).all()
        recent_messages.reverse()
    else:
        # 留言来源
        msg = Message.query.filter_by(phone=identifier).order_by(
            Message.created_at.desc()
        ).first()
        if msg:
            user_info = f"{msg.name}（{msg.phone}）"
            if msg.status == 'pending':
                msg.status = 'processing'
                db.session.commit()
        else:
            user_info = f"留言用户（{identifier}）"
        source_type = 'message'
        recent_messages = []

    return render_template_string('''
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ '回复留言' if source_type == 'message' else '回复用户消息' }}</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
                .header { background: #07c160; color: white; padding: 16px; text-align: center; }
                .header h2 { font-size: 18px; }
                .user-info { background: white; padding: 12px 16px; border-bottom: 1px solid #eee; }
                .user-info span { color: #666; font-size: 14px; }
                .messages { padding: 16px; max-height: 400px; overflow-y: auto; }
                .message { margin-bottom: 12px; padding: 10px 14px; border-radius: 8px; max-width: 80%; font-size: 14px; line-height: 1.5; }
                .message.user { background: #95ec69; margin-left: auto; }
                .message.admin { background: white; margin-right: auto; }
                .message .time { font-size: 11px; color: #999; margin-top: 4px; }
                .reply-form { position: fixed; bottom: 0; left: 0; right: 0; background: white; padding: 12px; border-top: 1px solid #eee; display: flex; gap: 8px; }
                .reply-form textarea { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; resize: none; height: 44px; }
                .reply-form button { padding: 0 20px; background: #07c160; color: white; border: none; border-radius: 6px; font-size: 14px; }
                .reply-form button:active { background: #06ad56; }
                .spacer { height: 80px; }
                .message-content { background: white; padding: 16px; margin: 12px; border-radius: 8px; }
                .message-content p { margin-bottom: 8px; font-size: 14px; line-height: 1.6; }
                .message-content .label { color: #999; }
                .message-content .value { color: #333; }
                {% if source_type == 'message' %}
                .phone-link { color: #07c160; text-decoration: none; }
                .phone-link:active { color: #06ad56; }
                {% endif %}
            </style>
        </head>
        <body>
            <div class="header"><h2>{{ '回复留言' if source_type == 'message' else '回复用户消息' }}</h2></div>
            <div class="user-info"><span>来源：{{ user_info }}</span></div>
            {% if source_type == 'message' %}
            <div class="message-content">
                {% if msg %}
                <p><span class="label">姓名：</span><span class="value">{{ msg.name }}</span></p>
                <p><span class="label">电话：</span><a class="phone-link" href="tel:{{ msg.phone }}">{{ msg.phone }}</a></p>
                <p><span class="label">留言：</span></p>
                <p style="white-space:pre-wrap;">{{ msg.content }}</p>
                <p style="color:#999;font-size:12px;margin-top:8px;">{{ msg.created_at.strftime('%Y-%m-%d %H:%M') }}</p>
                {% endif %}
            </div>
            {% else %}
            <div class="messages">
                {% for m in messages %}
                <div class="message {{ m.sender_type }}">
                    {{ m.content }}
                    <div class="time">{{ m.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            <div class="spacer"></div>
            <form class="reply-form" method="POST" action="/api/chat/reply">
                <input type="hidden" name="token" value="{{ token }}">
                <textarea name="content" placeholder="{{ '输入回复备注（可选）' if source_type == 'message' else '输入回复...' }}" ></textarea>
                <button type="submit">{{ '确认已处理' if source_type == 'message' else '发送' }}</button>
            </form>
        </body>
        </html>
    ''', user_info=user_info, messages=recent_messages, token=token, source_type=source_type, msg=msg if id_type == 'message' else None)


# ==================== 财务流水 API ====================

@api_bp.route('/financial/records', methods=['GET'])
@login_required
def get_financial_records():
    """获取用户财务流水记录"""
    try:

        user = g.current_user
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        record_type = request.args.get('record_type', None)  # 可选：按类型筛选

        result = FinancialService.get_user_financial_records(
            user_id=user.id,
            page=page,
            page_size=page_size,
            record_type=record_type
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/financial/summary', methods=['GET'])
@login_required
def get_financial_summary():
    """获取用户财务汇总统计"""
    try:
        from models import FinancialRecord
        from decimal import Decimal

        user = g.current_user

        # 总收入（充值）
        total_recharge = db.session.query(
            db.func.sum(FinancialRecord.amount)
        ).filter(
            FinancialRecord.user_id == user.id,
            FinancialRecord.record_type == 'recharge',
            FinancialRecord.status == 'success'
        ).scalar() or Decimal('0')

        # 总支出（退款为负数，取绝对值）
        total_refund = db.session.query(
            db.func.sum(db.func.abs(FinancialRecord.amount))
        ).filter(
            FinancialRecord.user_id == user.id,
            FinancialRecord.record_type == 'refund',
            FinancialRecord.status == 'success'
        ).scalar() or Decimal('0')

        # 推广总收入
        total_commission = db.session.query(
            db.func.sum(FinancialRecord.amount)
        ).filter(
            FinancialRecord.user_id == user.id,
            FinancialRecord.record_type == 'commission',
            FinancialRecord.status == 'success'
        ).scalar() or Decimal('0')

        # 提现总支出
        total_withdrawal = db.session.query(
            db.func.sum(db.func.abs(FinancialRecord.amount))
        ).filter(
            FinancialRecord.user_id == user.id,
            FinancialRecord.record_type == 'withdrawal',
            FinancialRecord.status == 'success'
        ).scalar() or Decimal('0')

        # 本地消费支出
        total_cash_consumption = db.session.query(
            db.func.sum(db.func.abs(FinancialRecord.amount))
        ).filter(
            FinancialRecord.user_id == user.id,
            FinancialRecord.record_type == 'cash_consumption',
            FinancialRecord.status == 'success'
        ).scalar() or Decimal('0')

        return jsonify({
            'success': True,
            'summary': {
                'total_recharge': float(total_recharge),
                'total_refund': float(total_refund),
                'total_commission': float(total_commission),
                'total_withdrawal': float(total_withdrawal),
                'total_cash_consumption': float(total_cash_consumption),
                'net_recharge': float(total_recharge - total_refund),
                'net_commission': float(total_commission - total_withdrawal - total_cash_consumption)
            }
        })

    except Exception as e:
        import logging
        logging.error(f'Financial summary error: {e}')
        return jsonify({'error': '服务器内部错误'}), 500


# ============================================
# 开发者端客户档案 API
# ============================================

def _mask_phone(phone):
    """手机号脱敏：中间 4 位替换为 ****"""
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + '****' + phone[7:]


def _check_dev_permission():
    """检查开发者权限，非开发者返回 404（不暴露接口存在）"""
    auth_service = AuthService()
    user = auth_service.get_current_user()
    if not user or not is_developer(user.id):
        return None, (jsonify({'success': False, 'error': '资源不存在'}), 404)
    return user, None


@api_bp.route('/dev/dashboard', methods=['GET'])
def dev_dashboard():
    """
    客户存量大盘
    - 用户级别分布统计（guest/normal/vip_active/vip_expired）
    - 资产总览（总用户数、流通发丝总量、累计充值金额、人均充值）
    - Redis 缓存 300 秒
    """
    user, err = _check_dev_permission()
    if err:
        return err

    try:
        from cache_service import get_cache_service
        cache = get_cache_service()
        cache_key = 'dev:dashboard:v1'

        # 尝试从缓存读取
        cached = cache.get(cache_key)
        if cached:
            return jsonify({'success': True, **cached})

        # 用户级别分布统计
        # guest 用户数
        guest_count = User.query.filter_by(user_type='guest').count()
        # normal 用户数（registered 且 member_level='normal'）
        normal_count = User.query.filter_by(user_type='registered', member_level='normal').count()
        # vip_active：registered 且 member_level='vip' 且未过期
        now = datetime.now()
        vip_active_count = User.query.filter(
            User.user_type == 'registered',
            User.member_level == 'vip',
            User.member_expire_at > now
        ).count()
        # vip_expired：registered 且 member_level='vip' 但已过期
        vip_expired_count = User.query.filter(
            User.user_type == 'registered',
            User.member_level == 'vip',
            User.member_expire_at <= now
        ).count()

        # 资产总览
        total_users = User.query.count()
        # 流通发丝总量（scissor_hairs + comb_hairs）
        total_hairs_result = db.session.query(
            sql_func.coalesce(sql_func.sum(User.scissor_hairs), 0),
            sql_func.coalesce(sql_func.sum(User.comb_hairs), 0)
        ).first()
        total_scissor_hairs = int(total_hairs_result[0] or 0)
        total_comb_hairs = int(total_hairs_result[1] or 0)
        total_hairs = total_scissor_hairs + total_comb_hairs

        # 累计充值金额
        total_recharge_result = db.session.query(
            sql_func.coalesce(sql_func.sum(User.total_recharge), 0)
        ).scalar()
        total_recharge = float(total_recharge_result or 0)

        # 人均充值
        avg_recharge = round(total_recharge / total_users, 2) if total_users > 0 else 0

        data = {
            'user_distribution': {
                'guest': guest_count,
                'normal': normal_count,
                'vip_active': vip_active_count,
                'vip_expired': vip_expired_count,
            },
            'overview': {
                'total_users': total_users,
                'total_hairs': total_hairs,
                'total_scissor_hairs': total_scissor_hairs,
                'total_comb_hairs': total_comb_hairs,
                'total_recharge': total_recharge,
                'avg_recharge': avg_recharge,
            }
        }

        # 写入缓存
        cache.set(cache_key, data, expire_seconds=300)

        return jsonify({'success': True, **data})

    except Exception as e:
        import logging
        logging.error(f'Dev dashboard error: {e}')
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@api_bp.route('/dev/customers', methods=['GET'])
def dev_customers():
    """
    客户全景列表
    - 分页查询（page, page_size，上限 100）
    - 排序支持：created_at_desc/asc, recharge_desc, hairs_desc, last_active
    - 筛选支持：member_level, user_type, phone（模糊）, nickname（模糊）
    - 手机号脱敏
    """
    user, err = _check_dev_permission()
    if err:
        return err

    try:
        # 分页参数
        page = max(int(request.args.get('page', 1)), 1)
        page_size = min(max(int(request.args.get('page_size', 20)), 1), 100)

        # 排序参数
        sort_by = request.args.get('sort_by', 'created_at_desc')

        # 筛选参数
        filter_level = request.args.get('level')  # guest/normal/vip
        filter_phone = request.args.get('phone', '').strip()
        filter_nickname = request.args.get('nickname', '').strip()

        # 构建查询
        query = User.query

        # 应用筛选（三级分类：游客/普通/会员）
        if filter_level:
            if filter_level == 'guest':
                query = query.filter(User.user_type == 'guest')
            elif filter_level == 'normal':
                query = query.filter(User.user_type == 'registered', User.member_level == 'normal')
            elif filter_level == 'vip':
                query = query.filter(User.user_type == 'registered', User.member_level == 'vip')
        if filter_phone:
            query = query.filter(User.phone.like(f'%{filter_phone}%'))
        if filter_nickname:
            query = query.filter(User.nickname.like(f'%{filter_nickname}%'))

        # 应用排序
        if sort_by == 'created_at_asc':
            query = query.order_by(User.created_at.asc())
        elif sort_by == 'recharge_desc':
            query = query.order_by(User.total_recharge.desc())
        elif sort_by == 'hairs_desc':
            # 按总发丝排序（scissor_hairs + comb_hairs）
            query = query.order_by((User.scissor_hairs + User.comb_hairs).desc())
        elif sort_by == 'last_active':
            # 按最后活跃时间排序（使用 updated_at 近似）
            query = query.order_by(User.updated_at.desc())
        else:
            # 默认按创建时间倒序
            query = query.order_by(User.created_at.desc())

        # 总数
        total = query.count()

        # 分页
        users = query.offset((page - 1) * page_size).limit(page_size).all()

        # 格式化结果
        items = []
        for u in users:
            items.append({
                'id': u.id,
                'nickname': u.nickname,
                'phone': _mask_phone(u.phone),
                'user_type': u.user_type,
                'member_level': u.member_level,
                'member_expire_at': u.member_expire_at.isoformat() if u.member_expire_at else None,
                'scissor_hairs': u.scissor_hairs,
                'comb_hairs': u.comb_hairs,
                'total_hairs': (u.scissor_hairs or 0) + (u.comb_hairs or 0),
                'total_recharge': float(u.total_recharge or 0),
                'total_consumed_hairs': u.total_consumed_hairs or 0,
                'is_vip': u.is_vip(),
                'created_at': u.created_at.isoformat() if u.created_at else None,
                'updated_at': u.updated_at.isoformat() if u.updated_at else None,
            })

        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if page_size > 0 else 0,
            }
        })

    except Exception as e:
        import logging
        logging.error(f'Dev customers error: {e}')
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@api_bp.route('/dev/customers/<int:customer_id>', methods=['GET'])
def dev_customer_detail(customer_id):
    """
    客户详情
    - 返回完整用户信息 + 最近 10 条消费/财务/充值记录
    - Redis 缓存 120 秒
    """
    user, err = _check_dev_permission()
    if err:
        return err

    try:
        from cache_service import get_cache_service
        cache = get_cache_service()
        cache_key = f'dev:customer:{customer_id}:v1'

        # 尝试从缓存读取
        cached = cache.get(cache_key)
        if cached:
            return jsonify({'success': True, **cached})

        # 查询用户
        target_user = User.query.get(customer_id)
        if not target_user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        # 最近 10 条消费记录
        consumption_records = ConsumptionRecord.query.filter_by(
            user_id=customer_id
        ).order_by(ConsumptionRecord.created_at.desc()).limit(10).all()

        # 最近 10 条财务记录
        financial_records = FinancialRecord.query.filter_by(
            user_id=customer_id
        ).order_by(FinancialRecord.created_at.desc()).limit(10).all()

        # 最近 10 条充值记录
        recharge_records = RechargeRecord.query.filter_by(
            user_id=customer_id
        ).order_by(RechargeRecord.created_at.desc()).limit(10).all()

        data = {
            'user': {
                'id': target_user.id,
                'openid': target_user.openid,
                'unionid': target_user.unionid,
                'phone': _mask_phone(target_user.phone),
                'device_id': target_user.device_id,
                'nickname': target_user.nickname,
                'avatar_url': target_user.avatar_url,
                'member_level': target_user.member_level,
                'member_expire_at': target_user.member_expire_at.isoformat() if target_user.member_expire_at else None,
                'scissor_hairs': target_user.scissor_hairs,
                'comb_hairs': target_user.comb_hairs,
                'total_hairs': (target_user.scissor_hairs or 0) + (target_user.comb_hairs or 0),
                'total_recharge': float(target_user.total_recharge or 0),
                'total_consumed_hairs': target_user.total_consumed_hairs or 0,
                'user_type': target_user.user_type,
                'is_vip': target_user.is_vip(),
                'is_deactivated': target_user.is_deactivated,
                'cash_balance': float(target_user.cash_balance or 0),
                'total_referral_earnings': float(target_user.total_referral_earnings or 0),
                'referral_code': target_user.referral_code,
                'referral_count': target_user.referral_count or 0,
                'created_at': target_user.created_at.isoformat() if target_user.created_at else None,
                'updated_at': target_user.updated_at.isoformat() if target_user.updated_at else None,
            },
            'consumption_records': [r.to_dict() for r in consumption_records],
            'financial_records': [r.to_dict() for r in financial_records],
            'recharge_records': [r.to_dict() for r in recharge_records],
        }

        # 写入缓存
        cache.set(cache_key, data, expire_seconds=120)

        return jsonify({'success': True, **data})

    except Exception as e:
        import logging
        logging.error(f'Dev customer detail error: {e}')
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@api_bp.route('/dev/search', methods=['GET'])
def dev_search():
    """
    精准查询
    - 参数：phone（完整手机号，精确匹配）
    - 返回客户详情，额外返回 found: true/false
    """
    user, err = _check_dev_permission()
    if err:
        return err

    try:
        phone = request.args.get('phone', '').strip()
        if not phone:
            return jsonify({'success': False, 'error': '缺少 phone 参数'}), 400

        # 精确匹配手机号
        target_user = User.query.filter_by(phone=phone).first()

        if not target_user:
            return jsonify({
                'success': True,
                'found': False,
                'user': None,
                'consumption_records': [],
                'financial_records': [],
                'recharge_records': [],
            })

        # 最近 10 条消费记录
        consumption_records = ConsumptionRecord.query.filter_by(
            user_id=target_user.id
        ).order_by(ConsumptionRecord.created_at.desc()).limit(10).all()

        # 最近 10 条财务记录
        financial_records = FinancialRecord.query.filter_by(
            user_id=target_user.id
        ).order_by(FinancialRecord.created_at.desc()).limit(10).all()

        # 最近 10 条充值记录
        recharge_records = RechargeRecord.query.filter_by(
            user_id=target_user.id
        ).order_by(RechargeRecord.created_at.desc()).limit(10).all()

        return jsonify({
            'success': True,
            'found': True,
            'user': {
                'id': target_user.id,
                'openid': target_user.openid,
                'unionid': target_user.unionid,
                'phone': _mask_phone(target_user.phone),
                'device_id': target_user.device_id,
                'nickname': target_user.nickname,
                'avatar_url': target_user.avatar_url,
                'member_level': target_user.member_level,
                'member_expire_at': target_user.member_expire_at.isoformat() if target_user.member_expire_at else None,
                'scissor_hairs': target_user.scissor_hairs,
                'comb_hairs': target_user.comb_hairs,
                'total_hairs': (target_user.scissor_hairs or 0) + (target_user.comb_hairs or 0),
                'total_recharge': float(target_user.total_recharge or 0),
                'total_consumed_hairs': target_user.total_consumed_hairs or 0,
                'user_type': target_user.user_type,
                'is_vip': target_user.is_vip(),
                'is_deactivated': target_user.is_deactivated,
                'cash_balance': float(target_user.cash_balance or 0),
                'total_referral_earnings': float(target_user.total_referral_earnings or 0),
                'referral_code': target_user.referral_code,
                'referral_count': target_user.referral_count or 0,
                'created_at': target_user.created_at.isoformat() if target_user.created_at else None,
                'updated_at': target_user.updated_at.isoformat() if target_user.updated_at else None,
            },
            'consumption_records': [r.to_dict() for r in consumption_records],
            'financial_records': [r.to_dict() for r in financial_records],
            'recharge_records': [r.to_dict() for r in recharge_records],
        })

    except Exception as e:
        import logging
        logging.error(f'Dev search error: {e}')
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@api_bp.route('/dev/today', methods=['GET'])
def dev_today():
    """
    今日动态看板
    - 今日新增用户（总数 + 分级别）
    - 今日活跃用户（有消费记录的去重用户数）
    - 今日充值金额/笔数
    - 今日消费笔数（按 service_type 分组）
    - Redis 缓存 60 秒
    """
    user, err = _check_dev_permission()
    if err:
        return err

    try:
        from cache_service import get_cache_service
        cache = get_cache_service()
        today_str = datetime.now().strftime('%Y-%m-%d')
        cache_key = f'dev:today:v1:{today_str}'

        # 尝试从缓存读取
        cached = cache.get(cache_key)
        if cached:
            return jsonify({'success': True, **cached})

        # 今日时间范围
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 今日新增用户（总数）
        new_users_total = User.query.filter(User.created_at >= today_start).count()

        # 今日新增用户（分级别）
        new_users_guest = User.query.filter(
            User.created_at >= today_start, User.user_type == 'guest'
        ).count()
        new_users_normal = User.query.filter(
            User.created_at >= today_start, User.user_type == 'registered', User.member_level == 'normal'
        ).count()
        new_users_vip = User.query.filter(
            User.created_at >= today_start, User.user_type == 'registered', User.member_level == 'vip'
        ).count()

        # 今日活跃用户（有消费记录的去重用户数）
        active_users_result = db.session.query(
            sql_func.count(sql_func.distinct(ConsumptionRecord.user_id))
        ).filter(
            ConsumptionRecord.created_at >= today_start
        ).scalar()
        active_users = int(active_users_result or 0)

        # 今日充值金额/笔数（仅统计成功的充值记录）
        recharge_result = db.session.query(
            sql_func.count(RechargeRecord.id),
            sql_func.coalesce(sql_func.sum(RechargeRecord.amount), 0)
        ).filter(
            RechargeRecord.created_at >= today_start,
            RechargeRecord.payment_status == 'success'
        ).first()
        today_recharge_count = int(recharge_result[0] or 0)
        today_recharge_amount = float(recharge_result[1] or 0)

        # 今日消费笔数（按 service_type 分组）
        consumption_by_type = db.session.query(
            ConsumptionRecord.service_type,
            sql_func.count(ConsumptionRecord.id)
        ).filter(
            ConsumptionRecord.created_at >= today_start,
            ConsumptionRecord.status == 'success'
        ).group_by(ConsumptionRecord.service_type).all()

        consumption_type_stats = {row[0]: int(row[1]) for row in consumption_by_type}
        today_consumption_total = sum(consumption_type_stats.values())

        data = {
            'date': today_str,
            'new_users': {
                'total': new_users_total,
                'guest': new_users_guest,
                'normal': new_users_normal,
                'vip': new_users_vip,
            },
            'active_users': active_users,
            'recharge': {
                'count': today_recharge_count,
                'amount': today_recharge_amount,
            },
            'consumption': {
                'total': today_consumption_total,
                'by_service_type': consumption_type_stats,
            }
        }

        # 写入缓存
        cache.set(cache_key, data, expire_seconds=60)

        return jsonify({'success': True, **data})

    except Exception as e:
        import logging
        logging.error(f'Dev today error: {e}')
        return jsonify({'success': False, 'error': '服务器内部错误'}), 500


# ============================================
# 全局错误处理（防止堆栈泄漏）
# ============================================

@api_bp.errorhandler(500)
def handle_internal_error(error):
    """处理500错误，返回通用消息"""
    import logging
    logging.error(f'Internal server error: {error}')
    return jsonify({'error': '服务器内部错误'}), 500


@api_bp.errorhandler(404)
def handle_not_found(error):
    """处理404错误"""
    return jsonify({'error': '请求的资源不存在'}), 404


@api_bp.errorhandler(405)
def handle_method_not_allowed(error):
    """处理405错误"""
    return jsonify({'error': '不支持的请求方法'}), 405
