"""
HEX Parser 模組單元測試
"""

import pytest
import tempfile
import os
from core.hex_parser import (
    parse_hex_address,
    parse_m0_hex_file,
    write_hex_file,
    read_hex_file,
    hex_to_hex_string
)


class TestParseHexAddress:
    """HEX 位址解析測試"""

    def test_h_prefix(self):
        """測試 h 前綴"""
        assert parse_hex_address("h00FF") == 0x00FF
        assert parse_hex_address("hFF") == 0xFF
        assert parse_hex_address("h1234") == 0x1234

    def test_0x_prefix(self):
        """測試 0x 前綴"""
        assert parse_hex_address("0xFF") == 0xFF
        assert parse_hex_address("0x1234") == 0x1234
        assert parse_hex_address("0xABCD") == 0xABCD

    def test_no_prefix(self):
        """測試無前綴"""
        assert parse_hex_address("FF") == 0xFF
        assert parse_hex_address("1234") == 0x1234
        assert parse_hex_address("ABCD") == 0xABCD

    def test_lowercase(self):
        """測試小寫"""
        assert parse_hex_address("hff") == 0xFF
        assert parse_hex_address("0xff") == 0xFF
        assert parse_hex_address("abcd") == 0xABCD

    def test_uppercase(self):
        """測試大寫"""
        assert parse_hex_address("hFF") == 0xFF
        assert parse_hex_address("0xFF") == 0xFF
        assert parse_hex_address("ABCD") == 0xABCD

    def test_with_whitespace(self):
        """測試空白字元"""
        assert parse_hex_address("  hFF  ") == 0xFF
        assert parse_hex_address("  0xFF  ") == 0xFF
        assert parse_hex_address("  FF  ") == 0xFF

    def test_integer_input(self):
        """測試整數輸入"""
        assert parse_hex_address(255) == 255
        assert parse_hex_address(0x1234) == 0x1234

    def test_invalid_input(self):
        """測試無效輸入"""
        assert parse_hex_address("") == -1
        assert parse_hex_address("invalid") == -1
        assert parse_hex_address("xyz") == -1


class TestWriteHexFile:
    """HEX 檔案寫入測試"""

    def test_write_empty_file(self):
        """測試寫入空檔案"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            filepath = f.name

        try:
            success = write_hex_file(filepath, bytearray())
            assert success is True

            with open(filepath, 'r') as f:
                content = f.read()
            assert content == ""
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_write_single_byte(self):
        """測試寫入單一字節"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            filepath = f.name

        try:
            success = write_hex_file(filepath, bytearray([0xFF]))
            assert success is True

            with open(filepath, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 1
            assert lines[0].strip() == "FF"
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_write_multiple_bytes(self):
        """測試寫入多個字節"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            filepath = f.name

        try:
            data = bytearray([0x00, 0x01, 0xFF, 0xAB, 0xCD])
            success = write_hex_file(filepath, data)
            assert success is True

            with open(filepath, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 5
            assert lines[0].strip() == "00"
            assert lines[1].strip() == "01"
            assert lines[2].strip() == "FF"
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestParseRawHexFile:
    """原始 HEX 檔案解析測試"""

    def test_parse_single_line(self):
        """測試解析單行"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            f.write("00 01 02 03 04")
            filepath = f.name

        try:
            success, buf, size = parse_m0_hex_file(filepath)
            assert success is True
            assert len(buf) == 5
            assert buf[0] == 0x00
            assert buf[4] == 0x04
            assert size == 5
        finally:
            os.remove(filepath)

    def test_parse_multiple_lines(self):
        """測試解析多行"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            f.write("00 01 02\n")
            f.write("03 04 05\n")
            f.write("06 07 08")
            filepath = f.name

        try:
            success, buf, size = parse_m0_hex_file(filepath)
            assert success is True
            assert len(buf) == 9
            assert size == 9
        finally:
            os.remove(filepath)

    def test_parse_empty_file(self):
        """測試解析空檔案"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            filepath = f.name

        try:
            success, buf, size = parse_m0_hex_file(filepath)
            assert success is True
            assert len(buf) == 0
            assert size == 0
        finally:
            os.remove(filepath)

    def test_parse_with_spaces(self):
        """測試解析帶多餘空白的檔案"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            f.write("  00  01  02  ")
            filepath = f.name

        try:
            success, buf, size = parse_m0_hex_file(filepath)
            assert success is True
            assert len(buf) == 3
        finally:
            os.remove(filepath)


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
        """測試全範圍"""
        data = bytearray([i for i in range(256)])
        result = hex_to_hex_string(data)
        lines = result.split('\n')
        assert len(lines) == 16  # 256 / 16 = 16 lines


class TestRoundTrip:
    """來回轉換測試"""

    def test_write_and_parse(self):
        """測試寫入後解析"""
        original_data = bytearray([0x00, 0x01, 0x02, 0x03, 0xFF, 0xAB, 0xCD])

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            filepath = f.name

        try:
            # 寫入
            write_hex_file(filepath, original_data)

            # 讀取
            success, buf, size = parse_m0_hex_file(filepath)

            assert success is True
            assert len(buf) == len(original_data)
            assert buf == original_data
        finally:
            os.remove(filepath)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
