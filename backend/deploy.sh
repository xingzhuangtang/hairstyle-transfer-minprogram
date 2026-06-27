#!/bin/bash
# ============================================
# 发型迁移系统 - 一键部署脚本
# ============================================
# 用法: ./deploy.sh [server_ip] [deploy_path]
# 示例: ./deploy.sh 139.196.105.33 /opt/hairstyle-transfer-v5.3-release
# ============================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SERVER_IP="${1:-139.196.105.33}"
DEPLOY_PATH="${2:-/opt/hairstyle-transfer-v5.3-release}"
FORCE_MODE="${3:-}"
SSH_USER="root"
SSH_PASS="${SSH_PASS:-}"  # 从环境变量读取，不硬编码
BACKEND_PORT=5003
DOMAIN="xn--gmq63iba0780e.com"

# 检查密码是否设置
if [[ -z "$SSH_PASS" ]]; then
    echo "错误: 未设置 SSH_PASS 环境变量"
    echo "用法: export SSH_PASS='your_password' && ./deploy.sh"
    echo "   或: SSH_PASS='your_password' ./deploy.sh"
    exit 1
fi

# 本地路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR"
NGINX_CONFIG="$BACKEND_DIR/config/nginx.conf"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  发型迁移系统 - 部署脚本${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "服务器: ${YELLOW}$SSH_USER@$SERVER_IP${NC}"
echo -e "部署路径: ${YELLOW}$DEPLOY_PATH${NC}"
echo ""

# ============================================
# 工具函数
# ============================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "$@"
}

remote_scp() {
    sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no "$@"
}

# ============================================
# 前置检查
# ============================================

check_prerequisites() {
    log_info "检查前置条件..."

    # 检查 sshpass
    if ! command -v sshpass &> /dev/null; then
        log_error "未安装 sshpass，请先安装: brew install sshpass"
        exit 1
    fi

    # 检查 git
    if ! command -v git &> /dev/null; then
        log_error "未安装 git"
        exit 1
    fi

    # 检查本地是否有未提交的更改
    GIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    if [[ -n $(cd "$GIT_ROOT" && git status --porcelain 2>/dev/null) ]]; then
        log_warn "检测到未提交的更改，建议先提交后再部署"
        log_warn "使用 --force 参数跳过此检查"
        if [[ "$FORCE_MODE" != "--force" ]]; then
            log_info "部署已取消"
            exit 1
        fi
    fi

    # 测试服务器连接
    log_info "测试服务器连接..."
    if ! remote_exec "echo '连接成功'" &> /dev/null; then
        log_error "无法连接到服务器 $SERVER_IP"
        exit 1
    fi

    log_info "前置检查通过"
    echo ""
}

# ============================================
# 部署路径校验（防止文件同步到错误位置）
# ============================================

verify_deploy_paths() {
    log_info "校验部署路径..."

    # 检查服务器上是否存在多份代码副本
    ROOT_APP="$DEPLOY_PATH/app.py"
    BACKEND_APP="$DEPLOY_PATH/backend/app.py"

    ROOT_EXISTS=$(remote_exec "test -f $ROOT_APP && echo yes || echo no" 2>/dev/null | tr -d '[:space:]')
    BACKEND_EXISTS=$(remote_exec "test -f $BACKEND_APP && echo yes || echo no" 2>/dev/null | tr -d '[:space:]')

    if [[ "$ROOT_EXISTS" == "yes" && "$BACKEND_EXISTS" == "yes" ]]; then
        log_warn "⚠️  检测到服务器上存在两份代码副本:"
        log_warn "   - $ROOT_APP"
        log_warn "   - $BACKEND_APP"
        log_warn "  这可能导致部署更新未生效！"

        # 检查实际运行的进程路径
        RUNNING_PATH=$(remote_exec "ps aux | grep 'python.*app.py' | grep -v grep | awk '{print \$NF}' | head -1" 2>/dev/null | tr -d '[:space:]')

        if [[ -n "$RUNNING_PATH" ]]; then
            log_info "  当前运行路径: $RUNNING_PATH"

            if [[ "$RUNNING_PATH" == *"/backend/app.py" ]]; then
                log_error "❌ 进程从 backend/ 子目录运行，但 deploy.sh 同步到根目录！"
                log_error "  修复方案: 在服务器上执行以下命令统一路径:"
                log_error "    cd $DEPLOY_PATH && kill \$(lsof -ti:$BACKEND_PORT) && nohup python3 app.py &"
                if [[ "$FORCE_MODE" != "--force" ]]; then
                    log_info "  使用 --force 参数跳过此检查"
                    exit 1
                fi
            else
                log_info "  ✅ 运行路径与部署路径一致"
            fi
        fi
    elif [[ "$ROOT_EXISTS" == "yes" ]]; then
        log_info "  ✅ 仅存在根目录副本，路径正确"
    elif [[ "$BACKEND_EXISTS" == "yes" ]]; then
        log_warn "  ⚠️  仅存在 backend/ 子目录副本，deploy.sh 将同步到根目录"
        log_info "  建议统一使用根目录部署"
    else
        log_info "  服务器上未找到 app.py（首次部署）"
    fi

    echo ""
}

# ============================================
# 同步代码到服务器
# ============================================

sync_code() {
    log_info "同步代码到服务器..."

    # 需要同步的核心文件
    CORE_FILES=(
        # --- 入口 & 路由 ---
        "app.py"
        "api.py"
        # --- 顶层硬导入（缺失则启动崩溃）---
        "logging_config.py"
        "monitoring_config.py"
        "member_service.py"
        "account_service.py"
        # --- 核心业务 ---
        "auth.py"
        "config.py"
        "models.py"
        "payment_service.py"
        "hair_service.py"
        "wechat_pay.py"
        "sms_service.py"
        "referral_service.py"
        "chat_service.py"
        "chat_notifier.py"
        "financial_service.py"
        # --- 延迟导入（缺失则特定功能不可用）---
        "virtual_payment_service.py"
        "refund_service.py"
        "refund_notifier.py"
        "cache_service.py"
        # --- AI / 图像处理 ---
        "bailian_sketch_converter.py"
        "aliyun_hair_transfer_fixed.py"
        "hair_segmentation.py"
        "image_preprocessor.py"
        "sketch_converter.py"
        # --- 运维 / 调度 ---
        "scheduler.py"
        "fix_financial_records.py"
        # --- 数据库检查 / 监控 ---
        "check_db_schema.py"
        "fix_db_schema.py"
        "monitor_financial.py"
        "manual_fix_recharge.py"
        "migrate_dev_indexes.py"
        "migrate_self_healing_tables.py"
        "migrate_bug_knowledge.py"
    )

    for file in "${CORE_FILES[@]}"; do
        if [[ -f "$BACKEND_DIR/$file" ]]; then
            remote_scp "$BACKEND_DIR/$file" "$SSH_USER@$SERVER_IP:$DEPLOY_PATH/"
            log_info "  已同步: $file"
        else
            log_warn "  本地不存在: $file (跳过)"
        fi
    done

    # 同步 self_healing 目录
    if [[ -d "$BACKEND_DIR/self_healing" ]]; then
        remote_exec "mkdir -p $DEPLOY_PATH/self_healing"
        remote_scp -r "$BACKEND_DIR"/self_healing/* "$SSH_USER@$SERVER_IP:$DEPLOY_PATH/self_healing/"
        log_info "  已同步: self_healing/"
    fi

    # 注意: 不同步 .env，避免覆盖远程服务器的重要配置
    # 如需更新远程 .env，请手动执行:
    #   scp backend/.env root@SERVER:$DEPLOY_PATH/.env
    # if [[ -f "$BACKEND_DIR/.env" ]]; then
    #     remote_scp "$BACKEND_DIR/.env" "$SSH_USER@$SERVER_IP:$DEPLOY_PATH/.env"
    #     log_info "  已同步: .env"
    # fi

    log_info "代码同步完成"
    echo ""
}

# ============================================
# 同步 Nginx 配置
# ============================================

sync_nginx_config() {
    log_info "检查 Nginx 配置..."

    if [[ -f "$NGINX_CONFIG" ]]; then
        # 备份当前配置
        remote_exec "cp /etc/nginx/conf.d/${DOMAIN}.conf /etc/nginx/conf.d/${DOMAIN}.conf.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"

        # 同步新配置
        remote_scp "$NGINX_CONFIG" "$SSH_USER@$SERVER_IP:/etc/nginx/conf.d/${DOMAIN}.conf"
        log_info "  已同步 Nginx 配置"

        # 验证配置
        if remote_exec "nginx -t" 2>&1 | grep -q "syntax is ok"; then
            log_info "  Nginx 配置验证通过"
        else
            log_error "  Nginx 配置有误，已恢复最新备份"
            remote_exec "LATEST=\$(ls -t /etc/nginx/conf.d/${DOMAIN}.conf.bak.* 2>/dev/null | head -1); [ -n \"\$LATEST\" ] && cp \"\$LATEST\" /etc/nginx/conf.d/${DOMAIN}.conf || true"
            exit 1
        fi
    else
        log_warn "  未找到 Nginx 配置文件 ($NGINX_CONFIG)，跳过"
    fi

    echo ""
}

# ============================================
# 检查服务器 .env 配置完整性
# ============================================

check_env_completeness() {
    log_info "检查服务器配置完整性..."

    # 必需的配置项列表（按功能分组）
    REQUIRED_VARS=(
        # 基础配置
        "MYSQL_HOST"
        "MYSQL_DATABASE"
        # 阿里云配置
        "ALIBABA_CLOUD_ACCESS_KEY_ID"
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET"
        # 企业微信通知
        "WECHAT_CORP_ID"
        "WECHAT_CORP_SECRET"
        "WECHAT_AGENT_ID"
    )

    MISSING_VARS=()

    for var in "${REQUIRED_VARS[@]}"; do
        if ! remote_exec "grep -q '^${var}=' $DEPLOY_PATH/.env 2>/dev/null"; then
            MISSING_VARS+=("$var")
        fi
    done

    if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
        log_warn "发现 ${#MISSING_VARS[@]} 个缺失的配置项:"
        for var in "${MISSING_VARS[@]}"; do
            echo "  - $var"
        done
        echo ""
        log_warn "缺失配置可能导致部分功能不可用"
        log_warn "请手动登录服务器补充配置: ssh $SSH_USER@$SERVER_IP"
        echo ""

        if [[ "$FORCE_MODE" != "--force" ]]; then
            read -p "是否继续部署? (y/N) " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "部署已取消"
                exit 1
            fi
        fi
    else
        log_info "配置完整性检查通过"
    fi

    echo ""
}

# ============================================
# 静态文件夹路径验证和修复
# ============================================

verify_static_paths() {
    log_info "验证静态文件夹路径..."

    # 检查 backend/static 是否存在且是符号链接
    BACKEND_STATIC="$DEPLOY_PATH/backend/static"
    PROJECT_STATIC="$DEPLOY_PATH/static"

    # 如果 backend/static 不存在或是目录（不是符号链接），创建符号链接
    if [[ -L "$BACKEND_STATIC" ]]; then
        # 已是符号链接，检查目标是否正确
        LINK_TARGET=$(readlink -f "$BACKEND_STATIC")
        if [[ "$LINK_TARGET" == "$PROJECT_STATIC" ]]; then
            log_info "  ✅ backend/static 符号链接正确"
        else
            log_warn "  ⚠️  backend/static 符号链接指向错误: $LINK_TARGET"
            log_info "  修复符号链接..."
            remote_exec "rm -rf $BACKEND_STATIC && ln -s $PROJECT_STATIC $BACKEND_STATIC"
        fi
    elif [[ -d "$BACKEND_STATIC" ]]; then
        # 是普通目录，需要迁移数据并创建符号链接
        log_warn "  ⚠️  backend/static 是普通目录，需要迁移数据..."

        # 迁移数据到项目根目录的 static
        remote_exec "mkdir -p $PROJECT_STATIC && cp -rn $BACKEND_STATIC/* $PROJECT_STATIC/ 2>/dev/null || true"

        # 删除原目录并创建符号链接
        remote_exec "rm -rf $BACKEND_STATIC && ln -s $PROJECT_STATIC $BACKEND_STATIC"
        log_info "  ✅ 已迁移数据并创建符号链接"
    else
        # 不存在，直接创建符号链接
        remote_exec "mkdir -p $PROJECT_STATIC && ln -s $PROJECT_STATIC $BACKEND_STATIC"
        log_info "  ✅ 已创建 backend/static 符号链接"
    fi

    # 验证符号链接
    if [[ -L "$BACKEND_STATIC" ]]; then
        LINK_TARGET=$(readlink -f "$BACKEND_STATIC")
        log_info "  ✅ backend/static -> $LINK_TARGET"
    else
        log_error "  ❌ 符号链接创建失败，请手动检查"
    fi

    echo ""
}

# ============================================
# 域名白名单检查（微信小程序）
# ============================================

check_domain_whitelist() {
    log_info "检查域名白名单配置..."

    # 需要检查的域名列表
    DOMAINS_TO_CHECK=()

    # 从 .env 读取 OSS 配置
    if [[ -f "$DEPLOY_PATH/.env" ]]; then
        OSS_ENDPOINT=$(remote_exec "grep '^OSS_ENDPOINT=' $DEPLOY_PATH/.env | cut -d= -f2" 2>/dev/null | tr -d '[:space:]')
        if [[ -n "$OSS_ENDPOINT" ]]; then
            DOMAINS_TO_CHECK+=("$OSS_ENDPOINT")
        fi
    fi

    # 默认 OSS 域名
    if [[ ${#DOMAINS_TO_CHECK[@]} -eq 0 ]]; then
        DOMAINS_TO_CHECK+=("oss-cn-shanghai.aliyuncs.com")
    fi

    WARN_COUNT=0

    for domain in "${DOMAINS_TO_CHECK[@]}"; do
        log_info "  检查域名: $domain"

        # 检查 Nginx 是否有该域名的代理配置
        if remote_exec "grep -q '$domain' $DEPLOY_PATH/config/nginx.conf 2>/dev/null || grep -q '$domain' /etc/nginx/conf.d/*.conf 2>/dev/null"; then
            log_info "    ✅ Nginx 已配置代理"
        else
            log_warn "    ⚠️  Nginx 未配置代理，前端可能无法直接访问"
            log_info "    建议: 在微信小程序后台配置 downloadFile/uploadFile 域名白名单"
            log_info "    或添加 Nginx 代理: location /oss/ { proxy_pass https://$domain/; }"
            WARN_COUNT=$((WARN_COUNT + 1))
        fi
    done

    if [[ $WARN_COUNT -gt 0 ]]; then
        log_warn "发现 $WARN_COUNT 个域名可能需要配置白名单"
        log_info "请参考: https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html"
    else
        log_info "  ✅ 所有域名配置正常"
    fi

    echo ""
}

# ============================================
# 清理缓存并重启服务
# ============================================

restart_services() {
    log_info "清理缓存并重启服务..."

    # 清理 Python 缓存
    remote_exec "cd $DEPLOY_PATH && rm -rf __pycache__ && find . -name '*.pyc' -delete"
    log_info "  已清理 Python 缓存"

    # 重启后端
    remote_exec "cd $DEPLOY_PATH && kill \$(lsof -ti:$BACKEND_PORT) 2>/dev/null || true; sleep 2; nohup python3 app.py > /tmp/backend.log 2>&1 </dev/null &"
    sleep 3

    # 检查后端是否启动成功
    BACKEND_PID=$(remote_exec "lsof -ti:$BACKEND_PORT" 2>/dev/null || echo "")
    if [[ -n "$BACKEND_PID" ]]; then
        log_info "  后端已重启 (PID: $BACKEND_PID)"
    else
        log_error "  后端启动失败，请检查 /tmp/backend.log"
        remote_exec "tail -20 /tmp/backend.log"
        exit 1
    fi

    # 重启 Nginx (如果配置有更新)
    if [[ -f "$NGINX_CONFIG" ]]; then
        remote_exec "nginx -s reload 2>/dev/null || (killall nginx 2>/dev/null; sleep 1; nginx)" && log_info "  Nginx 已重启"
    fi

    log_info "服务重启完成"
    echo ""
}

# ============================================
# 数据库结构检查
# ============================================

check_db_schema() {
    log_info "检查数据库表结构完整性..."

    # 在远程服务器执行检查
    CHECK_RESULT=$(remote_exec "cd $DEPLOY_PATH && python3 -c \"
import sys
from app import app, db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    db_tables = set(inspector.get_table_names())
    model_tables = set(db.metadata.tables.keys())

    missing_tables = model_tables - db_tables
    if missing_tables:
        print(f'MISSING_TABLES:{missing_tables}')
        sys.exit(1)

    missing_cols = {}
    for table in model_tables & db_tables:
        model_cols = {c.name for c in db.metadata.tables[table].columns}
        db_cols = {c['name'] for c in inspector.get_columns(table)}
        diff = model_cols - db_cols
        if diff:
            missing_cols[table] = list(diff)

    if missing_cols:
        print(f'MISSING_COLS:{missing_cols}')
        sys.exit(1)

    print('OK')
\"" 2>&1)

    if echo "$CHECK_RESULT" | grep -q "^OK"; then
        log_info "  ✅ 数据库表结构完整"
    else
        log_error "  ❌ 数据库结构问题: $CHECK_RESULT"
        log_warn "  请在服务器上运行: python3 fix_db_schema.py"
        return 1
    fi

    return 0
}

# ============================================
# 财务流水监控
# ============================================

monitor_financial() {
    log_info "检查财务流水记录完整性..."

    # 在远程服务器执行检查
    remote_exec "cd $DEPLOY_PATH && python3 -c \"
from app import app, db
from models import RechargeRecord, MemberOrder, FinancialRecord
from sqlalchemy import func

with app.app_context():
    success_orders = RechargeRecord.query.filter_by(payment_status='success').count()
    recharge_records = FinancialRecord.query.filter_by(record_type='recharge', status='success').count()
    member_orders = MemberOrder.query.filter_by(payment_status='success').count()
    member_records = FinancialRecord.query.filter_by(record_type='member_purchase', status='success').count()

    print(f'充值订单: {success_orders}, 财务记录: {recharge_records}')
    print(f'会员订单: {member_orders}, 财务记录: {member_records}')

    total_recharge = db.session.query(func.sum(RechargeRecord.amount)).filter(RechargeRecord.payment_status == 'success').scalar() or 0
    print(f'充值总额: ¥{float(total_recharge):.2f}')
\"" 2>&1 || log_warn "财务监控执行失败"

    return 0
}

# ============================================
# 健康检查
# ============================================

health_check() {
    log_info "执行健康检查..."

    PASS=0
    FAIL=0

    # 检查后端健康
    if curl -sf "https://$DOMAIN/api/monitoring/health" > /dev/null 2>&1; then
        log_info "  ✅ 后端健康检查通过"
        PASS=$((PASS + 1))
    else
        log_error "  ❌ 后端健康检查失败"
        FAIL=$((FAIL + 1))
    fi

    # 检查静态文件可访问
    STATIC_TESTS=(
        "/static/results/"
        "/static/uploads/"
    )

    for path in "${STATIC_TESTS[@]}"; do
        code=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN${path}" 2>/dev/null || echo "000")
        # 目录请求可能返回 403 或 404，这不算失败，只要不是连接错误就行
        if [[ "$code" != "000" ]]; then
            log_info "  ✅ 静态文件路径 $path 可访问 (HTTP $code)"
            PASS=$((PASS + 1))
        else
            log_error "  ❌ 静态文件路径 $path 无法访问"
            FAIL=$((FAIL + 1))
        fi
    done

    # 检查数据库连接
    if remote_exec "cd $DEPLOY_PATH && python3 -c 'from models import db; print(db.session.execute(db.text(\"SELECT 1\")).fetchone())' 2>/dev/null" | grep -q "1"; then
        log_info "  ✅ 数据库连接正常"
        PASS=$((PASS + 1))
    else
        log_error "  ❌ 数据库连接失败"
        FAIL=$((FAIL + 1))
    fi

    # 检查 Redis
    if remote_exec "redis-cli ping" 2>/dev/null | grep -q "PONG"; then
        log_info "  ✅ Redis 连接正常"
        PASS=$((PASS + 1))
    else
        log_warn "  ⚠️  Redis 连接失败 (如未使用可忽略)"
    fi

    echo ""
    log_info "健康检查: $PASS 通过, $FAIL 失败"

    if [[ $FAIL -gt 0 ]]; then
        log_error "部署完成但存在警告，请检查上述失败项"
        return 1
    fi

    return 0
}

# ============================================
# 文件一致性检查
# ============================================

verify_sync() {
    log_info "验证文件一致性..."

    MISMATCH=0

    CORE_FILES=(
        "app.py" "api.py"
        "logging_config.py" "monitoring_config.py"
        "member_service.py" "account_service.py"
        "auth.py" "config.py" "models.py"
        "payment_service.py" "hair_service.py"
        "wechat_pay.py" "sms_service.py"
        "referral_service.py" "chat_service.py"
        "chat_notifier.py" "financial_service.py"
        "virtual_payment_service.py" "refund_service.py"
        "refund_notifier.py"
        "bailian_sketch_converter.py" "aliyun_hair_transfer_fixed.py"
        "hair_segmentation.py" "image_preprocessor.py" "sketch_converter.py"
        "scheduler.py" "fix_financial_records.py" "debug_config.py"
        "check_db_schema.py" "fix_db_schema.py" "monitor_financial.py"
    )

    for file in "${CORE_FILES[@]}"; do
        if [[ -f "$BACKEND_DIR/$file" ]]; then
            local_md5=$(md5 -q "$BACKEND_DIR/$file" 2>/dev/null || md5sum "$BACKEND_DIR/$file" | awk '{print $1}')
            remote_md5=$(remote_exec "md5sum $DEPLOY_PATH/$file" 2>/dev/null | awk '{print $1}')

            if [[ "$local_md5" == "$remote_md5" ]]; then
                log_info "  ✅ $file"
            else
                log_error "  ❌ $file 不一致 (本地: ${local_md5:0:8}... vs 远程: ${remote_md5:0:8}...)"
                MISMATCH=$((MISMATCH + 1))
            fi
        fi
    done

    echo ""
    if [[ $MISMATCH -gt 0 ]]; then
        log_warn "发现 $MISMATCH 个文件不一致，请检查同步过程"
    else
        log_info "所有文件一致性验证通过"
    fi

    echo ""
}

# ============================================
# 主流程
# ============================================

main() {
    local start_time=$(date +%s)

    check_prerequisites "$@"
    verify_deploy_paths
    sync_code
    sync_nginx_config
    check_env_completeness
    verify_static_paths
    check_domain_whitelist
    restart_services

    echo ""
    log_info "============================================"
    log_info "开始数据库结构检查..."
    log_info "============================================"
    echo ""

    DB_CHECK_RESULT=0
    check_db_schema || DB_CHECK_RESULT=$?

    echo ""
    log_info "============================================"
    log_info "开始财务流水监控..."
    log_info "============================================"
    echo ""

    monitor_financial

    echo ""
    log_info "============================================"
    log_info "开始健康检查..."
    log_info "============================================"
    echo ""

    HEALTH_RESULT=0
    health_check || HEALTH_RESULT=$?

    echo ""
    log_info "============================================"
    log_info "开始财务记录一致性检查..."
    log_info "============================================"
    echo ""

    # 财务记录检查（不阻塞部署，只输出结果）
    remote_exec "cd $DEPLOY_PATH && python3 fix_financial_records.py" 2>&1 || log_warn "财务记录检查失败"

    echo ""
    log_info "============================================"
    log_info "开始文件一致性验证..."
    log_info "============================================"
    echo ""

    verify_sync

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo ""
    echo -e "${BLUE}============================================${NC}"
    if [[ $HEALTH_RESULT -eq 0 && $DB_CHECK_RESULT -eq 0 ]]; then
        echo -e "${GREEN}✅ 部署成功! 耗时: ${duration}秒${NC}"
    else
        echo -e "${YELLOW}⚠️  部署完成但存在警告，耗时: ${duration}秒${NC}"
        if [[ $DB_CHECK_RESULT -ne 0 ]]; then
            echo -e "${YELLOW}   - 数据库结构存在问题${NC}"
        fi
        if [[ $HEALTH_RESULT -ne 0 ]]; then
            echo -e "${YELLOW}   - 健康检查存在警告${NC}"
        fi
    fi
    echo -e "${BLUE}============================================${NC}"
    echo ""
    echo "后端地址: https://$DOMAIN"
    echo "健康检查: https://$DOMAIN/api/monitoring/health"
    echo ""
}

# 执行
main "$@"
