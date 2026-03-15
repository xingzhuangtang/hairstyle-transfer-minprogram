#!/bin/bash
# 发型迁移系统 - 启动脚本

echo "=========================================="
echo "  💇‍♂️ 发型迁移系统"
echo "  - 发型提取预览"
echo "  - 人脸融合技术"
echo "  - 素描风格转换"
echo "=========================================="
echo ""

# 检查环境变量
if [ -z "$ALIBABA_CLOUD_ACCESS_KEY_ID" ]; then
    echo "❌ 未设置环境变量"
    echo ""
    echo "请先执行:"
    echo "export ALIBABA_CLOUD_ACCESS_KEY_ID='你的key'"
    echo "export ALIBABA_CLOUD_ACCESS_KEY_SECRET='你的secret'"
    echo ""
    exit 1
fi

echo "✅ 环境变量已设置"
echo ""
echo "启动中..."
echo ""
echo "📍 访问地址: http://localhost:5002"
echo "📍 按 Ctrl+C 停止服务"
echo ""

python3 app.py
