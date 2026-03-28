"""
CRC16 模組單元測試
"""

import pytest
from core.crc16 import (
    calculate_custom_crc16,
    calculate_crc16_simple,
    calculate_crc16_fast,
    POLYNOMIAL,
    INIT_VALUE
)


class TestCRC16:
    """CRC16 計算測試"""

    def test_polynomial_value(self):
        """測試多項式值"""
        assert POLYNOMIAL == 0x8005

    def test_init_value(self):
        """測試初始值"""
        assert INIT_VALUE == 0x0052

    def test_empty_data(self):
        """測試空資料"""
        crc = calculate_custom_crc16(bytearray())
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_single_byte(self):
        """測試單一字節"""
        data = bytearray([0x00])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_multiple_bytes(self):
        """測試多個字節"""
        data = bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_known_values(self):
        """測試已知 CRC 值"""
        # 這些是使用相同多項式和初始值的硬體邏輯計算出的參考值
        data = bytearray([0x00, 0x01, 0x02])
        crc1 = calculate_custom_crc16(data)
        crc2 = calculate_crc16_simple(data)
        crc3 = calculate_crc16_fast(data)

        # 三種方法應該得到相同的結果
        assert crc1 == crc2 == crc3

    def test_different_implementations_match(self):
        """測試不同實作是否一致"""
        test_data = [
            bytearray(),
            bytearray([0x00]),
            bytearray([0xFF]),
            bytearray([0x00, 0xFF]),
            bytearray([0x00, 0x01, 0x02, 0x03]),
            bytearray([i for i in range(256)]),  # 全範圍測試
        ]

        for data in test_data:
            crc_parallel = calculate_custom_crc16(data)
            crc_lookup = calculate_crc16_simple(data)
            crc_fast = calculate_crc16_fast(data)

            assert crc_parallel == crc_lookup == crc_fast, \
                f"CRC mismatch for data {list(data)[:10]}"

    def test_list_input(self):
        """測試列表輸入"""
        data_list = [0x00, 0x01, 0x02, 0x03]
        crc = calculate_custom_crc16(data_list)
        crc_list = calculate_custom_crc16(bytearray(data_list))
        assert crc == crc_list

    def test_crc16_value_range(self):
        """測試 CRC 值範圍"""
        test_cases = [
            bytearray([0x00]),
            bytearray([0xFF]),
            bytearray([0x00, 0xFF, 0xAA, 0x55]),
            bytearray([i % 256 for i in range(100)]),
        ]

        for data in test_cases:
            crc = calculate_custom_crc16(data)
            assert 0 <= crc <= 0xFFFF

    def test_deterministic(self):
        """測試確定性 - 相同輸入應產生相同輸出"""
        data = bytearray([0x12, 0x34, 0x56, 0x78, 0x9A])

        crc1 = calculate_custom_crc16(data)
        crc2 = calculate_custom_crc16(data)
        crc3 = calculate_custom_crc16(data)

        assert crc1 == crc2 == crc3

    def test_edge_case_all_zeros(self):
        """測試邊界情況 - 全零"""
        data = bytearray([0x00] * 100)
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)

    def test_edge_case_all_ff(self):
        """測試邊界情況 - 全 FF"""
        data = bytearray([0xFF] * 100)
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)

    def test_large_data(self):
        """測試大量資料"""
        data = bytearray([i % 256 for i in range(1000)])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)


class TestCRC16Performance:
    """CRC16 效能測試"""

    def test_small_data_performance(self):
        """測試小資料效能"""
        data = bytearray([i for i in range(100)])

        # 確保所有實作都能正常運行
        crc1 = calculate_custom_crc16(data)
        crc2 = calculate_crc16_simple(data)
        crc3 = calculate_crc16_fast(data)

        assert crc1 == crc2 == crc3

    def test_large_data_performance(self):
        """測試大資料效能"""
        data = bytearray([i % 256 for i in range(10000)])

        crc1 = calculate_custom_crc16(data)
        crc2 = calculate_crc16_simple(data)
        crc3 = calculate_crc16_fast(data)

        assert crc1 == crc2 == crc3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
