"""
HEX Parser 模組單元測試
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.hex_parser import (
    parse_hex_address,
    parse_m0_hex_file,
    write_hex_file,
    read_hex_file,
    hex_to_hex_string
)


class TestParseHexAddress:
    """HEX 位址解析測試"""
    
    @pytest.mark.parametrize("input_val,expected", [
        ('h00FF', 0x00FF),
        ('hFF', 0xFF),
        ('h1234', 0x1234),
        ('0xFF', 0xFF),
        ('0x1234', 0x1234),
        ('0xABCD', 0xABCD),
        ('FF', 0xFF),
        ('1234', 0x1234),
        ('ABCD', 0xABCD),
        ('abcd', 0xABCD),
        (255, 255),
        (0x1234, 0x1234),
    ])
    def test_valid_addresses(self, input_val, expected):
        """測試有效位址解析"""
        result = parse_hex_address(input_val)
        assert result == expected
    
    @pytest.mark.parametrize("input_val,expected", [
        ('', -1),
        ('invalid', -1),
        ('xyz', -1),
        ('GG', -1),
    ])
    def test_invalid_addresses(self, input_val, expected):
        """測試無效位址解析"""
        result = parse_hex_address(input_val)
        assert result == expected
    
    def test_whitespace_handling(self):
        """測試空白處理"""
        assert parse_hex_address('  hFF  ') == 0xFF
        assert parse_hex_address('  0xFF  ') == 0xFF
        assert parse_hex_address('  FF  ') == 0xFF


class TestWriteHexFile:
    """HEX 檔案寫入測試"""
    
    def test_write_empty_file(self, temp_hex_file):
        """測試寫入空檔案"""
        success = write_hex_file(temp_hex_file, bytearray())
        assert success is True
        
        with open(temp_hex_file, 'r') as f:
            content = f.read()
        assert content == ""
    
    def test_write_single_byte(self, temp_hex_file):
        """測試寫入單一字節"""
        success = write_hex_file(temp_hex_file, bytearray([0xFF]))
        assert success is True
        
        with open(temp_hex_file, 'r') as f:
            content = f.read().strip()
        assert content == "FF"
    
    def test_write_multiple_bytes(self, temp_hex_file):
        """測試寫入多個字節"""
        data = bytearray([0x00, 0x01, 0xFF, 0xAB, 0xCD])
        success = write_hex_file(temp_hex_file, data)
        assert success is True
        
        with open(temp_hex_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 5
        assert lines[0].strip() == "00"
        assert lines[2].strip() == "FF"
    
    def test_write_invalid_path(self):
        """測試無效路徑"""
        success = write_hex_file('/nonexistent/directory/file.hex', bytearray([0x00]))
        assert success is False


class TestParseRawHexFile:
    """原始 HEX 檔案解析測試"""
    
    def test_parse_single_line(self, temp_hex_file):
        """測試解析單行"""
        with open(temp_hex_file, 'w') as f:
            f.write("00 01 02 03 04\n")
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success is True
        assert len(buf) == 5
        assert buf[0] == 0x00
        assert buf[4] == 0x04
        assert size == 5
    
    def test_parse_multiple_lines(self, temp_hex_file):
        """測試解析多行"""
        with open(temp_hex_file, 'w') as f:
            f.write("00 01 02\n")
            f.write("03 04 05\n")
            f.write("06 07 08\n")
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success is True
        assert len(buf) == 9
        assert size == 9
    
    def test_parse_empty_file(self, temp_hex_file):
        """測試解析空檔案"""
        with open(temp_hex_file, 'w') as f:
            pass
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success is True
        assert len(buf) == 0
        assert size == 0
    
    def test_parse_with_extra_spaces(self, temp_hex_file):
        """測試解析帶多餘空白的檔案"""
        with open(temp_hex_file, 'w') as f:
            f.write("  00  01  02  \n")
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success is True
        assert len(buf) == 3


class TestParseIntelHexFile:
    """Intel HEX 格式解析測試"""
    
    def test_parse_simple_intel_hex(self, temp_hex_file):
        """測試解析簡單 Intel HEX"""
        # :06 0000 00 010203040506 FC
        # 06 = 6 bytes
        # 0000 = address
        # 00 = data record
        # 010203040506 = data
        # FC = checksum
        with open(temp_hex_file, 'w') as f:
            f.write(":06000000010203040506FC\n")
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success is True
        assert len(buf) >= 6
    
    def test_parse_intel_hex_with_extended_address(self, temp_hex_file):
        """測試解析帶擴展位址的 Intel HEX"""
        with open(temp_hex_file, 'w') as f:
            # Extended Linear Address
            f.write(":020000040800E2\n")  # Base address = 0x08000000
            # Data at 0x08000000
            f.write(":06000000AABBCCDDEE\n")
            # End of file
            f.write(":00000001FF\n")
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success is True


class TestHexToHexString:
    """HEX 字串格式化測試"""
    
    def test_empty_data(self):
        """測試空資料"""
        result = hex_to_hex_string(bytearray())
        assert result == ""
    
    def test_single_byte(self):
        """測試單一字節"""
        result = hex_to_hex_string(bytearray([0x00]))
        assert "0000: 00" in result
    
    def test_multiple_bytes(self):
        """測試多個字節"""
        data = bytearray([0x00, 0x01, 0x02, 0x03])
        result = hex_to_hex_string(data)
        assert "0000: 00 01 02 03" in result
    
    def test_bytes_per_line(self):
        """測試每行位元組數"""
        data = bytearray([i for i in range(20)])
        result = hex_to_hex_string(data, bytes_per_line=10)
        lines = result.split('\n')
        assert len(lines) == 2
    
    def test_full_range(self):
        """測試全範圍 (256 bytes)"""
        data = bytearray([i for i in range(256)])
        result = hex_to_hex_string(data)
        lines = result.split('\n')
        assert len(lines) == 16  # 256 / 16 = 16 lines


class TestRoundTrip:
    """來回轉換測試"""
    
    def test_write_and_parse_raw(self, temp_hex_file):
        """測試 Raw HEX 寫入後解析"""
        original_data = bytearray([0x00, 0x01, 0x02, 0x03, 0xFF, 0xAB, 0xCD])
        
        # 寫入
        write_hex_file(temp_hex_file, original_data)
        
        # 解析
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        
        assert success is True
        assert len(buf) == len(original_data)
        assert buf == original_data


class TestReadHexFile:
    """HEX 檔案讀取測試"""
    
    def test_read_valid_file(self, temp_hex_file):
        """測試讀取有效檔案"""
        data = bytearray([0x00, 0x01, 0x02])
        write_hex_file(temp_hex_file, data)
        
        success, buf, error = read_hex_file(temp_hex_file)
        assert success is True
        assert buf == data
    
    def test_read_nonexistent_file(self):
        """測試讀取不存在的檔案"""
        success, buf, error = read_hex_file('/nonexistent/file.hex')
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
