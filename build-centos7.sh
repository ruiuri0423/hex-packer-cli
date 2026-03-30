#!/bin/bash
# ============================================================
# Hex Packer CLI - CentOS 7 本地編譯腳本
# 適用於直接在 CentOS 7 機器上執行
# ============================================================

set -e

VERSION=${1:-"1.2.3"}
OUTPUT_DIR="output"
BUILD_DIR="build_temp"

echo "=== Hex Packer CLI - CentOS 7 Build Script ==="
echo "Version: $VERSION"
echo ""

# 檢查系統
echo "[1/7] 檢查系統環境..."
if [[ -f /etc/centos-release ]]; then
    echo "  ✓ CentOS 系統偵測成功"
else
    echo "  ⚠ 警告: 非 CentOS 系統，可能不相容"
fi

# 安裝依賴
echo "[2/7] 安裝系統依賴..."
sudo yum -y install epel-release
sudo yum -y groupinstall "Development Tools"
sudo yum -y install python3 python3-pip wget git

# 安裝 Python 3.11 (重要!)
echo "[3/7] 安裝 Python 3.11..."
if ! command -v python3.11 &> /dev/null; then
    wget https://centos7.iuscommunity.org/ius-release.rpm
    sudo rpm -ivh ius-release.rpm
    sudo yum -y install python311 python311-pip python311-devel
    sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
    rm -f ius-release.rpm
fi

# 設定 Python 3.11
sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
sudo ln -sf /usr/bin/pip3.11 /usr/bin/pip3
echo "  Python 版本: $(python3 --version)"

# 建立虛擬環境
echo "[4/7] 建立 Python 虛擬環境..."
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
echo "[5/7] 安裝 Python 依賴..."
pip install --upgrade pip
pip install pyinstaller pandas openpyxl

# 建立 PyInstaller spec
echo "[6/7] 建立 PyInstaller 設定..."
cat > hex_packer.spec << 'SPEC'
block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/core', 'core')],
    hiddenimports=[
        'pandas', 'openpyxl', 'tkinter', 'threading',
        'core.crc16', 'core.hex_parser', 'core.mask_calculator',
        'core.packer', 'core.register', 'core.viewer',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='hex-packer-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False,
    name='hex-packer-cli',
)
SPEC

# 編譯
echo "[7/7] 編譯中..."
rm -rf build dist
pyinstaller hex_packer.spec --clean
chmod +x dist/hex-packer-cli/hex-packer-cli

# 測試
echo ""
echo "測試 binary..."
./dist/hex-packer-cli/hex-packer-cli --help | head -5

# 打包
echo ""
echo "建立發布包..."
mkdir -p "$OUTPUT_DIR"
cd dist
tar -czf "$OUTPUT_DIR/hex-packer-cli-centos7-${VERSION}.tar.gz" hex-packer-cli/
cd ..
sha256sum "$OUTPUT_DIR/hex-packer-cli-centos7-${VERSION}.tar.gz" > "$OUTPUT_DIR/hex-packer-cli-centos7-${VERSION}.tar.gz.sha256"

echo ""
echo "=== ✅ 編譯完成 ==="
echo "輸出目錄: $OUTPUT_DIR/"
ls -lh "$OUTPUT_DIR/"
echo ""
echo "SHA256:"
cat "$OUTPUT_DIR/hex-packer-cli-centos7-${VERSION}.tar.gz.sha256"
echo ""
echo "使用方法:"
echo "  tar -xzf $OUTPUT_DIR/hex-packer-cli-centos7-${VERSION}.tar.gz"
echo "  cd hex-packer-cli"
echo "  chmod +x hex-packer-cli"
echo "  ./hex-packer-cli --help"
