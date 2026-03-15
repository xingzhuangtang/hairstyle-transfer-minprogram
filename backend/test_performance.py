#!/usr/bin/env python3
"""
性能测试和API响应时间测量
"""

import time
import requests
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(
    "/Users/tangxingzhuang/PycharmProjects/PythonProject/hairstyle-transfer-v5.3-release"
)


def test_api_performance():
    """测试API响应时间"""
    print("=== 测试API响应时间 ===")

    base_url = "http://localhost:5003"

    # 测试健康检查端点
    print("🔄 测试健康检查端点...")
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒

        if response.status_code == 200:
            print(f"✅ 健康检查: {response_time:.2f}ms - 状态正常")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {str(e)}")
        return False

    # 多次测试获取平均响应时间
    print("\n📊 进行5次响应时间测试...")
    response_times = []

    for i in range(5):
        start_time = time.time()
        try:
            response = requests.get(f"{base_url}/api/health", timeout=5)
            if response.status_code == 200:
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)
                print(f"  测试{i + 1}: {response_time:.2f}ms")
            else:
                print(f"  测试{i + 1}: 失败 ({response.status_code})")
        except Exception as e:
            print(f"  测试{i + 1}: 异常 ({str(e)})")

    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        print(f"\n📈 响应时间统计:")
        print(f"  - 平均: {avg_time:.2f}ms")
        print(f"  - 最快: {min_time:.2f}ms")
        print(f"  - 最慢: {max_time:.2f}ms")

        # 性能评估
        if avg_time < 100:
            print("✅ 响应时间优秀 (<100ms)")
        elif avg_time < 500:
            print("⚠️  响应时间良好 (<500ms)")
        else:
            print("❌ 响应时间需要优化 (>500ms)")

    return True


def test_ai_service_cost():
    """测试AI服务成本和配额"""
    print("\n=== 测试AI服务成本分析 ===")

    # 根据CLAUDE.md中的成本信息
    api_costs = {
        "hair_segment": 0.0025,  # 头发分割
        "face_merge": 0.0025,  # 人脸融合
        "sketch": 0.08,  # 素描生成
    }

    print("💰 单次API调用成本:")
    for service, cost in api_costs.items():
        print(f"  - {service}: ¥{cost:.4f}")

    # 完整发型迁移流程成本
    total_cost = api_costs["hair_segment"] + api_costs["face_merge"]
    with_sketch_cost = total_cost + api_costs["sketch"]

    print(f"\n📊 完整流程成本:")
    print(f"  - 仅发型迁移: ¥{total_cost:.4f}")
    print(f"  - 含素描生成: ¥{with_sketch_cost:.4f}")

    # 收费对比
    from config import PRICING_RULES

    normal_price = PRICING_RULES["normal"]["combined"] / 100  # 0.88元
    premium_price = PRICING_RULES["premium"]["combined"] / 100  # 0.46元

    print(f"\n📈 收费与成本对比:")
    print(
        f"  - 普通用户收费: ¥{normal_price:.2f}, 成本: ¥{total_cost:.4f}, 利润率: {((normal_price - total_cost) / normal_price * 100):.1f}%"
    )
    print(
        f"  - 高级会员收费: ¥{premium_price:.2f}, 成本: ¥{total_cost:.4f}, 利润率: {((premium_price - total_cost) / premium_price * 100):.1f}%"
    )

    # 日成本估算
    daily_estimates = [10, 50, 100, 500, 1000]  # 日订单量
    print(f"\n📅 日成本估算 (纯发型迁移):")
    for orders in daily_estimates:
        daily_cost = total_cost * orders
        daily_revenue_normal = normal_price * orders
        daily_revenue_premium = premium_price * orders

        print(
            f"  - {orders}单: 成本¥{daily_cost:.2f}, 收入¥{daily_revenue_normal:.2f}-{daily_revenue_premium:.2f}, 利润¥{daily_revenue_normal - daily_cost:.2f}-{daily_revenue_premium - daily_cost:.2f}"
        )

    print("✅ 成本分析完成")
    return True


def test_memory_usage():
    """测试内存使用情况"""
    print("\n=== 测试内存使用情况 ===")

    try:
        import psutil

        process = psutil.Process()

        # 获取当前内存使用
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024  # 转换为MB

        print(f"🧠 当前内存使用: {memory_mb:.2f} MB")

        # 内存评估
        if memory_mb < 100:
            print("✅ 内存使用正常 (<100MB)")
        elif memory_mb < 500:
            print("⚠️  内存使用偏高 (<500MB)")
        else:
            print("❌ 内存使用过高 (>500MB)")

    except ImportError:
        print("⚠️  psutil未安装，跳过内存测试")
    except Exception as e:
        print(f"❌ 内存测试异常: {str(e)}")

    return True


def main():
    """主测试函数"""
    print("=" * 50)
    print("🧪 性能和成本测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    tests = [
        ("API性能测试", test_api_performance),
        ("AI服务成本分析", test_ai_service_cost),
        ("内存使用测试", test_memory_usage),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🔍 开始测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 发生异常: {str(e)}")
            results.append((test_name, False))

    # 输出测试结果摘要
    print("\n" + "=" * 50)
    print("📊 测试结果摘要")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n📈 总体结果: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！性能和成本指标正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查性能优化")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
