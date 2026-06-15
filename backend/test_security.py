#!/usr/bin/env python3
"""
发型迁移系统安全测试脚本
"""

from app import app, db
from models import User, RechargeRecord, MemberOrder, ConsumptionRecord, FinancialRecord
import re
import os

print('='*60)
print('安全测试报告：发型迁移系统 v5.3')
print('='*60)

with app.app_context():
    issues = []
    
    # ===== 安全测试 1: API 权限检查 =====
    print()
    print('[安全测试 1] 接口权限检查')
    print('-'*40)
    
    with open('api.py', 'r') as f:
        api_content = f.read()
    
    unprotected_routes = []
    lines = api_content.split('\n')
    for i, line in enumerate(lines):
        if '@api_bp.route' in line:
            context = '\n'.join(lines[max(0,i-3):i+3])
            if '@login_required' not in context and '@optional_login' not in context:
                route_match = re.search(r"'([^']+)'", line)
                if route_match:
                    r = route_match.group(1)
                    if not any(kw in r for kw in ['callback', 'login', 'send-code', 'health', 'refund/approve', 'chat/reply', 'referral/track', 'rules']):
                        unprotected_routes.append(r)
    
    if unprotected_routes:
        print(f'WARNING: 发现 {len(unprotected_routes)} 个无认证保护的路由:')
        for r in unprotected_routes[:10]:
            print(f'   - {r}')
        issues.append(('中风险', '部分API路由缺少认证保护', f'{len(unprotected_routes)}个'))
    else:
        print('PASS: 所有关键路由都有认证保护')
    
    # ===== 安全测试 2: SQL注入防护 =====
    print()
    print('[安全测试 2] SQL注入防护检查')
    print('-'*40)
    
    f_string_sql = len(re.findall(r'db\.session\.execute\(f"', api_content))
    if f_string_sql > 0:
        print(f'FAIL: 发现 {f_string_sql} 处 f-string 拼接SQL')
        issues.append(('高风险', 'f-string 拼接SQL', f'{f_string_sql}处'))
    else:
        print('PASS: 未发现 f-string 拼接SQL')
    
    # ===== 安全测试 3: 敏感信息 =====
    print()
    print('[安全测试 3] 敏感信息泄露检查')
    print('-'*40)
    
    log_found_sensitive = False
    for log_file in ['logs/app.log', 'logs/error.log', 'logs/access.log']:
        if os.path.exists(log_file):
            with open(log_file, 'r', errors='ignore') as f:
                log_sample = f.read()[:50000]
            sensitive_words = ['WECHAT_APP_SECRET=', 'MYSQL_PASSWORD=', 'JWT_SECRET=', 'ALIBABA_CLOUD_ACCESS_KEY_SECRET=']
            for word in sensitive_words:
                if word in log_sample:
                    print(f'FAIL: {log_file} 包含敏感信息: {word}')
                    issues.append(('高风险', '日志记录敏感信息', log_file))
                    log_found_sensitive = True
                    break
    if not log_found_sensitive:
        print('PASS: 日志文件未发现明显敏感信息')
    
    # ===== 安全测试 4: JWT 安全性 =====
    print()
    print('[安全测试 4] JWT 安全性检查')
    print('-'*40)
    
    with open('config.py', 'r') as f:
        config_content = f.read()
    
    if 'hairstyle-transfer-secret-key-2024-dev' in config_content:
        print('FAIL: JWT_SECRET_KEY 使用默认开发密钥')
        issues.append(('高风险', 'JWT_SECRET_KEY 使用默认值', 'config.py'))
    else:
        print('PASS: JWT_SECRET_KEY 已配置')
    
    jwt_expire = re.search(r'JWT_ACCESS_TOKEN_EXPIRES\s*=\s*(\d+)', config_content)
    if jwt_expire:
        expire_days = int(jwt_expire.group(1)) / (24*60*60)
        print(f'INFO: JWT 过期时间: {expire_days} 天')
    
    # ===== 安全测试 5: 支付安全 =====
    print()
    print('[安全测试 5] 支付安全检查')
    print('-'*40)
    
    with open('payment_service.py', 'r') as f:
        pay_content = f.read()
    
    if 'verify_callback' in pay_content:
        print('PASS: 支付回调验证机制存在')
    else:
        print('FAIL: 支付回调验证机制缺失')
        issues.append(('高风险', '支付回调验证缺失', 'payment_service.py'))
    
    if 'verify_refund_callback' in pay_content:
        print('PASS: 退款回调验证机制存在')
    else:
        print('WARNING: 退款回调验证机制待确认')
        issues.append(('中风险', '退款回调验证待确认', 'payment_service.py'))
    
    # ===== 安全测试 6: 文件上传安全 =====
    print()
    print('[安全测试 6] 文件上传安全检查')
    print('-'*40)
    
    if 'ALLOWED_EXTENSIONS' in config_content:
        ext = re.search(r'ALLOWED_EXTENSIONS\s*=\s*\{([^}]+)\}', config_content)
        if ext:
            print(f'PASS: 文件扩展名限制: {ext.group(1)}')
    
    if 'MAX_CONTENT_LENGTH' in config_content:
        max_len = re.search(r'MAX_CONTENT_LENGTH\s*=\s*(\d+)', config_content)
        if max_len:
            mb = int(max_len.group(1)) / (1024*1024)
            print(f'PASS: 文件大小限制: {mb}MB')
    
    # ===== 安全测试 7: 错误信息泄露 =====
    print()
    print('[安全测试 7] 错误信息泄露检查')
    print('-'*40)
    
    error_handler_count = api_content.count('@api_bp.errorhandler')
    if error_handler_count > 0:
        print(f'PASS: 发现 {error_handler_count} 个错误处理器')
    else:
        print('WARNING: 未发现自定义错误处理器')
        issues.append(('低风险', '缺少全局错误处理器', '可能暴露技术细节'))
    
    # ===== 安全测试 8: 环境配置 =====
    print()
    print('[安全测试 8] 环境配置检查')
    print('-'*40)
    
    debug_mode = 'DEBUG=True' in config_content or 'DEBUG = True' in config_content or "DEBUG, 'true'" in config_content
    if debug_mode:
        print('WARNING: DEBUG 模式在生产环境可能开启')
        issues.append(('中风险', 'DEBUG 模式可能开启', 'config.py'))
    else:
        print('PASS: DEBUG 模式未硬编码为 True')
    
    # 检查 .env.example 是否存在
    if os.path.exists('.env.example'):
        print('PASS: .env.example 文件存在（良好的配置管理）')
    
    # ===== 安全测试 9: 聊天内容安全 =====
    print()
    print('[安全测试 9] 聊天内容安全检查')
    print('-'*40)
    
    with open('chat_service.py', 'r') as f:
        chat_content = f.read()
    
    if 'sanitize_content' in chat_content or 'bleach' in chat_content or 're.sub' in chat_content:
        print('PASS: 聊天内容有 XSS 防护')
    else:
        print('FAIL: 聊天内容缺少 XSS 防护')
        issues.append(('高风险', '聊天内容 XSS 防护缺失', 'chat_service.py'))
    
    if 'check_send_limit' in chat_content or '_send_limits' in chat_content:
        print('PASS: 聊天有频率限制')
    else:
        print('FAIL: 聊天缺少频率限制')
        issues.append(('中风险', '聊天缺少频率限制', 'chat_service.py'))
    
    # ===== 安全测试 10: HMAC Token 安全 =====
    print()
    print('[安全测试 10] Token 安全性检查')
    print('-'*40)
    
    if 'hmac' in chat_content:
        print('PASS: 聊天回复使用 HMAC 签名')
    
    with open('refund_service.py', 'r') as f:
        refund_content = f.read()
    if 'hmac' in refund_content:
        print('PASS: 退款审批使用 HMAC 签名')
    
    if 'time.time()' in chat_content or 'expire' in chat_content:
        print('PASS: Token 有过期机制')
    
    # ===== 汇总 =====
    print()
    print('='*60)
    print('安全风险汇总')
    print('='*60)
    
    if issues:
        high = [i for i in issues if i[0] == '高风险']
        medium = [i for i in issues if i[0] == '中风险']
        low = [i for i in issues if i[0] == '低风险']
        
        print(f'FAIL 高风险: {len(high)} 个')
        for i in high:
            print(f'   - {i[1]}: {i[2]}')
        print(f'WARN 中风险: {len(medium)} 个')
        for i in medium:
            print(f'   - {i[1]}: {i[2]}')
        print(f'INFO 低风险: {len(low)} 个')
        for i in low:
            print(f'   - {i[1]}: {i[2]}')
    else:
        print('PASS: 未发现安全问题')
    
    print(f'\n总计: {len(issues)} 个安全问题')
