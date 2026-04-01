#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由模块
商业化相关API接口
"""

from flask import Blueprint, request, jsonify, g
import json
import time
import config

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 设置JSON响应的中文编码
def json_response(data, status=200):
    """返回JSON响应，确保中文正确编码"""
    response = jsonify(data)
    response.status_code = status
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response
from auth import AuthService, login_required, vip_required, optional_login
from sms_service import SMSService
from payment_service import PaymentService
from hair_service import HairService
from member_service import MemberService
from account_service import AccountService
from models import db, User, ConsumptionRecord, HistoryRecord

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
        
        auth_service = AuthService()
        result = auth_service.wechat_login(code)
        
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
        
        if not phone or not code:
            return jsonify({'error': '缺少phone或code参数'}), 400
        
        auth_service = AuthService()
        result = auth_service.phone_login(phone, code)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/bind-phone', methods=['POST'])
@login_required
def bind_phone():
    """绑定手机号"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        code = data.get('code')
        
        if not phone or not code:
            return jsonify({'error': '缺少phone或code参数'}), 400
        
        user = g.current_user
        auth_service = AuthService()
        result = auth_service.bind_phone(user.id, phone, code)
        
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
@login_required
def get_user_info():
    """获取用户信息"""
    try:
        user = g.current_user
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
        result = payment_service.create_recharge_order(user.id, amount, payment_method)
        
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
            # 清除登录信息
            from auth import AuthService
            auth_service = AuthService()
            auth_service.clearLoginInfo()

            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/upload', methods=['POST'])
@login_required
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
# 开发者工具接口
# ============================================

@api_bp.route('/dev/toggle-vip', methods=['POST'])
@login_required
def toggle_vip():
    """
    切换会员等级（开发者/管理员专属）
    用于开发测试时快速切换会员状态
    """
    try:
        from auth import is_developer

        user = g.current_user

        # 检查是否为开发者账号
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
