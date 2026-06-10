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
        # --- AI / 图像处理 ---
        "bailian_sketch_converter.py"
        "aliyun_hair_transfer_fixed.py"
        "hair_segmentation.py"
        "image_preprocessor.py"
        "sketch_converter.py"
        # --- 运维 / 调度 ---
        "scheduler.py"
        "fix_financial_records.py"
        "debug_config.py"
    )

    for file in "${CORE_FILES[@]}"; do
        if [[ -f "$BACKEND_DIR/$file" ]]; then
            remote_scp "$BACKEND_DIR/$file" "$SSH_USER@$SERVER_IP:$DEPLOY_PATH/"
            log_info "  已同步: $file"
        else
            log_warn "  本地不存在: $file (跳过)"
        fi
    done

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
    sync_code
    sync_nginx_config
    check_env_completeness
    restart_services

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
    if [[ $HEALTH_RESULT -eq 0 ]]; then
        echo -e "${GREEN}✅ 部署成功! 耗时: ${duration}秒${NC}"
    else
        echo -e "${YELLOW}⚠️  部署完成但存在警告，耗时: ${duration}秒${NC}"
    fi
    echo -e "${BLUE}============================================${NC}"
    echo ""
    echo "后端地址: https://$DOMAIN"
    echo "健康检查: https://$DOMAIN/api/monitoring/health"
    echo ""
}

# 执行
main "$@"
