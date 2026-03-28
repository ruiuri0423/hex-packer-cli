"""
FirmwarePacker 整合測試
"""

import pytest
import tempfile
import os
from core.packer import FirmwarePacker


class TestFirmwarePacker:
    """FirmwarePacker 類別測試"""

    def test_init(self):
        """測試初始化"""
        packer = FirmwarePacker()
        assert packer.sections == []

    def test_add_section(self):
        """測試新增分區"""
        packer = FirmwarePacker()
        section = {
            'name': 'TEST',
            'max_len': 1024,
            'file_path': '',
            'is_full': True,
            'calc_addr': 0
        }
        packer.add_section(section)
        assert len(packer.sections) == 1
        assert packer.sections[0]['name'] == 'TEST'

    def test_remove_section(self):
        """測試移除分區"""
        packer = FirmwarePacker()
        packer.add_section({'name': 'A', 'max_len': 100})
        packer.add_section({'name': 'B', 'max_len': 200})
        
        assert len(packer.sections) == 2
        assert packer.remove_section(0) is True
        assert len(packer.sections) == 1
        assert packer.sections[0]['name'] == 'B'

    def test_get_section(self):
        """測試取得分區"""
        packer = FirmwarePacker()
        packer.add_section({'name': 'TEST', 'max_len': 1024})
        
        section = packer.get_section(0)
        assert section is not None
        assert section['name'] == 'TEST'
        
        # 取得不存在的分區
        assert packer.get_section(99) is None

    def test_calculate_addresses(self):
        """測試位址計算"""
        packer = FirmwarePacker()
        packer.add_section({'name': 'A', 'max_len': 100, 'calc_addr': 0})
        packer.add_section({'name': 'B', 'max_len': 200, 'calc_addr': 0})
        packer.add_section({'name': 'C', 'max_len': 300, 'calc_addr': 0})
        
        packer.calculate_addresses()
        
        assert packer.sections[0]['calc_addr'] == 0
        assert packer.sections[1]['calc_addr'] == 100
        assert packer.sections[2]['calc_addr'] == 300  # 100 + 200


class TestFirmwarePackerCSV:
    """CSV 配置測試"""

    def test_save_and_load_config(self):
        """測試 CSV 儲存和載入"""
        packer = FirmwarePacker()
        packer.add_section({
            'name': 'HEADER',
            'max_len': 256,
            'file_path': '',
            'is_full': True,
            'inject_err': False,
            'target_sec': '',
            'size_offset': '',
            'size_offset_orig': '',
            'en_offset': '',
            'en_offset_orig': '',
            'en_bit': '',
            'en_val': 1,
            'crc_offset': '',
            'crc_offset_orig': '',
            'crc_bit': '',
            'crc_val': 1,
            'addr_offset': '',
            'addr_offset_orig': '',
            'mask_target': '',
            'mask_offset': '',
            'mask_offset_orig': '',
            'mask_val': 0,
            'calc_addr': 0,
            'bypass_crc': False
        })
        
        # 建立臨時檔案
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            csv_path = f.name
        
        try:
            # 儲存
            success, msg = packer.save_csv_config(csv_path)
            assert success is True
            
            # 載入到新的 packer
            packer2 = FirmwarePacker()
            success2, msg2 = packer2.load_csv_config(csv_path)
            assert success2 is True
            assert len(packer2.sections) == 1
            assert packer2.sections[0]['name'] == 'HEADER'
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)


class TestFirmwarePackerHEXGeneration:
    """HEX 生成測試"""

    def test_generate_firmware_empty(self):
        """測試空分區列表"""
        packer = FirmwarePacker()
        success, msg = packer.generate_firmware_hex("/tmp/test.hex")
        assert success is False
        assert "empty" in msg.lower()

    def test_generate_firmware_with_random_data(self):
        """測試使用隨機資料生成"""
        packer = FirmwarePacker()
        packer.add_section({
            'name': 'TEST',
            'max_len': 100,
            'file_path': '',  # 空路徑會生成隨機資料
            'is_full': True,
            'inject_err': False,
            'target_sec': '',
            'size_offset': '',
            'size_offset_orig': '',
            'en_offset': '',
            'en_offset_orig': '',
            'en_bit': '',
            'en_val': 1,
            'crc_offset': '',
            'crc_offset_orig': '',
            'crc_bit': '',
            'crc_val': 1,
            'addr_offset': '',
            'addr_offset_orig': '',
            'mask_target': '',
            'mask_offset': '',
            'mask_offset_orig': '',
            'mask_val': 0,
            'calc_addr': 0,
            'bypass_crc': False
        })
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            hex_path = f.name
        
        try:
            success, msg = packer.generate_firmware_hex(hex_path)
            assert success is True
            
            # 驗證檔案內容
            with open(hex_path, 'r') as f:
                lines = f.readlines()
            # 應該有 100 行 (max_len)
            assert len(lines) == 100
        finally:
            if os.path.exists(hex_path):
                os.remove(hex_path)


class TestFirmwarePackerMaskInjection:
    """Mask 注入測試"""

    def test_mask_calculation(self):
        """測試 Mask 計算"""
        packer = FirmwarePacker()
        packer.add_section({
            'name': 'MASK_TARGET',
            'max_len': 100,
            'file_path': '',
            'is_full': True,
            'inject_err': False,
            'target_sec': '',
            'size_offset': '',
            'size_offset_orig': '',
            'en_offset': '',
            'en_offset_orig': '',
            'en_bit': '',
            'en_val': 1,
            'crc_offset': '',
            'crc_offset_orig': '',
            'crc_bit': '',
            'crc_val': 1,
            'addr_offset': '',
            'addr_offset_orig': '',
            'mask_target': '',  # 無 mask target
            'mask_offset': '',
            'mask_offset_orig': '',
            'mask_val': 0x0103,  # Bit 0, 1, 8 = 1
            'calc_addr': 0,
            'bypass_crc': False
        })
        
        # 計算位址
        packer.calculate_addresses()
        
        # 驗證 mask_val 為 0x0103 (二進位: 00000001 00000011)
        assert packer.sections[0]['mask_val'] == 0x0103


class TestFirmwarePackerBypassCRC:
    """Bypass CRC 測試"""

    def test_bypass_crc(self):
        """測試 CRC 繞過"""
        packer = FirmwarePacker()
        packer.add_section({
            'name': 'TEST',
            'max_len': 100,
            'file_path': '',
            'is_full': True,
            'inject_err': False,
            'target_sec': '',
            'size_offset': '',
            'size_offset_orig': '',
            'en_offset': '',
            'en_offset_orig': '',
            'en_bit': '',
            'en_val': 1,
            'crc_offset': '',
            'crc_offset_orig': '',
            'crc_bit': '',
            'crc_val': 1,
            'addr_offset': '',
            'addr_offset_orig': '',
            'mask_target': '',
            'mask_offset': '',
            'mask_offset_orig': '',
            'mask_val': 0,
            'calc_addr': 0,
            'bypass_crc': True  # 繞過 CRC
        })
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            hex_path = f.name
        
        try:
            success, msg = packer.generate_firmware_hex(hex_path)
            assert success is True
            
            # 讀取並驗證 - 最後兩位不應該是 CRC
            with open(hex_path, 'r') as f:
                lines = f.readlines()
            
            # bypass_crc = True 時，最後兩位不應該是 CRC 計算結果
            # 應該保持為原始值 (0xFF)
            assert len(lines) == 100
        finally:
            if os.path.exists(hex_path):
                os.remove(hex_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
