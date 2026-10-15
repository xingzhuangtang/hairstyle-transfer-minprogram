#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全清理重复账号脚本
- 不直接删除，而是标记为重复
- 保留完整数据用于回滚
- 生成详细报告
"""

import sys
from datetime import datetime
from app import app, db
from models import User, HistoryRecord, ConsumptionRecord, RechargeRecord, MemberOrder, FinancialRecord

def find_duplicates():
    """查找重复账号"""
    duplicates = []
    
    with app.app_context():
        # 按手机号分组查找重复
        users_by_phone = {}
        all_users = User.query.all()
        
        for user in all_users:
            if user.phone:
                if user.phone not in users_by_phone:
                    users_by_phone[user.phone] = []
                users_by_phone[user.phone].append(user)
        
        # 找出有重复的手机号
        for phone, users in users_by_phone.items():
            if len(users) > 1:
                # 按创建时间排序，保留最早的
                users.sort(key=lambda u: u.created_at if u.created_at else datetime.min)
                duplicates.append({
                    'phone': phone,
                    'keep': users[0],  # 保留最早的
                    'remove': users[1:]  # 标记其余的
                })
        
        # 按 openid 分组查找重复（同一微信账号多次注册）
        users_by_openid = {}
        for user in all_users:
            if user.openid:
                if user.openid not in users_by_openid:
                    users_by_openid[user.openid] = []
                users_by_openid[user.openid].append(user)
        
        for openid, users in users_by_openid.items():
            if len(users) > 1:
                users.sort(key=lambda u: u.created_at if u.created_at else datetime.min)
                # 检查是否已经按手机号处理过
                already_processed = any(
                    any(u.id == dup['keep'].id or u.id in [r.id for r in dup['remove']] 
                        for u in users)
                    for dup in duplicates
                )
                if not already_processed:
                    duplicates.append({
                        'openid': openid,
                        'keep': users[0],
                        'remove': users[1:]
                    })
    
    return duplicates

def mark_duplicates(duplicates, dry_run=True):
    """标记重复账号（不删除）"""
    report = []
    
    with app.app_context():
        for dup in duplicates:
            keep_user = dup['keep']
            remove_users = dup['remove']
            identifier = dup.get('phone') or dup.get('openid', 'unknown')
            
            report.append(f"\n{'='*60}")
            report.append(f"重复账号组：{identifier}")
            report.append(f"{'='*60}")
            report.append(f"保留账号：ID={keep_user.id}, 昵称={keep_user.nickname}, 创建时间={keep_user.created_at}")
            report.append(f"  - 剪刀发丝：{keep_user.scissor_hairs}, 梳子发丝：{keep_user.comb_hairs}")
            report.append(f"  - 会员等级：{keep_user.member_level}")
            
            for user in remove_users:
                report.append(f"\n标记为重复：ID={user.id}, 昵称={user.nickname}, 创建时间={user.created_at}")
                report.append(f"  - 剪刀发丝：{user.scissor_hairs}, 梳子发丝：{user.comb_hairs}")
                report.append(f"  - 会员等级：{user.member_level}")
                
                if not dry_run:
                    # 标记为重复账号（修改昵称为特殊前缀）
                    user.nickname = f"[重复-{keep_user.id}]{user.nickname or '微信用户'}"
                    user.user_type = 'duplicate'
                    user.is_active = False  # 停用账号
                    
                    # 记录操作日志
                    print(f"标记账号 ID={user.id} 为重复，保留账号 ID={keep_user.id}")
        
        if not dry_run:
            db.session.commit()
            report.append("\n✅ 已提交数据库更改")
        else:
            report.append("\n⚠️  这是预览模式（dry_run=True），未实际修改数据库")
    
    return '\n'.join(report)

def rollback_from_backup():
    """从备份回滚（如果需要）"""
    print("如需回滚，请执行以下命令：")
    print("1. 找到备份文件：ls -lt /tmp/hairstyle_transfer_backup_*.sql | head -1")
    print("2. 恢复数据库：mysql -u root -p hairstyle_transfer < /tmp/hairstyle_transfer_backup_YYYYMMDD_HHMMSS.sql")

if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    
    print("="*60)
    print("安全清理重复账号脚本")
    print("="*60)
    
    if dry_run:
        print("\n⚠️  预览模式：仅显示将要执行的更改，不实际修改数据库")
        print("如需实际执行，请添加 --execute 参数\n")
    else:
        print("\n⚠️  执行模式：将实际修改数据库")
        print("确保已备份数据库！\n")
    
    # 查找重复账号
    print("正在查找重复账号...")
    duplicates = find_duplicates()
    
    if not duplicates:
        print("✅ 未发现重复账号")
        sys.exit(0)
    
    print(f"发现 {len(duplicates)} 组重复账号\n")
    
    # 标记重复账号
    report = mark_duplicates(duplicates, dry_run=dry_run)
    print(report)
    
    # 生成报告文件
    report_file = f"/tmp/duplicate_accounts_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n 详细报告已保存到：{report_file}")
    
    # 回滚说明
    if not dry_run:
        print("\n" + "="*60)
        print("回滚说明")
        print("="*60)
        rollback_from_backup()
