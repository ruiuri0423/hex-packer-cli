"""
HEX Parser Module - HEX 位址解析與 Intel HEX 處理
"""

from typing import Tuple, Union, List


def parse_hex_address(val: Union[str, int]) -> int:
    """
    安全地將字串形式的十六進位位址轉換為整數。

    支援格式:
    - "h00FF" → 0x00FF
    - "0xFF" → 0xFF
    - "FF" → 0xFF
    - 純數字 → 直接返回

    Args:
        val: 要解析的值 (字串或整數)

    Returns:
        解析後的整數位址，解析失敗返回 -1

    Example:
        >>> parse_hex_address("h00FF")
        255
        >>> parse_hex_address("0xFF")
        255
        >>> parse_hex_address("FF")
        255
    """
    if isinstance(val, int):
        return val

    val_str = str(val).strip().lower().replace('h', '').replace('0x', '')
    if not val_str:
        return -1

    try:
        return int(val_str, 16)
    except ValueError:
        return -1


def parse_m0_hex_file(filepath: str) -> Tuple[bool, bytearray, int]:
    """
    智慧解析器，自動偵測標準 Intel HEX 或原始空格分隔 HEX。

    支援兩種格式:
    1. 標準 Intel HEX (: 開頭)
       - 自動解析 Extended Linear Address (Record Type 0x04)
       - 空白區域填充 0xFF

    2. 原始空格分隔 HEX (.hex/.txt)
       - 直接讀取並轉換為 bytearray

    Args:
        filepath: HEX 檔案路徑

    Returns:
        Tuple[成功與否, 資料緩衝區, 原始大小]

    Example:
        >>> success, buf, size = parse_m0_hex_file("firmware.hex")
        >>> if success:
        ...     print(f"Parsed {size} bytes")
    """
    try:
        with open(filepath, 'r') as f:
            first_char = f.read(1)

        if first_char == ':':
            # 模式 1: 標準 Intel HEX
            return _parse_intel_hex(filepath)
        else:
            # 模式 2: 原始空格分隔 HEX
            return _parse_raw_hex(filepath)

    except Exception as e:
        return False, bytearray(), 0


def _parse_intel_hex(filepath: str) -> Tuple[bool, bytearray, int]:
    """
    解析標準 Intel HEX 格式。

    支援記錄類型:
    - 0x00: 數據記錄
    - 0x04: 擴展線性位址

    Args:
        filepath: HEX 檔案路徑

    Returns:
        Tuple[成功與否, 資料緩衝區, 原始大小]
    """
    memory = {}
    base_addr = 0

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line[0] != ':':
                continue

            try:
                byte_count = int(line[1:3], 16)
                address = int(line[3:7], 16)
                record_type = int(line[7:9], 16)

                if record_type == 0:  # 數據記錄
                    for i in range(byte_count):
                        addr = base_addr + address + i
                        memory[addr] = int(line[9 + i * 2:11 + i * 2], 16)

                elif record_type == 4:  # 擴展線性位址
                    base_addr = int(line[9:13], 16) << 16

            except (ValueError, IndexError):
                continue

    if not memory:
        return False, bytearray(), 0

    # 建立連續緩衝區，空白區域填充 0xFF
    min_addr = min(memory.keys())
    max_addr = max(memory.keys())
    orig_size = (max_addr - min_addr) + 1

    buf = bytearray([0xFF] * orig_size)
    for addr, val in memory.items():
        buf[addr - min_addr] = val

    return True, buf, orig_size


def _parse_raw_hex(filepath: str) -> Tuple[bool, bytearray, int]:
    """
    解析原始空格分隔 HEX 格式。

    每一行包含多個以空格分隔的十六進位值。

    Args:
        filepath: HEX 檔案路徑

    Returns:
        Tuple[成功與否, 資料緩衝區, 原始大小]
    """
    buf = bytearray()

    with open(filepath, 'r') as f:
        for line in f:
            tokens = line.strip().split()
            for token in tokens:
                if token:
                    try:
                        buf.append(int(token, 16))
                    except ValueError:
                        continue

    return True, buf, len(buf)


def write_hex_file(filepath: str, data: bytearray) -> bool:
    """
    將資料寫入 HEX 檔案。

    格式: 每行一個位元組 (02X)

    Args:
        filepath: 輸出檔案路徑
        data: 要寫入的資料

    Returns:
        成功與否

    Example:
        >>> buf = bytearray([0x00, 0x01, 0x02, 0xFF])
        >>> write_hex_file("output.hex", buf)
        True
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for byte in data:
                f.write(f"{byte:02X}\n")
        return True
    except Exception:
        return False


def read_hex_file(filepath: str) -> Tuple[bool, bytearray, str]:
    """
    讀取 HEX 檔案。

    自動偵測格式 (Intel HEX 或 Raw HEX)。

    Args:
        filepath: 輸入檔案路徑

    Returns:
        Tuple[成功與否, 資料緩衝區, 錯誤訊息]
    """
    success, buf, size = parse_m0_hex_file(filepath)
    if success:
        return True, buf, ""
    return False, bytearray(), "Failed to parse HEX file"


def hex_to_hex_string(data: bytearray, bytes_per_line: int = 16) -> str:
    """
    將 HEX 資料轉換為可讀的字串格式。

    Args:
        data: HEX 資料
        bytes_per_line: 每行位元組數

    Returns:
        格式化的 HEX 字串

    Example:
        >>> buf = bytearray([0x00, 0x01, 0x02, 0x03])
        >>> print(hex_to_hex_string(buf))
        00 01 02 03
    """
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        hex_str = ' '.join(f"{b:02X}" for b in chunk)
        addr_str = f"{i:04X}: "
        lines.append(addr_str + hex_str)
    return '\n'.join(lines)


if __name__ == "__main__":
    # 簡單測試
    print("HEX Parser Module Test")
    print("=" * 50)

    # Test address parsing
    test_cases = [
        ("h00FF", 0x00FF),
        ("0xFF", 0xFF),
        ("FF", 0xFF),
        ("0x1234", 0x1234),
        ("invalid", -1),
    ]

    print("\n[Test] Address Parsing:")
    for addr_str, expected in test_cases:
        result = parse_hex_address(addr_str)
        mark = "✓" if result == expected else "✗"
        print(f"  {mark} '{addr_str}' → 0x{result:04X} (expected 0x{expected:04X})")
