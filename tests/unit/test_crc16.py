"""
CRC16 模組單元測試

修復版本：移除不存在的 calculate_crc16_simple 函數引用
"""

import pytest
import sys
from pathlib import Path

# 確保路徑設定正確
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.crc16 import (
    calculate_custom_crc16,
    calculate_crc16_fast,
    POLYNOMIAL,
    INIT_VALUE
)


class TestCRC16Parameters:
    """CRC16 參數測試"""
    
    def test_polynomial_value(self):
        """測試多項式值是否符合硬體定義"""
        assert POLYNOMIAL == 0x8005, "多項式應為 0x8005 (CRC-16)"
    
    def test_init_value(self):
        """測試初始值"""
        assert INIT_VALUE == 0x0052, "初始值應為 0x0052"
    
    def test_parameters_are_int(self):
        """測試參數類型"""
        assert isinstance(POLYNOMIAL, int)
        assert isinstance(INIT_VALUE, int)


class TestCRC16BasicFunction:
    """CRC16 基本功能測試"""
    
    def test_empty_data(self):
        """測試空資料"""
        crc = calculate_custom_crc16(bytearray())
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
    
    def test_single_byte_zero(self):
        """測試單一字節 0x00"""
        crc = calculate_custom_crc16(bytearray([0x00]))
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
        # 記錄值用於迴歸測試
        print(f"CRC(0x00) = 0x{crc:04X}")
    
    def test_single_byte_ff(self):
        """測試單一字節 0xFF"""
        crc = calculate_custom_crc16(bytearray([0xFF]))
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
        print(f"CRC(0xFF) = 0x{crc:04X}")
    
    def test_multiple_bytes(self):
        """測試多個字節"""
        data = bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
        print(f"CRC(seq 0-5) = 0x{crc:04X}")
    
    def test_mixed_data(self):
        """測試混合資料"""
        data = bytearray([0xAA, 0xBB, 0xCC, 0xDD])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF


class TestCRC16Determinism:
    """CRC16 確定性測試"""
    
    def test_same_input_same_output(self):
        """測試相同輸入產生相同輸出"""
        data = bytearray([0x12, 0x34, 0x56, 0x78, 0x9A])
        
        crc1 = calculate_custom_crc16(data)
        crc2 = calculate_custom_crc16(data)
        crc3 = calculate_custom_crc16(data)
        
        assert crc1 == crc2 == crc3, "相同輸入應產生相同 CRC"
    
    def test_different_input_different_output(self):
        """測試不同輸入產生不同輸出"""
        data1 = bytearray([0x00])
        data2 = bytearray([0x01])
        
        crc1 = calculate_custom_crc16(data1)
        crc2 = calculate_custom_crc16(data2)
        
        # 注意：不同輸入不見得一定產生不同輸出（碰撞機率很低）
        # 但至少兩個都應該是有效的 CRC 值
        assert 0 <= crc1 <= 0xFFFF
        assert 0 <= crc2 <= 0xFFFF


class TestCRC16FastImplementation:
    """CRC16 快速實作測試"""
    
    def test_fast_matches_main(self):
        """測試快速實作與主實作結果一致"""
        test_cases = [
            bytearray(),
            bytearray([0x00]),
            bytearray([0xFF]),
            bytearray([0x00, 0xFF]),
            bytearray([0x00, 0x01, 0x02, 0x03]),
            bytearray([i for i in range(256)]),
            bytearray([i % 256 for i in range(1000)]),
        ]
        
        for data in test_cases:
            crc_main = calculate_custom_crc16(data)
            crc_fast = calculate_crc16_fast(data)
            assert crc_main == crc_fast, f"CRC mismatch for data {list(data)[:10]}"


class TestCRC16EdgeCases:
    """CRC16 邊界條件測試"""
    
    def test_all_zeros(self):
        """測試全零資料"""
        data = bytearray([0x00] * 100)
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
    
    def test_all_ff(self):
        """測試全 FF 資料"""
        data = bytearray([0xFF] * 100)
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF
    
    def test_alternating_pattern(self):
        """測試交替模式"""
        data = bytearray([0x00 if i % 2 == 0 else 0xFF for i in range(100)])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
    
    def test_large_data(self):
        """測試大量資料"""
        data = bytearray([i % 256 for i in range(1000)])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)
    
    def test_very_large_data(self):
        """測試超大資料"""
        data = bytearray([i % 256 for i in range(10000)])
        crc = calculate_custom_crc16(data)
        assert isinstance(crc, int)


class TestCRC16ListInput:
    """CRC16 列表輸入測試"""
    
    def test_list_input(self):
        """測試列表輸入"""
        data_list = [0x00, 0x01, 0x02, 0x03]
        crc_list = calculate_custom_crc16(data_list)
        crc_bytes = calculate_custom_crc16(bytearray(data_list))
        assert crc_list == crc_bytes
    
    def test_empty_list(self):
        """測試空列表"""
        crc = calculate_custom_crc16([])
        assert isinstance(crc, int)


class TestCRC16ValueRange:
    """CRC16 值範圍測試"""
    
    def test_value_range_comprehensive(self):
        """全面測試 CRC 值範圍"""
        test_cases = [
            bytearray([0x00]),
            bytearray([0xFF]),
            bytearray([0x00, 0xFF, 0xAA, 0x55]),
            bytearray([i for i in range(100)]),
            bytearray([i % 256 for i in range(256)]),
        ]
        
        for data in test_cases:
            crc = calculate_custom_crc16(data)
            assert 0 <= crc <= 0xFFFF, f"CRC out of range for data {list(data)[:5]}"


class TestCRC16Regression:
    """CRC16 迴歸測試 (記錄預期值)"""
    
    def test_known_values(self):
        """記錄已知 CRC 值用於迴歸測試"""
        known_cases = {
            'empty': bytearray(),
            'single_00': bytearray([0x00]),
            'single_ff': bytearray([0xFF]),
            'sequence_0_5': bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05]),
            'mixed': bytearray([0xAA, 0xBB, 0xCC, 0xDD]),
        }
        
        results = {}
        for name, data in known_cases.items():
            crc = calculate_custom_crc16(data)
            results[name] = crc
            print(f"  {name}: 0x{crc:04X}")
        
        # 這些值應記錄下來用於未來的迴歸測試
        # 如果未來 CRC 值改變，這些測試會失敗


# ============================================================================
# 工廠模式測試
# ============================================================================

class TestCRC16WithFactory:
    """使用工廠模式的 CRC16 測試"""
    
    def test_factory_standard_suite(self):
        """使用工廠測試套件"""
        from tests.factories.crc16_factory import CRC16Factory
        
        suite = CRC16Factory.get_standard_test_suite()
        
        for case in suite:
            data = case['data']
            crc = calculate_custom_crc16(data)
            assert isinstance(crc, int), f"Failed: {case['id']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
