"""
Mask Calculator Module - Flash 位址對齊與 Enable Mask 計算
"""

from typing import List, Dict, Tuple, Any, Optional


def validate_and_align_flash_address(
    item_addr: int,
    base_addr: int
) -> Tuple[int, bool, str]:
    """
    驗證 Flash 位址並自動對齊到 base address。

    規則:
    1. 如果 Flash 位址 < Base 位址，對齊到 Base 位址
    2. Flash 位址必須 256-byte 對齊 (低位元組為 0)

    Args:
        item_addr: 項目 Flash 位址
        base_addr: 全域基址

    Returns:
        Tuple[調整後位址, 是否調整, 警告訊息]

    Example:
        >>> addr, adjusted, warning = validate_and_align_flash_address(0x1234, 0x1000)
        >>> print(f"Adjusted: {adjusted}, New addr: 0x{addr:04X}")
    """
    was_adjusted = False
    alignment_warning = ""

    # 確保輸入是整數
    try:
        item_addr = int(item_addr)
        base_addr = int(base_addr)
    except (ValueError, TypeError):
        return base_addr, False, "Invalid address type"

    # 規則 1: 如果 Flash 位址 < Base 位址，對齊到 Base 位址
    if item_addr < base_addr:
        item_addr = base_addr
        was_adjusted = True
        alignment_warning = f"Auto-aligned from below base to 0x{item_addr:04X}"

    # 規則 2: 確保 256-byte 對齊
    if item_addr > 0 and item_addr % 256 != 0:
        old_addr = item_addr
        item_addr = (item_addr // 256) * 256
        alignment_warning = (
            f"Auto-aligned from 0x{old_addr:04X} to 0x{item_addr:04X} "
            f"(256-byte boundary)"
        )
        was_adjusted = True

    return item_addr, was_adjusted, alignment_warning


def calculate_dynamic_mask_bytes(
    max_flash_addr: int,
    base_addr: int
) -> Tuple[int, int]:
    """
    計算動態 Mask 位元組數。

    規則:
    - 計算所需位元數 = (max_flash_addr - base_addr) // 256 + 1
    - 轉換為位元組 = (bits_needed + 7) // 8
    - 最小值為 1 位元組

    Args:
        max_flash_addr: 最大 Flash 位址
        base_addr: 全域基址

    Returns:
        Tuple[mask_位元組數, 總位元數]

    Example:
        >>> bytes_needed, total_bits = calculate_dynamic_mask_bytes(0x2000, 0x1000)
        >>> print(f"Need {bytes_needed} bytes for {total_bits} bits")
    """
    try:
        max_flash_addr = int(max_flash_addr)
        base_addr = int(base_addr)
    except (ValueError, TypeError):
        return 1, 1  # 最小為 1 bit

    if max_flash_addr < base_addr:
        return 1, 1  # 最小為 1 bit

    # 計算從 base 到 max 位址有多少個 256-byte 區塊
    offset = max_flash_addr - base_addr
    
    # 確保至少 1 bit (Bit 0 = base_addr)
    total_bits = (offset // 256) + 1

    # 轉換為位元組
    mask_bytes = (total_bits + 7) // 8

    return max(1, mask_bytes), total_bits


def calculate_enable_mask_with_gaps(
    enabled_items: List[Dict[str, Any]],
    base_addr: int
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    計算考慮 Gap 的 Enable Mask。

    規則:
    - 對於每個已啟用的表格，計算位元位置 = (addr - base) // 256
    - Flash 位址中的 Gap = 對應的 mask 位元 = 0
    - 返回 mask 值和位元位置映射

    Args:
        enabled_items: 已啟用的項目列表 [{'name': str, 'addr': int}, ...]
        base_addr: 全域基址

    Returns:
        Tuple[mask_值, mask_位元組數, 位元映射資訊]

    Example:
        >>> items = [{'name': 'Table_A', 'addr': 0x1000}]
        >>> mask, bytes, mapping = calculate_enable_mask_with_gaps(items, 0x1000)
        >>> print(f"Mask: 0x{mask:04X}")
    """
    if not enabled_items:
        return 0, 1, []

    # 找出最大位址來確定位元組長度
    max_addr = max(item['addr'] for item in enabled_items)
    mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)

    # 計算 mask 值 (Gap 會自動為 0)
    mask_value = 0
    bit_mapping = []

    for item in enabled_items:
        addr = item['addr']
        bit_pos = (addr - base_addr) // 256

        if 0 <= bit_pos < total_bits:
            mask_value |= (1 << bit_pos)
            bit_mapping.append({
                'name': item['name'],
                'addr': addr,
                'bit_pos': bit_pos,
                'enabled': True
            })
        else:
            bit_mapping.append({
                'name': item['name'],
                'addr': addr,
                'bit_pos': bit_pos,
                'enabled': False,
                'reason': 'out_of_range'
            })

    return mask_value, mask_bytes, bit_mapping


def detect_flash_address_gaps(
    enabled_items: List[Dict[str, Any]],
    base_addr: int,
    max_addr: int
) -> List[Tuple[int, int]]:
    """
    偵測 Flash 位址中的 Gap/Jump。

    規則:
    - 識別沒有表格的範圍
    - 這些 Gap 將填入 0xFF 填充

    Args:
        enabled_items: 已啟用的項目列表
        base_addr: 全域基址
        max_addr: 最大位址

    Returns:
        [(gap_start, gap_end), ...] - Gap 範圍列表 (絕對位址)

    Example:
        >>> items = [{'name': 'A', 'addr': 0x1000}, {'name': 'B', 'addr': 0x2000}]
        >>> gaps = detect_flash_address_gaps(items, 0x1000, 0x2000)
        >>> print(f"Found {len(gaps)} gap(s)")
    """
    try:
        base_addr = int(base_addr)
        max_addr = int(max_addr)
    except (ValueError, TypeError):
        return []

    if not enabled_items:
        return [(base_addr, max_addr + 255)]

    gaps = []
    try:
        sorted_items = sorted(enabled_items, key=lambda x: int(x['addr']))
    except (ValueError, TypeError, KeyError):
        return []

    # 檢查第一個表格前的 Gap
    try:
        first_addr = int(sorted_items[0]['addr'])
        if first_addr > base_addr:
            gaps.append((base_addr, first_addr - 256))
    except (ValueError, TypeError, KeyError, IndexError):
        pass

    # 檢查表格之間的 Gap
    for i in range(len(sorted_items) - 1):
        try:
            current_addr = int(sorted_items[i]['addr'])
            next_addr = int(sorted_items[i + 1]['addr'])
        except (ValueError, TypeError, KeyError):
            continue

        current_end = current_addr + 256

        if next_addr > current_end:
            # 在 current 結尾和 next 開始之間有 Gap
            gaps.append((current_end, next_addr - 256))

    return gaps


def format_mask_debug_info(
    enabled_items: List[Dict[str, Any]],
    base_addr: int
) -> str:
    """
    格式化 Mask 偵錯資訊。

    Args:
        enabled_items: 已啟用的項目列表
        base_addr: 全域基址

    Returns:
        格式化後的偵錯字串
    """
    if not enabled_items:
        return "No enabled items"

    max_addr = max(item['addr'] for item in enabled_items)
    mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
    mask_val, _, bit_mapping = calculate_enable_mask_with_gaps(enabled_items, base_addr)

    lines = [
        f"Base Address: 0x{base_addr:04X}",
        f"Max Address: 0x{max_addr:04X}",
        f"Total Bits: {total_bits}",
        f"Mask Bytes: {mask_bytes}",
        f"Enable Mask: 0x{mask_val:0{mask_bytes*2}X}",
        "",
        "Bit Mapping:",
    ]

    for m in bit_mapping:
        gap_note = ""
        lines.append(f"  Bit {m['bit_pos']:2d}: 0x{m['addr']:04X} - {m['name']}")

    return "\n".join(lines)


if __name__ == "__main__":
    # 簡單測試
    base_addr = 0x1000
    items = [
        {'name': 'Table_A', 'addr': 0x1000},
        {'name': 'Table_B', 'addr': 0x1300},
        {'name': 'Table_C', 'addr': 0x2000},
    ]

    print("=" * 50)
    print("Mask Calculator Test")
    print("=" * 50)

    # Test alignment
    print("\n[Test 1] Address Alignment:")
    test_cases = [
        (0x0500, "Flash < Base"),
        (0x1234, "Non-aligned"),
        (0x1500, "Aligned"),
    ]
    for addr, desc in test_cases:
        new_addr, adj, warn = validate_and_align_flash_address(addr, base_addr)
        mark = "✓" if not adj else "⚠"
        print(f"  {mark} {desc}: 0x{addr:04X} → 0x{new_addr:04X}")

    # Test mask calculation
    print("\n[Test 2] Mask Calculation:")
    mask, bytes_needed, mapping = calculate_enable_mask_with_gaps(items, base_addr)
    max_addr = max(i['addr'] for i in items)
    _, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
    print(f"  Max Address: 0x{max_addr:04X}")
    print(f"  Total Bits: {total_bits}")
    print(f"  Mask Bytes: {bytes_needed}")
    print(f"  Enable Mask: 0x{mask:0{bytes_needed*2}X}")

    # Test gap detection
    print("\n[Test 3] Gap Detection:")
    gaps = detect_flash_address_gaps(items, base_addr, max_addr)
    for i, (start, end) in enumerate(gaps, 1):
        blocks = (end - start) // 256 + 1
        print(f"  Gap #{i}: 0x{start:04X} ~ 0x{end:04X} ({blocks} blocks)")
