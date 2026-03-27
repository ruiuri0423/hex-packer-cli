# 🔧 Hex Packer CLI

**Firmware Pipeline Studio (Ultimate Flagship Edition)**

一個功能完整的固件管線工具，支援 HEX 檔案解析、CRC16 計算、寄存器整合、以及自動化 CLI 操作。

---

## 📋 功能概覽

| 功能 | 說明 |
|------|------|
| **Firmware Packer** | 多分區固件打包，支援自定義 CRC、Enable Mask、位址注入 |
| **M0 HEX Converter** | Intel HEX 與原始 HEX 格式轉換 |
| **Register Integrator** | 多寄存器 Excel 表整合，自動計算 16-bit Enable Mask |
| **Single Map Viewer** | 寄存器位元映射查看器，自動檢測缺口與 CRC 位置 |

---

## 🚀 快速開始

### GUI 模式
```bash
cd /mnt/openwebui_data/hex_packer_cli/src
python3 main.py
```

### CLI 模式
```bash
# 基本打包
python3 main.py --cli --config config.csv --output firmware.hex

# 完整管道 (包含 M0 和寄存器整合)
python3 main.py \
  --cli \
  --config "packer_config.csv" \
  --output "firmware.hex" \
  --m0_in "M0_firmware.hex" \
  --m0_out "M0_expanded.hex" \
  --reg_csv "integrator_config.csv" \
  --reg_base "0000" \
  --reg_out "all_registers.hex"
```

---

## 📦 安裝依賴

```bash
pip install pandas openpyxl
```

---

## 📂 專案結構

```
hex_packer_cli/
├── README.md              # 本檔案
├── docs/
│   └── 功能解析報告.md      # 詳細功能分析
└── src/
    └── main.py            # 主程式碼
```

---

## 🔐 CRC16 參數

| 參數 | 值 |
|------|-----|
| 多項式 | 0x8005 |
| 初始值 | 0x0052 |
| 對應 Verilog | ✅ 完全硬體對應 |

---

## 📊 版本資訊

- **版本時間：** 2026-03-26 17:20:42
- **程式大小：** 75 KB
- **Python 版本：** 3.x
- **GUI 框架：** Tkinter

---

## ⚙️ CLI 參數速查

| 參數 | 必填 | 說明 |
|------|------|------|
| `--cli` | 是 | 啟用 CLI 無頭模式 |
| `--config` | 是 | Packer CSV 配置文件 |
| `--output` | 否 | 輸出檔案 (預設: all_crc.hex) |
| `--m0_in` | 否 | M0 HEX 輸入檔案 |
| `--m0_out` | 否 | M0 HEX 輸出檔案 |
| `--reg_csv` | 否 | Integrator CSV 配置 |
| `--reg_base` | 否 | 全域基址 (預設: 0000) |
| `--reg_out` | 否 | 整合寄存器 HEX 輸出 |

---

## 📖 更多資訊

請參閱 [docs/功能解析報告.md](docs/功能解析報告.md) 了解完整的技術細節。

---

*Generated on 2026-03-27*
