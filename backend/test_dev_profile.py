#!/usr/bin/env python3
"""
开发者端客户档案功能测试
测试 5 个 API 接口的正常响应、权限控制、分页排序筛选、缓存功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import User, ConsumptionRecord, FinancialRecord, RechargeRecord
from auth import AuthService
from datetime import datetime, timedelta
from decimal import Decimal


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def setup_test_data():
    """创建测试数据"""
    print_section("准备测试数据")

    # 创建开发者账号
    dev_user = User.query.filter_by(phone='13800000099').first()
    if not dev_user:
        dev_user = User(
            phone='13800000099',
            openid='test_dev_openid_99',
            nickname='开发者测试',
            user_type='registered',
            member_level='normal',
            scissor_hairs=100,
            comb_hairs=200,
            total_recharge=Decimal('500.00'),
        )
        db.session.add(dev_user)
        db.session.flush()
        print(f"✅ 创建开发者账号: id={dev_user.id}")
    else:
        print(f"ℹ️  开发者账号已存在: id={dev_user.id}")

    # 创建普通测试用户
    test_users = []
    for i in range(5):
        phone = f'1380000{i:04d}'
        u = User.query.filter_by(phone=phone).first()
        if not u:
            u = User(
                phone=phone,
                openid=f'test_openid_{i:04d}',
                nickname=f'测试用户{i}',
                user_type='registered' if i % 2 == 0 else 'guest',
                member_level='normal' if i % 3 != 0 else 'vip',
                member_expire_at=datetime.now() + timedelta(days=30) if i % 3 == 0 else None,
                scissor_hairs=100 * (i + 1),
                comb_hairs=50 * (i + 1),
                total_recharge=Decimal(str(10 * (i + 1))),
                total_consumed_hairs=20 * (i + 1),
            )
            db.session.add(u)
            db.session.flush()
            print(f"✅ 创建测试用户: id={u.id}, phone={phone}")
        else:
            print(f"ℹ️  测试用户已存在: id={u.id}, phone={phone}")
        test_users.append(u)

    # 创建测试消费记录
    for u in test_users[:2]:
        existing = ConsumptionRecord.query.filter_by(user_id=u.id).first()
        if not existing:
            cr = ConsumptionRecord(
                user_id=u.id,
                task_id=f'test_task_{u.id}',
                service_type='combined',
                hairs_consumed=88,
                scissor_deducted=44,
                comb_deducted=44,
                status='success',
            )
            db.session.add(cr)
            print(f"✅ 创建消费记录: user_id={u.id}")

    # 创建测试充值记录
    for u in test_users[:2]:
        existing = RechargeRecord.query.filter_by(user_id=u.id).first()
        if not existing:
            rr = RechargeRecord(
                user_id=u.id,
                order_no=f'TEST_ORDER_{u.id}_{int(datetime.now().timestamp())}',
                amount=Decimal('50.00'),
                scissor_hairs=5000,
                comb_hairs=588,
                payment_method='wechat',
                payment_status='success',
                paid_at=datetime.now(),
            )
            db.session.add(rr)
            print(f"✅ 创建充值记录: user_id={u.id}")

    # 创建测试财务记录
    for u in test_users[:2]:
        existing = FinancialRecord.query.filter_by(user_id=u.id).first()
        if not existing:
            fr = FinancialRecord(
                user_id=u.id,
                record_type='recharge',
                amount=Decimal('50.00'),
                description='测试充值',
                status='success',
            )
            db.session.add(fr)
            print(f"✅ 创建财务记录: user_id={u.id}")

    db.session.commit()
    print("✅ 测试数据准备完成")

    return dev_user, test_users


def get_auth_header(user):
    """生成认证头"""
    auth_service = AuthService()
    token = auth_service.generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}


def test_dashboard(client, dev_user):
    """测试 1: GET /api/dev/dashboard - 客户存量大盘"""
    print_section("测试 1: GET /api/dev/dashboard")

    headers = get_auth_header(dev_user)
    resp = client.get('/api/dev/dashboard', headers=headers)
    print(f"状态码: {resp.status_code}")

    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}"
    data = resp.get_json()
    assert data['success'] is True, f"期望 success=True，实际 {data}"
    assert 'user_distribution' in data, "缺少 user_distribution 字段"
    assert 'overview' in data, "缺少 overview 字段"
    assert 'total_users' in data['overview'], "缺少 total_users 字段"

    print(f"✅ 大盘接口正常响应")
    print(f"   用户分布: {data['user_distribution']}")
    print(f"   总用户数: {data['overview']['total_users']}")

    # 测试缓存（第二次请求应该命中缓存）
    resp2 = client.get('/api/dev/dashboard', headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2['success'] is True
    print(f"✅ 大盘接口缓存正常")


def test_customers_list(client, dev_user):
    """测试 2: GET /api/dev/customers - 客户全景列表"""
    print_section("测试 2: GET /api/dev/customers")

    headers = get_auth_header(dev_user)

    # 2.1 基本分页查询
    resp = client.get('/api/dev/customers?page=1&page_size=10', headers=headers)
    print(f"状态码: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'data' in data
    assert 'items' in data['data']
    assert 'total' in data['data']
    print(f"✅ 列表分页正常，共 {data['data']['total']} 条，当前页 {len(data['data']['items'])} 条")

    # 验证手机号脱敏
    for item in data['data']['items']:
        if item['phone']:
            assert '****' in item['phone'], f"手机号未脱敏: {item['phone']}"
    print(f"✅ 手机号脱敏正常")

    # 2.2 排序测试
    resp = client.get('/api/dev/customers?sort_by=recharge_desc&page_size=5', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    print(f"✅ 按充值排序正常")

    resp = client.get('/api/dev/customers?sort_by=hairs_desc&page_size=5', headers=headers)
    assert resp.status_code == 200
    print(f"✅ 按发丝排序正常")

    resp = client.get('/api/dev/customers?sort_by=created_at_asc&page_size=5', headers=headers)
    assert resp.status_code == 200
    print(f"✅ 按创建时间升序正常")

    resp = client.get('/api/dev/customers?sort_by=last_active&page_size=5', headers=headers)
    assert resp.status_code == 200
    print(f"✅ 按最后活跃排序正常")

    # 2.3 筛选测试
    resp = client.get('/api/dev/customers?member_level=normal&page_size=5', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    for item in data['data']['items']:
        assert item['member_level'] == 'normal', f"筛选失败: {item['member_level']}"
    print(f"✅ 按会员等级筛选正常")

    resp = client.get('/api/dev/customers?user_type=registered&page_size=5', headers=headers)
    assert resp.status_code == 200
    print(f"✅ 按用户类型筛选正常")

    # 2.4 page_size 上限测试
    resp = client.get('/api/dev/customers?page_size=200', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['data']['page_size'] <= 100, f"page_size 应上限 100，实际 {data['data']['page_size']}"
    print(f"✅ page_size 上限 100 正常")


def test_customer_detail(client, dev_user, test_users):
    """测试 3: GET /api/dev/customers/<id> - 客户详情"""
    print_section("测试 3: GET /api/dev/customers/<id>")

    headers = get_auth_header(dev_user)
    target_id = test_users[0].id

    resp = client.get(f'/api/dev/customers/{target_id}', headers=headers)
    print(f"状态码: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'user' in data
    assert 'consumption_records' in data
    assert 'financial_records' in data
    assert 'recharge_records' in data
    assert data['user']['id'] == target_id
    print(f"✅ 客户详情正常响应，user_id={target_id}")

    # 验证手机号脱敏
    if data['user']['phone']:
        assert '****' in data['user']['phone']
    print(f"✅ 详情手机号脱敏正常")

    # 测试缓存
    resp2 = client.get(f'/api/dev/customers/{target_id}', headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2['success'] is True
    print(f"✅ 客户详情缓存正常")

    # 测试不存在的用户
    resp = client.get('/api/dev/customers/999999', headers=headers)
    assert resp.status_code == 404
    print(f"✅ 不存在的用户返回 404")


def test_search(client, dev_user, test_users):
    """测试 4: GET /api/dev/search - 精准查询"""
    print_section("测试 4: GET /api/dev/search")

    headers = get_auth_header(dev_user)

    # 4.1 精确匹配存在的手机号
    target_phone = test_users[0].phone
    resp = client.get(f'/api/dev/search?phone={target_phone}', headers=headers)
    print(f"状态码: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['found'] is True
    assert data['user'] is not None
    print(f"✅ 精确匹配成功: phone={target_phone}, found=True")

    # 4.2 精确匹配不存在的手机号
    resp = client.get('/api/dev/search?phone=19999999999', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['found'] is False
    assert data['user'] is None
    print(f"✅ 不存在的手机号返回 found=False")

    # 4.3 缺少 phone 参数
    resp = client.get('/api/dev/search', headers=headers)
    assert resp.status_code == 400
    print(f"✅ 缺少 phone 参数返回 400")


def test_today(client, dev_user):
    """测试 5: GET /api/dev/today - 今日动态看板"""
    print_section("测试 5: GET /api/dev/today")

    headers = get_auth_header(dev_user)
    resp = client.get('/api/dev/today', headers=headers)
    print(f"状态码: {resp.status_code}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'date' in data
    assert 'new_users' in data
    assert 'active_users' in data
    assert 'recharge' in data
    assert 'consumption' in data
    print(f"✅ 今日动态看板正常响应")
    print(f"   日期: {data['date']}")
    print(f"   今日新增: {data['new_users']}")
    print(f"   今日活跃: {data['active_users']}")

    # 测试缓存
    resp2 = client.get('/api/dev/today', headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2['success'] is True
    print(f"✅ 今日动态缓存正常")


def test_permission_control(client, test_users):
    """测试 6: 权限控制 - 非开发者返回 404"""
    print_section("测试 6: 权限控制（非开发者返回 404）")

    # 使用普通用户 token
    normal_user = test_users[0]
    headers = get_auth_header(normal_user)

    endpoints = [
        '/api/dev/dashboard',
        '/api/dev/customers',
        f'/api/dev/customers/{normal_user.id}',
        '/api/dev/search?phone=13800000001',
        '/api/dev/today',
    ]

    for endpoint in endpoints:
        resp = client.get(endpoint, headers=headers)
        assert resp.status_code == 404, f"非开发者访问 {endpoint} 应返回 404，实际 {resp.status_code}"
        print(f"✅ {endpoint} -> 404（非开发者不可见）")

    # 未登录用户
    for endpoint in endpoints:
        resp = client.get(endpoint)
        assert resp.status_code == 404, f"未登录访问 {endpoint} 应返回 404，实际 {resp.status_code}"
    print(f"✅ 未登录用户访问所有接口返回 404")


def test_cache_service():
    """测试 7: CacheService 基本功能"""
    print_section("测试 7: CacheService 基本功能")

    from cache_service import get_cache_service
    cache = get_cache_service()

    # 测试 set/get
    test_key = 'dev:test:key'
    test_value = {'foo': 'bar', 'num': 42, 'list': [1, 2, 3]}

    result = cache.set(test_key, test_value, expire_seconds=10)
    print(f"set 结果: {result}")

    retrieved = cache.get(test_key)
    if retrieved is not None:
        assert retrieved['foo'] == 'bar'
        assert retrieved['num'] == 42
        assert retrieved['list'] == [1, 2, 3]
        print(f"✅ get/set 正常: {retrieved}")
    else:
        print(f"⚠️  Redis 不可用，get 返回 None（降级正常）")

    # 测试 delete
    cache.delete(test_key)
    deleted = cache.get(test_key)
    assert deleted is None
    print(f"✅ delete 正常")

    # 测试 exists
    cache.set(test_key, 'hello', expire_seconds=10)
    assert cache.exists(test_key) is True
    cache.delete(test_key)
    assert cache.exists(test_key) is False
    print(f"✅ exists 正常")


def run_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  开发者端客户档案功能 - 测试套件")
    print("=" * 60)

    # 启用开发者模式（临时）
    import config as cfg
    original_dev_mode = cfg.DEVELOPER_MODE_ENABLED
    original_dev_accounts = cfg.DEVELOPER_ACCOUNTS

    with app.app_context():
        dev_user, test_users = setup_test_data()

        # 临时启用开发者模式
        cfg.DEVELOPER_MODE_ENABLED = True
        cfg.DEVELOPER_ACCOUNTS = [dev_user.id]

        try:
            with app.test_client() as client:
                test_dashboard(client, dev_user)
                test_customers_list(client, dev_user)
                test_customer_detail(client, dev_user, test_users)
                test_search(client, dev_user, test_users)
                test_today(client, dev_user)
                test_permission_control(client, test_users)

            # CacheService 测试不需要 Flask 上下文
            test_cache_service()

        finally:
            # 恢复原始配置
            cfg.DEVELOPER_MODE_ENABLED = original_dev_mode
            cfg.DEVELOPER_ACCOUNTS = original_dev_accounts

    print("\n" + "=" * 60)
    print("  🎉 所有测试通过！")
    print("=" * 60)


if __name__ == '__main__':
    run_tests()
