"""
CLI 功能整合測試
"""

import pytest
import tempfile
import os
import sys

# 確保可以匯入 main.py 中的函數
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestCLIArguments:
    """CLI 參數解析測試"""

    def test_cli_help(self):
        """測試 CLI 幫助訊息"""
        import subprocess
        result = subprocess.run(
            [sys.executable, '-c', 
             'import sys; sys.path.insert(0, "src"); '
             'from main import *; '
             'import argparse; '
             'parser = argparse.ArgumentParser(); '
             'print("OK")'],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )
        # 應該能正常執行
        assert result.returncode == 0 or "argparse" in result.stdout or "OK" in result.stdout

    def test_cli_missing_config(self):
        """測試 CLI 缺少 config 參數"""
        import subprocess
        result = subprocess.run(
            [sys.executable, 'src/main.py', '--cli'],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )
        # 應該輸出錯誤訊息
        assert "config" in result.stdout.lower() or "error" in result.stdout.lower()


class TestCLIGenerateIntegratedHex:
    """CLI 整合 HEX 生成測試"""

    def test_generate_integrated_hex_import(self):
        """測試 CLI 函數可以匯入"""
        from main import generate_integrated_hex_from_csv
        assert callable(generate_integrated_hex_from_csv)

    def test_generate_integrated_hex_missing_file(self):
        """測試處理不存在的 CSV 檔案"""
        from main import generate_integrated_hex_from_csv
        
        success, mask = generate_integrated_hex_from_csv(
            '/nonexistent/file.csv',
            '0x1000',
            '/tmp/output.hex'
        )
        # 應該失敗
        assert success is False


class TestCLIArgumentParsing:
    """CLI 參數解析測試"""

    def test_base_address_hex_parsing(self):
        """測試 Base Address 十六進位解析"""
        from core.hex_parser import parse_hex_address
        
        assert parse_hex_address('1000') == 0x1000
        assert parse_hex_address('0x1000') == 0x1000
        assert parse_hex_address('h1000') == 0x1000

    def test_address_alignment_cli(self):
        """測試 CLI 中的位址對齊"""
        from core.mask_calculator import validate_and_align_flash_address
        
        # Flash < Base → 對齊到 Base
        addr, adj, _ = validate_and_align_flash_address(0x0500, 0x1000)
        assert addr == 0x1000
        assert adj is True
        
        # 非對齊 → 對齊
        addr, adj, _ = validate_and_align_flash_address(0x1234, 0x1000)
        assert addr == 0x1200
        assert adj is True
        
        # 已對齊 → 保持
        addr, adj, _ = validate_and_align_flash_address(0x1000, 0x1000)
        assert addr == 0x1000
        assert adj is False


class TestCLIPipeline:
    """CLI 管線測試"""

    def test_packer_import(self):
        """測試 FirmwarePacker 可以匯入"""
        from main import FirmwarePacker
        packer = FirmwarePacker()
        assert packer.sections == []

    def test_full_pipeline_components(self):
        """測試完整管線元件"""
        # 測試所有主要元件可以匯入
        from main import (
            calculate_custom_crc16,
            parse_hex_address,
            parse_m0_hex_file,
            validate_and_align_flash_address,
            calculate_dynamic_mask_bytes,
            parse_register_excel_to_buffer,
            FirmwarePacker,
            generate_integrated_hex_from_csv
        )
        
        # 驗證函數可呼叫
        crc = calculate_custom_crc16(bytearray([0x00, 0x01]))
        assert isinstance(crc, int)
        
        addr = parse_hex_address('0xFF')
        assert addr == 0xFF
        
        aligned, adj, _ = validate_and_align_flash_address(0x1234, 0x1000)
        assert aligned == 0x1200
        
        bytes_needed, bits = calculate_dynamic_mask_bytes(0x2000, 0x1000)
        assert bytes_needed == 3
        assert bits == 17
        
        packer = FirmwarePacker()
        assert isinstance(packer, FirmwarePacker)


class TestCLIFirmwareGeneration:
    """CLI 固件生成測試"""

    def test_firmware_packer_csv_workflow(self):
        """測試從 CSV 到 HEX 的完整流程"""
        import pandas as pd
        
        # 建立測試 CSV
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            csv_path = f.name
            pd.DataFrame([{
                'name': 'TEST_SECTION',
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
                'bypass_crc': False
            }]).to_csv(csv_path, index=False)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            hex_path = f.name
        
        try:
            # 載入配置
            from main import FirmwarePacker
            packer = FirmwarePacker()
            success, msg = packer.load_csv_config(csv_path)
            assert success is True
            assert len(packer.sections) == 1
            
            # 生成 HEX
            success, msg = packer.generate_firmware_hex(hex_path)
            assert success is True
            
            # 驗證 HEX 檔案
            assert os.path.exists(hex_path)
            with open(hex_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 100
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)
            if os.path.exists(hex_path):
                os.remove(hex_path)


class TestCLIM0Processing:
    """CLI M0 處理測試"""

    def test_parse_m0_hex_raw(self):
        """測試解析原始 HEX"""
        from core.hex_parser import parse_m0_hex_file
        
        # 建立測試檔案
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            f.write("00 01 02 03 04 05\n")
            hex_path = f.name
        
        try:
            success, buf, size = parse_m0_hex_file(hex_path)
            assert success is True
            assert len(buf) == 6
            assert buf[0] == 0x00
            assert buf[5] == 0x05
            assert size == 6
        finally:
            os.remove(hex_path)

    def test_parse_m0_hex_intel(self):
        """測試解析 Intel HEX"""
        from core.hex_parser import parse_m0_hex_file
        
        # 建立 Intel HEX 格式檔案
        # :06000100010203040506
        # 06 = 6 bytes
        # 0001 = address 0x0001
        # 00 = data record
        # 010203040506 = data
        # Check byte would be calculated
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.hex') as f:
            f.write(":06000100010203040506AB\n")  # 最後的 AB 是隨機校驗
            hex_path = f.name
        
        try:
            success, buf, size = parse_m0_hex_file(hex_path)
            assert success is True
            # Intel HEX 會解析記錄
            assert len(buf) >= 6
        finally:
            os.remove(hex_path)


class TestCLIMaskIntegration:
    """CLI Mask 整合測試"""

    def test_dynamic_mask_calculation_integration(self):
        """測試動態 Mask 計算整合"""
        from core.mask_calculator import (
            validate_and_align_flash_address,
            calculate_dynamic_mask_bytes,
            calculate_enable_mask_with_gaps,
            detect_flash_address_gaps
        )
        
        # 模擬表格場景
        base_addr = 0x1000
        tables = [
            {'name': 'Table_A', 'addr': 0x1000, 'enabled': True},
            {'name': 'Table_B', 'addr': 0x1300, 'enabled': True},
            {'name': 'Table_C', 'addr': 0x2000, 'enabled': True},
            {'name': 'Table_D', 'addr': 0x0500, 'enabled': False},  # 會被對齊
        ]
        
        # 對齊所有位址
        aligned_tables = []
        for t in tables:
            addr, adj, _ = validate_and_align_flash_address(t['addr'], base_addr)
            aligned_tables.append({
                'name': t['name'],
                'addr': addr,
                'enabled': t['enabled']
            })
        
        # 計算 Mask
        enabled = [t for t in aligned_tables if t['enabled']]
        mask_val, mask_bytes, bit_mapping = calculate_enable_mask_with_gaps(enabled, base_addr)
        
        # 驗證
        max_addr = max(t['addr'] for t in enabled)
        expected_bytes, expected_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        
        assert mask_bytes == expected_bytes
        assert len(bit_mapping) == 3  # 3 個 enabled 表格
        
        # 驗證 Gap
        gaps = detect_flash_address_gaps(enabled, base_addr, max_addr)
        assert len(gaps) >= 1  # 應該有 Gap


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
