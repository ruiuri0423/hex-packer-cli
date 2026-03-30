"""
Register Parser Module - 寄存器 Excel 解析
"""

import os
from typing import Tuple, Optional
from .crc16 import calculate_custom_crc16
from .hex_parser import parse_hex_address

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def parse_register_excel_to_buffer(
    file_path: str,
    page_size: int = 256
) -> Tuple[bool, bytearray]:
    """
    讀取寄存器 Excel 檔案，提取 Init 值並位移到 LSB 位置，
    返回包含 CRC 的固定大小緩衝區。

    Args:
        file_path: Excel 檔案路徑 (.xlsx/.xls)
        page_size: 頁面緩衝區大小 (預設 256 bytes)

    Returns:
        Tuple[成功與否, 緩衝區資料]

    Excel 欄位格式:
        0: High Address
        1: Low Address
        2: Loc MSB
        3: Loc LSB
        4: Name
        5: MSB
        6: LSB
        7: Bits
        8: Init Value (格式: hXXXX 或 0xXXXX)
        9: r/w
        10: Description (可選)

    Example:
        >>> success, buf = parse_register_excel_to_buffer("register.xlsx")
        >>> if success:
        ...     print(f"Buffer size: {len(buf)} bytes")
    """
    if not PANDAS_AVAILABLE:
        print("Warning: pandas not available, returning empty buffer")
        return False, bytearray(page_size)

    page_buffer = bytearray(page_size)

    try:
        df = pd.read_excel(file_path).fillna("")
        total_cols = len(df.columns)

        for idx, row in df.iterrows():
            # 確保有足夠的欄位
            if total_cols < 10:
                continue

            # 解析位址
            low = parse_hex_address(row.iloc[1])
            high = parse_hex_address(row.iloc[0])
            if low < 0 or high < 0:
                continue

            # 取得 LSB 位置以確定位移
            loc_lsb_str = str(row.iloc[3]).strip()
            try:
                loc_lsb = int(loc_lsb_str)
            except ValueError:
                loc_lsb = 0

            # 解析 Init 值
            init_str = str(row.iloc[8]).replace('h', '').replace('0x', '').strip()
            if not init_str:
                continue

            try:
                init_val = int(init_str, 16)
                # 將值位移到正確的位元欄位置
                shifted_val = init_val << loc_lsb

                span = (high - low) + 1
                max_bytes = max(span, (shifted_val.bit_length() + 7) // 8)

                # 安全地對每個需要的位元組應用 OR
                for i in range(max_bytes):
                    if low + i < page_size - 2:  # 保留最後 2 bytes 給 CRC
                        page_buffer[low + i] |= ((shifted_val >> (i * 8)) & 0xFF)

            except ValueError:
                pass

        # 計算 CRC (0x00 到 0xFD)
        crc_val = calculate_custom_crc16(page_buffer[:page_size - 2])
        page_buffer[page_size - 2] = (crc_val >> 8) & 0xFF  # MSB
        page_buffer[page_size - 1] = crc_val & 0xFF         # LSB

        return True, page_buffer

    except Exception as e:
        return False, bytearray(page_size)


def parse_register_excel_with_mapping(
    file_path: str,
    page_size: int = 256
) -> Tuple[bool, bytearray, list]:
    """
    讀取寄存器 Excel 並返回映射資訊。

    除了緩衝區，還返回詳細的寄存器映射列表，
    包括每個寄存器的位址範圍、LSB/MSB 等。

    Args:
        file_path: Excel 檔案路徑
        page_size: 頁面緩衝區大小

    Returns:
        Tuple[成功與否, 緩衝區, 映射列表]

    映射列表格式:
        [{
            'high_addr': int,
            'low_addr': int,
            'loc_msb': int,
            'loc_lsb': int,
            'name': str,
            'bits': int,
            'init': str,
            'start_bit': int,
            'end_bit': int,
        }, ...]
    """
    if not PANDAS_AVAILABLE:
        return False, bytearray(page_size), []

    page_buffer = bytearray(page_size)
    mapping = []

    try:
        df = pd.read_excel(file_path).fillna("")
        total_cols = len(df.columns)

        for idx, row in df.iterrows():
            if total_cols < 10:
                continue

            low = parse_hex_address(row.iloc[1])
            high = parse_hex_address(row.iloc[0])
            if low < 0 or high < 0:
                continue

            try:
                loc_msb = int(row.iloc[2])
            except ValueError:
                loc_msb = 7

            try:
                loc_lsb = int(row.iloc[3])
            except ValueError:
                loc_lsb = 0

            # 絕對位元追蹤
            start_bit = low * 8 + loc_lsb
            end_bit = high * 8 + loc_msb

            if end_bit < start_bit:
                end_bit = start_bit

            name = str(row.iloc[4]).strip()
            raw_desc = str(row.iloc[10]).strip() if total_cols > 10 else ""

            mapping.append({
                'start_bit': start_bit,
                'end_bit': end_bit,
                'high_addr': high,
                'low_addr': low,
                'high_addr_hex': f"h{high:04X}",
                'low_addr_hex': f"h{low:04X}",
                'loc_msb': str(loc_msb),
                'loc_lsb': str(loc_lsb),
                'name': name,
                'msb': str(row.iloc[5]).strip(),
                'lsb': str(row.iloc[6]).strip(),
                'bits': str(row.iloc[7]).strip(),
                'init': str(row.iloc[8]).strip(),
                'rw': str(row.iloc[9]).strip(),
                'raw_desc': raw_desc,
                'display_desc': raw_desc.replace('\n', ' ↵ ').replace('\r', '')
            })

            # 填充緩衝區
            init_str = mapping[-1]['init'].replace('h', '').replace('0x', '').strip()
            if init_str:
                try:
                    init_val = int(init_str, 16)
                    shifted_val = init_val << loc_lsb
                    span = (high - low) + 1
                    max_bytes = max(span, (shifted_val.bit_length() + 7) // 8)

                    for i in range(max_bytes):
                        if low + i < page_size - 2:
                            page_buffer[low + i] |= ((shifted_val >> (i * 8)) & 0xFF)
                except ValueError:
                    pass

        # 計算並嵌入 CRC
        crc_val = calculate_custom_crc16(page_buffer[:page_size - 2])
        page_buffer[page_size - 2] = (crc_val >> 8) & 0xFF
        page_buffer[page_size - 1] = crc_val & 0xFF

        return True, page_buffer, mapping

    except Exception as e:
        return False, bytearray(page_size), []


def validate_register_excel(file_path: str) -> Tuple[bool, str]:
    """
    驗證寄存器 Excel 檔案的格式。

    Args:
        file_path: Excel 檔案路徑

    Returns:
        Tuple[有效與否, 錯誤訊息]
    """
    if not PANDAS_AVAILABLE:
        return False, "pandas not available"

    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"

    try:
        df = pd.read_excel(file_path)
        total_cols = len(df.columns)

        if total_cols < 10:
            return False, f"Insufficient columns: {total_cols} (expected >= 10)"

        # 檢查必要的欄位
        required_headers = ['Init', 'Name']
        # 這裡不做嚴格檢查，因為欄位可能是數字索引

        return True, ""

    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    print("Register Parser Module Test")
    print("=" * 50)
    print("Note: This module requires pandas and openpyxl")
    print("Install with: pip install pandas openpyxl")
