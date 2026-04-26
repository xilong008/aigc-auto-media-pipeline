#!/bin/bash
cd "$(dirname "$0")"

echo "========================================="
echo "       AIGC 自媒体全程自动化系统"
echo "========================================="

# 1. 自动环境检查与登录拦截
if [ ! -d "src/xhs_profile" ]; then
    echo "⚠️ 检测到首次运行，正在为您拉起安全隐身浏览器..."
    echo "👉 请在弹出的浏览器内【扫码或者静默登录小红书】"
    echo "👉 登录成功看到创作者主页后，窗口会在此后为您终身托管后台"
    venv/bin/python src/rpa_xiaohongshu.py
    echo "✅ 授权凭据已物理离线加密封存！"
else
    echo "✅ 已挂载设备环境，免密登录就绪。"
fi

# 2. 中枢一键启动
echo "🚀 启动 AIGC 系统引擎 (监听本地待办指令中)..."
venv/bin/python src/main.py
