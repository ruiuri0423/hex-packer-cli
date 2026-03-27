#!/bin/bash
# ============================================================
# Hex Packer CLI - 快速啟動腳本
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/src"

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤: 未找到 python3，請先安裝 Python 3"
    exit 1
fi

# 檢查必要依賴
echo "🔍 檢查依賴套件..."
python3 -c "import pandas; import openpyxl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 安裝依賴套件..."
    pip install pandas openpyxl
fi

# 啟動 GUI 模式
echo "🚀 啟動 Firmware Pipeline Studio..."
python3 main.py "$@"
