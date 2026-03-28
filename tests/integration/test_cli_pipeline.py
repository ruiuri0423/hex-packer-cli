"""
CLI Pipeline 整合測試

測試完整的 CLI 工作流程。
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.crc16 import calculate_custom_crc16
from core.hex_parser import parse_hex_address, parse_m0_hex_file, write_hex_file
from core.mask_calculator import (
    validate_and_align_flash_address,
    calculate_dynamic_mask_bytes,
    calculate_enable_mask_with_gaps,
    detect_flash_address_gaps
)
from core.packer import FirmwarePacker


class TestCLIPipelineComponents:
    """CLI 管線元件測試"""
    
    def test_all_imports(self):
        """測試所有主要元件可以匯入"""
        from main import (
            calculate_custom_crc16,
            parse_hex_address,
            parse_m0_hex_file,
            validate_and_align_flash_address,
            calculate_dynamic_mask_bytes,
            parse_register_excel_to_buffer,
            FirmwarePacker,
        )
        
        assert callable(calculate_custom_crc16)
        assert callable(parse_hex_address)
        assert callable(FirmwarePacker)
    
    def test_crc_hex_integration(self):
        """測試 CRC 和 HEX 整合"""
        # 計算 CRC
        data = bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])
        crc = calculate_custom_crc16(data)
        
        # 寫入 HEX
        with tempfile.NamedTemporaryFile(mode='w', suffix='.hex', delete=False) as f:
            filepath = f.name
        
        try:
            # 將 CRC 附加到資料
            full_data = data + bytearray([(crc >> 8) & 0xFF, crc & 0xFF])
            write_hex_file(filepath, full_data)
            
            # 讀回
            success, buf, size = parse_m0_hex_file(filepath)
            assert success
            assert len(buf) == len(full_data)
            
            # 驗證 CRC
            computed_crc = calculate_custom_crc16(buf[:len(buf)-2])
            assert computed_crc == crc
        finally:
            os.remove(filepath)


class TestFirmwarePackerCSVWorkflow:
    """FirmwarePacker CSV 工作流測試"""
    
    def test_full_workflow(self, temp_csv_file, temp_hex_file):
        """測試完整 CSV 到 HEX 工作流"""
        import pandas as pd
        
        # 建立測試 CSV
        sections = [{
            'name': 'TEST_SECTION',
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
        }]
        
        pd.DataFrame(sections).to_csv(temp_csv_file, index=False)
        
        # 載入並生成
        packer = FirmwarePacker()
        success, msg = packer.load_csv_config(temp_csv_file)
        assert success
        
        success, msg = packer.generate_firmware_hex(temp_hex_file)
        assert success
        
        # 驗證 HEX 檔案
        assert os.path.exists(temp_hex_file)
        with open(temp_hex_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 256


class TestMaskCalculationIntegration:
    """Mask 計算整合測試"""
    
    def test_dynamic_mask_workflow(self, base_address, sample_flash_tables):
        """測試動態 Mask 工作流"""
        # 對齊所有位址
        aligned_tables = []
        for table in sample_flash_tables:
            addr, adj, _ = validate_and_align_flash_address(table['addr'], base_address)
            aligned_tables.append({
                'name': table['name'],
                'addr': addr
            })
        
        # 計算 Mask
        mask_val, mask_bytes, mapping = calculate_enable_mask_with_gaps(
            aligned_tables, base_address
        )
        
        # 驗證
        assert mask_val > 0
        assert mask_bytes >= 1
        assert len(mapping) == len(sample_flash_tables)
        
        # 檢測 Gaps
        max_addr = max(t['addr'] for t in aligned_tables)
        gaps = detect_flash_address_gaps(aligned_tables, base_address, max_addr)
        
        # Gap 數量應 >= 0
        assert isinstance(gaps, list)


class TestM0HEXProcessing:
    """M0 HEX 處理測試"""
    
    def test_parse_m0_hex_raw(self, temp_hex_file):
        """測試解析原始 HEX"""
        with open(temp_hex_file, 'w') as f:
            f.write("00 01 02 03 04 05\n")
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success
        assert len(buf) == 6
        assert buf[0] == 0x00
        assert buf[5] == 0x05
    
    def test_parse_m0_hex_intel(self, temp_hex_file):
        """測試解析 Intel HEX"""
        with open(temp_hex_file, 'w') as f:
            f.write(":06000100010203040506FC\n")
        
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success


class TestAddressAlignmentIntegration:
    """位址對齊整合測試"""
    
    def test_address_alignment_cli(self, base_address):
        """測試 CLI 中的位址對齊"""
        # Flash < Base → 對齊到 Base
        addr, adj, _ = validate_and_align_flash_address(0x0500, base_address)
        assert addr == base_address
        assert adj is True
        
        # 非對齊 → 對齊
        addr, adj, _ = validate_and_align_flash_address(0x1234, base_address)
        assert addr == 0x1200
        assert adj is True
        
        # 已對齊 → 保持
        addr, adj, _ = validate_and_align_flash_address(base_address, base_address)
        assert addr == base_address
        assert adj is False


class TestFullPipelineIntegration:
    """完整管線整合測試"""
    
    def test_crc_to_hex_pipeline(self, temp_hex_file):
        """測試 CRC 到 HEX 管線"""
        # 1. 生成資料
        original_data = bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])
        
        # 2. 計算 CRC
        crc = calculate_custom_crc16(original_data)
        
        # 3. 準備輸出資料
        output_data = bytearray(len(original_data) + 2)
        for i, b in enumerate(original_data):
            output_data[i] = b
        output_data[-2] = (crc >> 8) & 0xFF
        output_data[-1] = crc & 0xFF
        
        # 4. 寫入 HEX
        success = write_hex_file(temp_hex_file, output_data)
        assert success
        
        # 5. 讀回
        success, buf, size = parse_m0_hex_file(temp_hex_file)
        assert success
        assert len(buf) == len(output_data)
        
        # 6. 驗證 CRC
        extracted_data = buf[:len(buf)-2]
        extracted_crc = buf[-2] << 8 | buf[-1]
        computed_crc = calculate_custom_crc16(extracted_data)
        
        assert computed_crc == crc
        assert extracted_crc == crc


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
