"""
Mask Calculator 模組單元測試
"""

import pytest
from core.mask_calculator import (
    validate_and_align_flash_address,
    calculate_dynamic_mask_bytes,
    calculate_enable_mask_with_gaps,
    detect_flash_address_gaps,
    format_mask_debug_info
)


class TestValidateAndAlignFlashAddress:
    """Flash 位址對齊測試"""

    def test_address_below_base(self):
        """測試 Flash 位址低於 Base 的情況"""
        item_addr = 0x0500
        base_addr = 0x1000

        result_addr, was_adjusted, warning = validate_and_align_flash_address(
            item_addr, base_addr
        )

        assert was_adjusted is True
        assert result_addr == base_addr

    def test_address_above_base(self):
        """測試 Flash 位址高於 Base 的情況"""
        item_addr = 0x1500
        base_addr = 0x1000

        result_addr, was_adjusted, warning = validate_and_align_flash_address(
            item_addr, base_addr
        )

        assert was_adjusted is False
        assert result_addr == item_addr

    def test_non_aligned_address(self):
        """測試非對齊位址"""
        item_addr = 0x1234
        base_addr = 0x1000

        result_addr, was_adjusted, warning = validate_and_align_flash_address(
            item_addr, base_addr
        )

        assert was_adjusted is True
        assert result_addr == 0x1200  # 對齊到 256 boundary

    def test_aligned_address(self):
        """測試已對齊的位址"""
        item_addr = 0x1000
        base_addr = 0x1000

        result_addr, was_adjusted, warning = validate_and_align_flash_address(
            item_addr, base_addr
        )

        assert was_adjusted is False
        assert result_addr == item_addr

    def test_aligned_at_256_boundary(self):
        """測試恰好在 256 邊界的位址"""
        item_addr = 0x1100
        base_addr = 0x1000

        result_addr, was_adjusted, warning = validate_and_align_flash_address(
            item_addr, base_addr
        )

        assert was_adjusted is False
        assert result_addr == item_addr

    def test_string_input(self):
        """測試字串輸入"""
        item_addr = "0x1234"
        base_addr = "0x1000"

        result_addr, was_adjusted, warning = validate_and_align_flash_address(
            item_addr, base_addr
        )

        assert result_addr == 0x1200
        assert was_adjusted is True


class TestCalculateDynamicMaskBytes:
    """動態 Mask 位元組計算測試"""

    def test_basic_calculation(self):
        """測試基本計算"""
        max_addr = 0x2000
        base_addr = 0x1000

        bytes_needed, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)

        # 0x2000 - 0x1000 = 0x1000 = 4096 bytes = 16 * 256
        # 所以需要 17 bits
        assert total_bits == 17
        assert bytes_needed == 3  # (17 + 7) // 8 = 3

    def test_single_table(self):
        """測試單一表格"""
        max_addr = 0x1000
        base_addr = 0x1000

        bytes_needed, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)

        assert total_bits == 1
        assert bytes_needed == 1

    def test_max_equals_base(self):
        """測試最大位址等於 Base"""
        max_addr = 0x1000
        base_addr = 0x1000

        bytes_needed, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)

        assert total_bits == 0
        assert bytes_needed == 1

    def test_max_less_than_base(self):
        """測試最大位址小於 Base"""
        max_addr = 0x0FFF
        base_addr = 0x1000

        bytes_needed, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)

        assert total_bits == 0
        assert bytes_needed == 1

    def test_256_byte_increment(self):
        """測試 256 位元組遞增"""
        base_addr = 0x1000

        for i in range(1, 10):
            max_addr = base_addr + (i * 256)
            _, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
            assert total_bits == i + 1


class TestCalculateEnableMaskWithGaps:
    """Enable Mask 計算測試"""

    def test_empty_items(self):
        """測試空列表"""
        mask, bytes_needed, mapping = calculate_enable_mask_with_gaps([], 0x1000)

        assert mask == 0
        assert bytes_needed == 1
        assert len(mapping) == 0

    def test_single_table(self):
        """測試單一表格"""
        items = [{'name': 'Table_A', 'addr': 0x1000}]
        base_addr = 0x1000

        mask, bytes_needed, mapping = calculate_enable_mask_with_gaps(items, base_addr)

        assert mask == 0b1  # Bit 0 = 1
        assert bytes_needed == 1
        assert len(mapping) == 1
        assert mapping[0]['bit_pos'] == 0

    def test_multiple_tables(self):
        """測試多個表格"""
        items = [
            {'name': 'Table_A', 'addr': 0x1000},
            {'name': 'Table_B', 'addr': 0x1100},
            {'name': 'Table_C', 'addr': 0x1200},
        ]
        base_addr = 0x1000

        mask, bytes_needed, mapping = calculate_enable_mask_with_gaps(items, base_addr)

        # Bit 0, 1, 2 為 1
        assert mask == 0b111  # 7
        assert bytes_needed == 1
        assert len(mapping) == 3

    def test_with_gaps(self):
        """測試有 Gap 的情況"""
        items = [
            {'name': 'Table_A', 'addr': 0x1000},  # Bit 0
            {'name': 'Table_B', 'addr': 0x2000},  # Bit 16 (有 Gap)
        ]
        base_addr = 0x1000

        mask, bytes_needed, mapping = calculate_enable_mask_with_gaps(items, base_addr)

        # Bit 0 和 Bit 16 為 1，中間為 0
        expected_mask = (1 << 0) | (1 << 16)
        assert mask == expected_mask

    def test_out_of_range(self):
        """測試超出範圍"""
        items = [
            {'name': 'Table_A', 'addr': 0x1000},
            {'name': 'Table_B', 'addr': 0xFFFF},  # 可能超出
        ]
        base_addr = 0x1000

        mask, bytes_needed, mapping = calculate_enable_mask_with_gaps(items, base_addr)

        # 應該正常處理
        assert isinstance(mask, int)
        assert bytes_needed >= 1


class TestDetectFlashAddressGaps:
    """Gap 偵測測試"""

    def test_no_gaps(self):
        """測試無 Gap 的情況"""
        items = [
            {'name': 'Table_A', 'addr': 0x1000},
            {'name': 'Table_B', 'addr': 0x1100},
        ]
        base_addr = 0x1000
        max_addr = 0x1200

        gaps = detect_flash_address_gaps(items, base_addr, max_addr)

        # 應該只有一個 gap (結尾到 max)
        assert len(gaps) >= 1

    def test_with_gaps(self):
        """測試有 Gap 的情況"""
        items = [
            {'name': 'Table_A', 'addr': 0x1000},
            {'name': 'Table_B', 'addr': 0x2000},
        ]
        base_addr = 0x1000
        max_addr = 0x2000

        gaps = detect_flash_address_gaps(items, base_addr, max_addr)

        # 應該有一個 gap
        assert len(gaps) >= 1

    def test_empty_items(self):
        """測試空列表"""
        gaps = detect_flash_address_gaps([], 0x1000, 0x2000)

        assert len(gaps) == 1
        assert gaps[0] == (0x1000, 0x20FF)  # 整個範圍

    def test_first_table_not_at_base(self):
        """測試第一個表格不在 Base"""
        items = [
            {'name': 'Table_A', 'addr': 0x1200},
        ]
        base_addr = 0x1000
        max_addr = 0x1200

        gaps = detect_flash_address_gaps(items, base_addr, max_addr)

        # 應該有 gap 從 base 到第一個表格
        assert len(gaps) >= 1


class TestFormatMaskDebugInfo:
    """Mask 偵錯資訊格式化測試"""

    def test_empty_items(self):
        """測試空列表"""
        info = format_mask_debug_info([], 0x1000)
        assert "No enabled items" in info

    def test_with_items(self):
        """測試有項目的情況"""
        items = [
            {'name': 'Table_A', 'addr': 0x1000},
            {'name': 'Table_B', 'addr': 0x1100},
        ]
        base_addr = 0x1000

        info = format_mask_debug_info(items, base_addr)

        assert "Base Address: 0x1000" in info
        assert "Max Address: 0x1100" in info
        assert "Enable Mask:" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
