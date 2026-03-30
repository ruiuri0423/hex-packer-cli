# Hex Packer CLI v1.2.3

## 📦 下載說明

### Linux 執行檔 (推薦)

下載 `hex-packer-cli/` 資料夾並執行：

```bash
chmod +x hex-packer-cli/hex-packer-cli
./hex-packer-cli/hex-packer-cli --help
```

### 原始碼

下載 `hex-packer-cli-1.2.3-src.tar.gz` 並解壓縮：

```bash
tar -xzf hex-packer-cli-1.2.3-src.tar.gz
cd hex-packer-cli-1.2.3
pip install -r requirements.txt
python3 src/main.py
```

## 🔧 版本資訊

- **版本**: 1.2.3
- **建置日期**: 2026-03-30
- **目標平台**: linux-x86_64
- **建置類型**: Static (靜態連結)

## ✨ 新功能

本次更新包含靜態編譯版本，解決跨系統相容性問題：
- ✅ 靜態連結所有 Python 標準函式庫
- ✅ 內嵌所有必要依賴（pandas, openpyxl）
- ✅ 無需安裝 Python 環境即可執行
- ✅ 支援大多數 Linux 發行版

## 📋 SHA256 校驗碼

```
Binary:  c81a16b1d0b64f067cf126435980fdb707e0c0d5364fefa45211f4f25ded0ccd
Source:  ef68999c244cb65a0e0beded359d9cdf64f8f579c91e62a6695030b3dfa36b1a
```

## 📖 使用方式

### GUI 模式（預設）
```bash
./hex-packer-cli --gui
```

### CLI 模式
```bash
# 打包固件
./hex-packer-cli --cli --config config.csv --output firmware.hex

# 轉換 M0 HEX
./hex-packer-cli --cli --m0_in firmware.hex --m0_out m0_output.hex

# 整合暫存器表格
./hex-packer-cli --cli --reg_csv registers.csv --reg_base 0000 --reg_out registers.hex
```

## 📁 目錄結構

```
hex-packer-cli/
├── hex-packer-cli      # 主執行檔
├── _internal/          # 依賴函式庫
├── VERSION             # 版本資訊
└── README.md           # 本說明檔
```

## ⚠️ 注意事項

1. **Tkinter GUI**: 需要系統已安裝 Tkinter (`apt install python3-tk`)
2. **執行權限**: 請確保 `hex-packer-cli` 具有執行權限
3. **心血漏洞**: 若在安全性要求高的環境使用，請注意 Python 版本的已知漏洞

---
Built with PyInstaller | https://github.com/ruiuri0423/hex-packer-cli
