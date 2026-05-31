#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由模块
商业化相关API接口
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import json
import time
import config
from auth import AuthService, login_required, vip_required, optional_login
from sms_service import SMSService
from payment_service import PaymentService
from hair_service import HairService
from member_service import MemberService
from account_service import AccountService
from models import db, User, ConsumptionRecord, HistoryRecord, Device, Message

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')


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
        from config import RECHARGE_RULES
        
        rules = []
        for amount, rule in RECHARGE_RULES.items():
            rules.append({
                'amount': amount,
                'scissor_hairs': rule['scissor_hairs'],
                'comb_hairs': rule['comb_hairs'],
                'total_hairs': rule['scissor_hairs'] + rule['comb_hairs']
            })
        
        return jsonify({'rules': rules})
        
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

            # 开发环境下返回模拟支付参数
            from config import get_config
            _config = get_config()
            if _config.DEBUG:
                return jsonify({
                    'success': True,
                    'prepay_id': 'mock_prepay_id',
                    'wxpay_params': {
                        'timeStamp': str(int(time.time())),
                        'nonceStr': 'mock_nonce_str',
                        'package': 'prepay_id=mock_prepay_id',
                        'signType': 'RSA',
                        'paySign': 'mock_pay_sign',
                        'total_fee': float(order.amount) * 100  # 单位：分
                    },
                    'mock': True  # 标记为模拟支付
                })

            # 创建微信支付订单
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


@api_bp.route('/recharge/callback/wechat', methods=['POST'])
def wechat_pay_callback():
    """微信支付回调 - 充值"""
    try:
        from payment_service import WeChatPayService, PaymentService

        # 获取回调数据
        request_data = request.get_json()

        print(f"\n📨 收到微信支付回调 (充值)")

        # 验证签名并解密数据
        wechat_service = WeChatPayService()
        verify_result = wechat_service.verify_callback(request_data)

        if not verify_result['success']:
            print(f"❌ 微信支付回调验证失败: {verify_result['error']}")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=False,
                message=verify_result['error']
            ))

        # 处理订单
        order_no = verify_result['data']['order_no']
        transaction_id = verify_result['data']['transaction_id']

        print(f"   订单号: {order_no}")
        print(f"   微信订单号: {transaction_id}")

        payment_service = PaymentService()
        process_result = payment_service.process_recharge_success(
            order_no=order_no,
            transaction_id=transaction_id
        )

        if process_result['success']:
            print(f"✅ 充值订单处理成功")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=True,
                message='OK'
            ))
        else:
            print(f"❌ 处理充值失败: {process_result['error']}")
            return jsonify(wechat_service.wechat_pay.generate_response(
                success=False,
                message=process_result['error']
            ))

    except Exception as e:
        print(f"❌ 微信支付回调处理异常: {e}")
        import traceback
        traceback.print_exc()
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

            # 开发环境下返回模拟支付参数
            from config import get_config
            _config = get_config()
            if _config.DEBUG:
                return jsonify({
                    'success': True,
                    'prepay_id': 'mock_prepay_id',
                    'wxpay_params': {
                        'timeStamp': str(int(time.time())),
                        'nonceStr': 'mock_nonce_str',
                        'package': 'prepay_id=mock_prepay_id',
                        'signType': 'RSA',
                        'paySign': 'mock_pay_sign',
                        'total_fee': float(order.amount) * 100  # 单位：分
                    },
                    'mock': True  # 标记为模拟支付
                })

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
        return jsonify({'error': str(e)}), 500


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
            return jsonify({'error': '该类型图片不存在'}, 404)

        # 这里需要返回图片URL或直接返回图片
        
        return jsonify({
            'success': True,
            'download_url': image_url,
            'image_type': image_type,
            'record_id': record_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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

        # 返回完整URL
        # 获取请求的协议和主机
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
        
        # 创建留言记录（使用 SQLAlchemy ORM，自动防 SQL 注入）
        message = Message(
            name=name.strip(),
            phone=phone.strip(),
            content=content.strip()
        )
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '留言提交成功，感谢您的反馈！'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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

        if not order_type or not amount or not goods_key:
            return jsonify({"error": "参数不完整"}), 400

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
            # 计算头发丝数量（1元=10根）
            hairs = int(amount * 10)
            order = RechargeRecord(
                user_id=user.id,
                order_no=order_no,
                amount=amount,
                scissor_hairs=hairs,
                comb_hairs=0,
                payment_method="wechat_virtual",
                payment_status=payment_status,
            )
            db.session.add(order)
            
            # 开发者模式：立即充值
            if is_developer:
                user.comb_hairs += hairs
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
            order = RechargeRecord.query.filter_by(order_no=order_no).first()
            if order:
                payment_service.process_recharge_success(order_no)
            else:
                order = MemberOrder.query.filter_by(order_no=order_no).first()
                if order:
                    payment_service.process_member_success(order_no)

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
    """获取提现记录"""
    try:
        from models import CashWithdrawalRecord
        user = g.current_user

        records = CashWithdrawalRecord.query.filter_by(user_id=user.id)\
            .order_by(CashWithdrawalRecord.created_at.desc())\
            .limit(20).all()

        return jsonify({
            'success': True,
            'records': [r.to_dict() for r in records]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
