# Bug 记录

## BUG-2026-025 - 素描优化/视频绘制功能失效

### 基本信息

| 字段 | 内容 |
|------|------|
| 等级 | **P1 - 严重** |
| 状态 | 已修复 |
| 发现日期 | 2026-10-16 |
| 修复日期 | 2026-10-16 |
| 影响范围 | 素描优化、视频绘制功能完全不可用 |
| 影响用户 | 所有线上用户 |

### 问题描述

用户点击"素描优化"按钮后，发型迁移成功但素描图片无法生成。点击"视频绘制"按钮后，提示"没有素描图片"，手绘视频无法生成。

### 根因分析

**直接原因**：服务器上缺少 `httpx` Python 模块。

**故障链路**：
1. `bailian_sketch_converter.py` 依赖 `httpx` 调用百炼 AI API
2. `httpx` 未安装 → `BailianSketchConverter` 导入失败 → `BAILIAN_SKETCH_AVAILABLE = False`
3. 降级到 OpenCV `SketchConverter`
4. OpenCV 转换器只支持 `pencil/detailed/artistic/color` 四种风格
5. 前端发送 `sketch_style: "vivid"` → OpenCV 抛出 `"未知的素描风格: vivid"` 异常
6. 素描生成失败，`sketch_url` 为空，视频绘制也无法进行

**根本原因**：
- 部署时遗漏了 `httpx` 依赖（`requirements.txt` 中可能未包含或安装时跳过）
- OpenCV `SketchConverter` 未对 `vivid` 风格做兼容处理

### 修复方案

#### 修复 1：安装缺失依赖（根本修复）

```bash
cd /opt/hairstyle-transfer-v5.3-release/backend
source venv/bin/activate
pip install httpx certifi
```

#### 修复 2：OpenCV 降级兼容（防御性修复）

**文件**：`backend/sketch_converter.py:249`

将 `vivid` 风格映射到 `color`（两者效果一致，都是淡彩素描），避免 OpenCV 降级时崩溃：

```python
# 修复前
elif style == 'color':

# 修复后
elif style in ('color', 'vivid'):
```

### 涉及文件

| 文件 | 修改内容 |
|------|----------|
| `backend/sketch_converter.py` | `vivid` 风格兼容到 `color` 分支 |
| 服务器环境 | 安装 `httpx` + `certifi` |

### 验证结果

- 本地测试：素描优化、视频绘制均正常
- 线上部署：百炼素描转换器加载成功，支持全部 5 种风格（pencil, anime, ink, color, vivid）

### 经验教训

1. **依赖完整性**：部署时应验证所有关键依赖是否安装，特别是 AI API 调用相关的模块
2. **降级容错**：主方案失败时的降级路径也需要覆盖所有输入场景
3. **启动日志检查**：应关注启动日志中 `✅ 百炼素描转换器可用` 是否出现，确认核心模块加载正常

### 等级说明

| 等级 | 定义 |
|------|------|
| P0 - 致命 | 系统崩溃，核心功能完全不可用 |
| **P1 - 严重** | **核心功能失效，影响所有用户，无可用替代方案** |
| P2 - 一般 | 非核心功能异常，有替代方案 |
| P3 - 轻微 | 体验问题，不影响功能使用 |
