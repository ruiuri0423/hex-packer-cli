"""
FirmwarePacker 模組單元測試
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.packer import FirmwarePacker


class TestFirmwarePackerInit:
    """FirmwarePacker 初始化測試"""
    
    def test_init(self):
        """測試初始化"""
        packer = FirmwarePacker()
        assert packer.sections == []
    
    def test_multiple_init(self):
        """測試多次初始化"""
        packer1 = FirmwarePacker()
        packer2 = FirmwarePacker()
        assert packer1.sections == []
        assert packer2.sections == []


class TestFirmwarePackerSections:
    """FirmwarePacker 分區管理測試"""
    
    def test_add_section(self, minimal_section):
        """測試新增分區"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section)
        assert len(packer.sections) == 1
        assert packer.sections[0]['name'] == minimal_section['name']
    
    def test_add_multiple_sections(self, minimal_section):
        """測試新增多個分區"""
        packer = FirmwarePacker()
        
        section1 = minimal_section.copy()
        section1['name'] = 'A'
        
        section2 = minimal_section.copy()
        section2['name'] = 'B'
        
        packer.add_section(section1)
        packer.add_section(section2)
        
        assert len(packer.sections) == 2
    
    def test_remove_section(self, minimal_section):
        """測試移除分區"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section.copy())
        packer.add_section(minimal_section.copy())
        
        assert len(packer.sections) == 2
        assert packer.remove_section(0) is True
        assert len(packer.sections) == 1
    
    def test_remove_invalid_index(self, minimal_section):
        """測試移除無效索引"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section)
        
        assert packer.remove_section(-1) is False
        assert packer.remove_section(99) is False
    
    def test_get_section(self, minimal_section):
        """測試取得分區"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section)
        
        section = packer.get_section(0)
        assert section is not None
        assert section['name'] == minimal_section['name']
    
    def test_get_invalid_section(self, minimal_section):
        """測試取得無效分區"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section)
        
        assert packer.get_section(99) is None


class TestFirmwarePackerAddresses:
    """FirmwarePacker 位址計算測試"""
    
    def test_calculate_addresses_empty(self):
        """測試空分區列表"""
        packer = FirmwarePacker()
        packer.calculate_addresses()
        # 不應拋出異常
    
    def test_calculate_addresses_single(self, minimal_section):
        """測試單一分區位址計算"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section)
        packer.calculate_addresses()
        
        assert packer.sections[0]['calc_addr'] == 0
    
    def test_calculate_addresses_multiple(self):
        """測試多分區位址計算"""
        packer = FirmwarePacker()
        
        for i in range(3):
            packer.add_section({
                'name': chr(65 + i),
                'max_len': 100 * (i + 1),
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
        
        packer.calculate_addresses()
        
        assert packer.sections[0]['calc_addr'] == 0
        assert packer.sections[1]['calc_addr'] == 100
        assert packer.sections[2]['calc_addr'] == 300  # 100 + 200


class TestFirmwarePackerCSV:
    """FirmwarePacker CSV 配置測試"""
    
    def test_save_and_load_config(self, temp_csv_file, minimal_section):
        """測試 CSV 儲存和載入"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section)
        
        # 儲存
        success, msg = packer.save_csv_config(temp_csv_file)
        assert success is True
        
        # 載入到新的 packer
        packer2 = FirmwarePacker()
        success2, msg2 = packer2.load_csv_config(temp_csv_file)
        
        assert success2 is True
        assert len(packer2.sections) == 1
        assert packer2.sections[0]['name'] == minimal_section['name']
    
    def test_load_nonexistent_csv(self):
        """測試載入不存在的 CSV"""
        packer = FirmwarePacker()
        success, msg = packer.load_csv_config('/nonexistent/config.csv')
        assert success is False


class TestFirmwarePackerHEXGeneration:
    """FirmwarePacker HEX 生成測試"""
    
    def test_generate_firmware_empty(self, temp_nonexistent_path):
        """測試空分區列表生成"""
        packer = FirmwarePacker()
        # 使用不存在的路徑，確保返回 False
        success, msg = packer.generate_firmware_hex(temp_nonexistent_path)
        assert success is False
        assert "empty" in msg.lower()
    
    def test_generate_firmware_with_random_data(self, temp_hex_file, minimal_section):
        """測試使用隨機資料生成"""
        packer = FirmwarePacker()
        packer.add_section(minimal_section)
        
        success, msg = packer.generate_firmware_hex(temp_hex_file)
        assert success is True
        
        # 驗證檔案存在
        assert os.path.exists(temp_hex_file)
        
        # 驗證檔案內容
        with open(temp_hex_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == minimal_section['max_len']


class TestFirmwarePackerBypassCRC:
    """Bypass CRC 測試"""
    
    def test_bypass_crc_enabled(self, temp_hex_file, minimal_section):
        """測試啟用 CRC 繞過"""
        section = minimal_section.copy()
        section['bypass_crc'] = True
        
        packer = FirmwarePacker()
        packer.add_section(section)
        
        success, msg = packer.generate_firmware_hex(temp_hex_file)
        assert success is True


class TestFirmwarePackerMask:
    """Mask 注入測試"""
    
    def test_mask_calculation(self, minimal_section):
        """測試 Mask 計算"""
        packer = FirmwarePacker()
        section = minimal_section.copy()
        section['mask_val'] = 0x0103  # Bit 0, 1, 8 = 1
        packer.add_section(section)
        
        packer.calculate_addresses()
        
        # 驗證 mask_val 保持不變
        assert packer.sections[0]['mask_val'] == 0x0103


class TestPackerWithFactory:
    """使用工廠模式的測試"""
    
    def test_factory_workflow(self, temp_csv_file, temp_hex_file):
        """測試完整工作流"""
        from tests.factories.packer_factory import PackerFactory
        
        # 建立配置
        sections = PackerFactory.create_multi_section_config(2)
        
        # 建立 CSV
        csv_path = PackerFactory.create_csv_file(sections, temp_csv_file)
        
        # 載入配置
        packer = FirmwarePacker()
        success, msg = packer.load_csv_config(csv_path)
        assert success is True
        
        # 生成 HEX
        success, msg = packer.generate_firmware_hex(temp_hex_file)
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
