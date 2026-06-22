#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收费规则完整测试脚本
覆盖所有服务类型 × 用户等级的组合
"""
import os
os.environ['FLASK_ENV'] = 'production'

from dotenv import load_dotenv
load_dotenv()
from app import app
from models import User
from hair_service import HairService

# 预期收费表
EXPECTED_NORMAL = {
    "hair_segment": 4,
    "extract_hair_only": 4,
    "face_merge": 4,
    "migrate_hair_only": 4,
    "sketch": 84,
    "sketch_only": 84,
    "combined": 88,
    "face_merge_step": 4,
    "step1_migrate": 4,
    "sketch_step": 88,
    "step2_sketch": 88,
}

EXPECTED_VIP = {
    "hair_segment": 2,
    "extract_hair_only": 2,
    "face_merge": 2,
    "migrate_hair_only": 2,
    "sketch": 42,
    "sketch_only": 42,
    "combined": 46,
    "face_merge_step": 2,
    "step1_migrate": 2,
    "sketch_step": 44,
    "step2_sketch": 44,
}

def test_pricing():
    with app.app_context():
        hair_service = HairService()

        # 获取测试用户
        normal_user = User.query.filter_by(phone="17731005216").first()
        vip_user = User.query.filter_by(phone="18911523837").first()

        if not normal_user or not vip_user:
            print("ERROR: 测试用户不存在")
            return

        all_passed = True
        results = []

        print("=" * 80)
        print("收费规则测试")
        print("=" * 80)

        # 测试普通用户
        print(f"\n【普通用户】ID={normal_user.id}, phone={normal_user.phone}, level={normal_user.member_level}")
        print("-" * 60)

        for service_type, expected in EXPECTED_NORMAL.items():
            actual = hair_service.calculate_cost(normal_user, service_type)
            status = "PASS" if actual == expected else "FAIL"
            if status == "FAIL":
                all_passed = False
            results.append({
                "user": "normal",
                "service_type": service_type,
                "expected": expected,
                "actual": actual,
                "status": status
            })
            print(f"  {status:4s} | {service_type:20s} | 预期={expected:3d} | 实际={actual:3d}")

        # 测试 VIP 用户
        print(f"\n【VIP 用户】ID={vip_user.id}, phone={vip_user.phone}, level={vip_user.member_level}")
        print("-" * 60)

        for service_type, expected in EXPECTED_VIP.items():
            actual = hair_service.calculate_cost(vip_user, service_type)
            status = "PASS" if actual == expected else "FAIL"
            if status == "FAIL":
                all_passed = False
            results.append({
                "user": "vip",
                "service_type": service_type,
                "expected": expected,
                "actual": actual,
                "status": status
            })
            print(f"  {status:4s} | {service_type:20s} | 预期={expected:3d} | 实际={actual:3d}")

        # 汇总
        print("\n" + "=" * 80)
        failed = [r for r in results if r["status"] == "FAIL"]
        passed = [r for r in results if r["status"] == "PASS"]

        print(f"总计: {len(results)} 项 | 通过: {len(passed)} | 失败: {len(failed)}")

        if failed:
            print("\n失败详情:")
            for r in failed:
                print(f"  ❌ [{r['user']}] {r['service_type']}: 预期={r['expected']}, 实际={r['actual']}")
        else:
            print("\n✅ 所有收费规则测试通过！")

        print("=" * 80)

        return all_passed

if __name__ == "__main__":
    success = test_pricing()
    exit(0 if success else 1)
