"""
Firmware Packer Module - 固件打包器核心
"""

import os
import random
from typing import List, Dict, Any, Tuple, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .crc16 import calculate_custom_crc16
from .hex_parser import write_hex_file
from .mask_calculator import calculate_dynamic_mask_bytes


class FirmwarePacker:
    """
    固件打包器類別

    負責管理多分區固件配置，支援:
    - CRC16 計算與注入
    - 動態 Enable Mask 計算
    - 跨分區參數注入
    - HEX 檔案生成
    """

    def __init__(self):
        """初始化固件打包器"""
        self.sections: List[Dict[str, Any]] = []

    def load_csv_config(self, file_path: str) -> Tuple[bool, str]:
        """
        從 CSV 載入打包器配置。

        CSV 欄位:
            name: 分區名稱
            max_len: 最大長度
            file_path: 檔案路徑
            is_full: 是否完整填充
            target_sec: 目標分區
            size_offset: 大小偏移
            addr_offset: 位址偏移
            en_offset/en_bit/en_val: 啟用位參數
            crc_offset/crc_bit/crc_val: CRC 位參數
            mask_target/mask_offset/mask_val: 遮罩參數

        Args:
            file_path: CSV 檔案路徑

        Returns:
            Tuple[成功與否, 訊息]
        """
        if not PANDAS_AVAILABLE:
            return False, "pandas not available"

        def clean_str(val: Any) -> str:
            """防止 pandas 將 '14' 轉換為 '14.0'"""
            s = str(val).strip()
            if s.endswith('.0'):
                return s[:-2]
            return s

        def safe_int(val: Any, default: Any = "") -> Any:
            """安全地將值轉換為整數"""
            s = str(val).strip()
            if not s:
                return default
            try:
                if s.lower().startswith("0x") or s.lower().startswith("-0x"):
                    return int(s, 16)
                return int(float(s))
            except ValueError:
                return default

        def safe_hex(val: str) -> Any:
            """安全地解析十六進位值"""
            v = val.strip().replace("0x", "").replace("0X", "")
            try:
                return int(v, 16) if v else ""
            except ValueError:
                return ""

        try:
            df = pd.read_csv(file_path).fillna("")
            new_sections = []

            for _, row in df.iterrows():
                sec = {
                    'name': str(row.get('name', '')),
                    'max_len': safe_int(row.get('max_len'), 1024),
                    'file_path': str(row.get('file_path', '')),
                    'is_full': bool(row.get('is_full', True)),
                    'inject_err': bool(row.get('inject_err', False)),
                    'target_sec': str(row.get('target_sec', '')),

                    'size_offset': safe_int(row.get('size_offset')),
                    'size_offset_orig': clean_str(row.get('size_offset_orig')),

                    'en_offset': safe_int(row.get('en_offset')),
                    'en_offset_orig': clean_str(row.get('en_offset_orig')),
                    'en_bit': safe_int(row.get('en_bit')),
                    'en_val': safe_int(row.get('en_val'), 1),

                    'crc_offset': safe_int(row.get('crc_offset')),
                    'crc_offset_orig': clean_str(row.get('crc_offset_orig')),
                    'crc_bit': safe_int(row.get('crc_bit')),
                    'crc_val': safe_int(row.get('crc_val'), 1),

                    'addr_offset': safe_int(row.get('addr_offset')),
                    'addr_offset_orig': clean_str(row.get('addr_offset_orig')),

                    'mask_target': str(row.get('mask_target', '')),
                    'mask_offset': safe_int(row.get('mask_offset')),
                    'mask_offset_orig': clean_str(row.get('mask_offset_orig')),
                    'mask_val': safe_int(row.get('mask_val'), 0),

                    'calc_addr': 0,
                    'bypass_crc': bool(row.get('bypass_crc', False))
                }
                new_sections.append(sec)

            self.sections = new_sections
            return True, f"Loaded {len(self.sections)} sections."

        except Exception as e:
            return False, str(e)

    def save_csv_config(self, file_path: str) -> Tuple[bool, str]:
        """
        將配置儲存為 CSV 檔案。

        Args:
            file_path: 輸出 CSV 檔案路徑

        Returns:
            Tuple[成功與否, 訊息]
        """
        if not self.sections:
            return False, "No sections to save."

        if not PANDAS_AVAILABLE:
            return False, "pandas not available"

        try:
            pd.DataFrame(self.sections).to_csv(file_path, index=False)
            return True, file_path
        except Exception as e:
            return False, str(e)

    def calculate_addresses(self) -> None:
        """
        計算所有分區的動態絕對位址。

        位址從 0 開始，每個分區根據 max_len 遞增。
        """
        current_addr = 0
        for sec in self.sections:
            sec['calc_addr'] = current_addr
            current_addr += sec['max_len']

    def add_section(self, section: Dict[str, Any]) -> None:
        """
        添加一個分區配置。

        Args:
            section: 分區配置字典
        """
        self.sections.append(section)

    def remove_section(self, index: int) -> bool:
        """
        移除指定索引的分區。

        Args:
            index: 分區索引

        Returns:
            成功與否
        """
        if 0 <= index < len(self.sections):
            del self.sections[index]
            return True
        return False

    def get_section(self, index: int) -> Optional[Dict[str, Any]]:
        """
        取得指定索引的分區。

        Args:
            index: 分區索引

        Returns:
            分區配置或 None
        """
        if 0 <= index < len(self.sections):
            return self.sections[index]
        return None

    def generate_firmware_hex(self, output_file: str = "all_crc.hex") -> Tuple[bool, str]:
        """
        生成最終固件 HEX 檔案。

        流程分為四個階段:
        1. 緩衝區初始化、填充與規則驗證
        2. 跨分區參數注入 (CRC 計算前)
        3. CRC 計算與錯誤注入
        4. 寫入最終 HEX 檔案

        Args:
            output_file: 輸出檔案路徑

        Returns:
            Tuple[成功與否, 訊息]
        """
        if not self.sections:
            return False, "Section list is empty!"

        self.calculate_addresses()
        buffers = {}
        actual_lens = {}

        # ---------------------------------------------------------
        # Phase 1: 緩衝區初始化、填充與規則驗證
        # ---------------------------------------------------------
        for sec in self.sections:
            name = sec['name']
            max_len = sec['max_len']

            if sec['file_path'] and os.path.exists(sec['file_path']):
                try:
                    with open(sec['file_path'], 'r') as f:
                        lines = [line.strip() for line in f if line.strip()]

                    actual_len = len(lines)

                    # 規則檢查: 檔案長度必須 <= max_len
                    if actual_len > max_len:
                        return False, (
                            f"Error: File length ({actual_len}) exceeds "
                            f"Max Length ({max_len}) for section '{name}'."
                        )

                    # 規則檢查: 檔案必須足夠大以容納 CRC
                    if not sec.get('bypass_crc', False) and actual_len < 2:
                        return False, (
                            f"Error: File length ({actual_len}) is too small "
                            f"to embed CRC16 for section '{name}'."
                        )

                    # 填充邏輯: 如果 is_full 為 True，緩衝區大小為 max_len
                    buf_size = max_len if sec['is_full'] else actual_len
                    buf = bytearray([0xFF] * buf_size)

                    for i in range(actual_len):
                        buf[i] = int(lines[i], 16)

                except Exception as e:
                    return False, f"Error reading {sec['file_path']}: {e}"
            else:
                # 沒有檔案: 生成隨機資料
                actual_len = random.randint(2, max_len) if max_len >= 2 else max_len
                buf = bytearray([0xFF] * max_len)
                for i in range(actual_len):
                    buf[i] = random.getrandbits(8)

            buffers[name] = buf
            actual_lens[name] = actual_len

        # ---------------------------------------------------------
        # Phase 2: 跨分區參數注入 (CRC 計算前)
        # ---------------------------------------------------------
        for sec in self.sections:
            name = sec['name']

            # 參數注入
            target_name = sec['target_sec']
            if target_name and target_name in buffers:
                target_buf = buffers[target_name]

                # Size 注入
                if sec['size_offset'] != "":
                    off = int(sec['size_offset'])
                    if off < len(target_buf):
                        target_buf[off] = actual_lens[name] & 0xFF
                    if off + 1 < len(target_buf):
                        target_buf[off + 1] = (actual_lens[name] >> 8) & 0xFF

                # Address 注入
                if sec['addr_offset'] != "":
                    off = int(sec['addr_offset'])
                    addr = sec['calc_addr']
                    if off < len(target_buf):
                        target_buf[off] = addr & 0xFF
                    if off + 1 < len(target_buf):
                        target_buf[off + 1] = (addr >> 8) & 0xFF
                    if off + 2 < len(target_buf):
                        target_buf[off + 2] = (addr >> 16) & 0xFF

                # Enable Bit 注入
                if sec['en_offset'] != "" and sec['en_bit'] != "":
                    off = int(sec['en_offset'])
                    if off < len(target_buf):
                        bit = int(sec['en_bit'])
                        val = int(sec['en_val'])
                        if val:
                            target_buf[off] |= (1 << bit)
                        else:
                            target_buf[off] &= ~(1 << bit)

                # CRC Bit 注入
                if sec['crc_offset'] != "" and sec['crc_bit'] != "":
                    off = int(sec['crc_offset'])
                    if off < len(target_buf):
                        bit = int(sec['crc_bit'])
                        val = int(sec['crc_val'])
                        if val:
                            target_buf[off] |= (1 << bit)
                        else:
                            target_buf[off] &= ~(1 << bit)

            # Mask 注入 (動態位元組長度計算)
            mask_target = sec.get('mask_target', "")
            if mask_target and mask_target in buffers and sec.get('mask_offset', "") != "":
                mask_buf = buffers[mask_target]
                off = int(sec['mask_offset'])
                mask_val = int(sec.get('mask_val', 0))

                # 動態位元組計算
                byte_length = max(1, (mask_val.bit_length() + 7) // 8)

                # Little Endian 寫入目標分區
                for i in range(byte_length):
                    if off + i < len(mask_buf):
                        mask_buf[off + i] = (mask_val >> (i * 8)) & 0xFF

        # ---------------------------------------------------------
        # Phase 3: CRC 計算與錯誤注入
        # ---------------------------------------------------------
        for sec in self.sections:
            name = sec['name']
            buf = buffers[name]
            actual_len = actual_lens[name]

            if not sec.get('bypass_crc', False) and actual_len >= 2:
                # 計算 CRC (資料長度 L - 2)
                crc_val = calculate_custom_crc16(buf[:actual_len - 2])

                # CRC 錯誤注入
                if sec.get('inject_err', False):
                    wrong_crc = crc_val ^ 0xFFFF
                    print(f"[*] CRC Error Injection for '{name}'")
                    print(f"    ├── Correct CRC: 0x{crc_val:04X}")
                    print(f"    └── Injected CRC: 0x{wrong_crc:04X}")

                buf[actual_len - 2] = (crc_val >> 8) & 0xFF  # MSB
                buf[actual_len - 1] = crc_val & 0xFF         # LSB

                if sec.get('inject_err', False):
                    buf[actual_len - 1] ^= 0xFF

        # ---------------------------------------------------------
        # Phase 4: 寫入最終 HEX 檔案
        # ---------------------------------------------------------
        try:
            success = write_hex_file(output_file, bytearray(b for buf in buffers.values() for b in buf))
            if success:
                return True, f"Successfully generated HEX file:\n{output_file}"
            else:
                return False, "Failed to write HEX file"
        except Exception as e:
            return False, f"Write error: {str(e)}"


def create_packer_from_csv(csv_path: str) -> Optional[FirmwarePacker]:
    """
    便利函數: 從 CSV 建立打包器。

    Args:
        csv_path: CSV 檔案路徑

    Returns:
        打包器實例或 None
    """
    packer = FirmwarePacker()
    success, msg = packer.load_csv_config(csv_path)
    if success:
        return packer
    return None


if __name__ == "__main__":
    print("Firmware Packer Module Test")
    print("=" * 50)
    print("Note: This module requires pandas")
    print("Install with: pip install pandas")
