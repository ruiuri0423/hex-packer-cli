# Tab3 測試範例

## 測試場景

此測試範例展示了新的 Register Integrator 邏輯：

### 設定
- **Base Address**: 0x1000
- **Table_A**: 0x1000 (Bit 0)
- **Table_B**: 0x1300 (Bit 3, 有 Gap)
- **Table_C**: 0x2000 (Bit 16, 有大 Gap)

### 新邏輯驗證

1. **Auto-Alignment**
   - 如果 Flash < Base，自動對齊到 Base
   - 如果非 256 對齊，自動向下對齊

2. **動態 Mask 計算**
   - Mask Bits = (Max_Addr - Base) / 256 + 1
   - Mask Bytes = (Bits + 7) / 8
   - 本例：Max = 0x2000, Base = 0x1000
   - Bits = 17, Bytes = 3
   - Mask = 0x10009

3. **Gap 檢測**
   - Gap #1: 0x1100 ~ 0x12FF (Table_A → Table_B)
   - Gap #2: 0x1400 ~ 0x1FFF (Table_B → Table_C)

4. **HEX 填補**
   - Gap 區域填補 0xFF

## 使用方式

```bash
# CLI 測試
cd src
python3 main.py --cli \
  --config packer_config.csv \
  --reg_csv ../test_samples/integrator_config.csv \
  --reg_base 1000 \
  --reg_out ../test_samples/output.hex
```

## 預期輸出

```
[*] Parsing Integrator Config: ../test_samples/integrator_config.csv
[*] Global Base Address: 0x1000
[*] Validating and auto-aligning Flash Addresses...
[*] Max Flash Address: 0x2000
[*] Total Enable Bits needed: 17
[*] Mask Byte Length: 3 byte(s)
[*] Enable Mask (Hex): 0x010009

[*] Bit-to-Address Mapping (Base 0x1000 + Bit*N*256):
    ├── Bit  0: 0x1000 - Table_A
    [GAP #1] 0x1100 - 0x12FF (1 blocks = Mask bits = 0)
    ├── Bit  3: 0x1300 - Table_B
    [GAP #2] 0x1400 - 0x1FFF (12 blocks = Mask bits = 0)
    ├── Bit 16: 0x2000 - Table_C

[*] Generating Integrated HEX (Size: 4352 bytes)...
[*] Gap areas will be filled with 0xFF padding

[+] Integrator Generated successfully
```
