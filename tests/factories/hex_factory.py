"""
HEX Parser Test Factory

產生 HEX 解析測試所需的各種測試資料。
"""

import os
import tempfile
from typing import List, Dict, Any, Tuple


class HEXFactory:
    """HEX 解析測試資料工廠"""
    
    @classmethod
    def create_address_parse_cases(cls) -> List[Tuple[str, int]]:
        """建立位址解析測試案例"""
        return [
            # (輸入, 預期輸出)
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
            ('', -1),
            ('invalid', -1),
            ('xyz', -1),
            ('  hFF  ', 0xFF),
            ('  0xFF  ', 0xFF),
            ('  FF  ', 0xFF),
        ]
    
    @classmethod
    def create_raw_hex_content(cls, data: bytes) -> str:
        """將資料轉換為 Raw HEX 格式"""
        return '\n'.join(f'{b:02X}' for b in data) + '\n'
    
    @classmethod
    def create_intel_hex_record(cls, address: int, data: bytes) -> str:
        """建立 Intel HEX 記錄"""
        byte_count = len(data)
        record_type = 0x00  # 數據記錄
        
        # 計算校驗和
        checksum = byte_count
        checksum += (address >> 8) & 0xFF
        checksum += address & 0xFF
        checksum += record_type
        for b in data:
            checksum += b
        checksum = (~checksum + 1) & 0xFF
        
        # 格式化記錄
        record = f":{byte_count:02X}{address:04X}{record_type:02X}"
        for b in data:
            record += f"{b:02X}"
        record += f"{checksum:02X}"
        
        return record.upper()
    
    @classmethod
    def create_intel_hex_with_extended_address(cls, high_addr: int, data: bytes, start_addr: int = 0) -> List[str]:
        """建立包含擴展線性位址的 Intel HEX"""
        records = []
        
        # 擴展線性位址記錄
        ext_record = f":02000004{high_addr:04X}00"
        checksum = 0x02 + 0x00 + 0x04 + ((high_addr >> 8) & 0xFF) + (high_addr & 0xFF)
        checksum = (~checksum + 1) & 0xFF
        ext_record += f"{checksum:02X}"
        records.append(ext_record)
        
        # 數據記錄
        data_record = cls.create_intel_hex_record(start_addr, data)
        records.append(data_record)
        
        # 結束記錄
        records.append(":00000001FF")
        
        return records
    
    @classmethod
    def create_raw_hex_file(cls, data: bytes, filepath: str = None) -> str:
        """建立 Raw HEX 檔案"""
        if filepath is None:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.hex', delete=False) as f:
                f.write(cls.create_raw_hex_content(data))
                filepath = f.name
        else:
            with open(filepath, 'w') as f:
                f.write(cls.create_raw_hex_content(data))
        
        return filepath
    
    @classmethod
    def create_intel_hex_file(cls, data: bytes, filepath: str = None) -> str:
        """建立 Intel HEX 檔案"""
        if filepath is None:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.hex', delete=False) as f:
                filepath = f.name
        
        with open(filepath, 'w') as f:
            # 分段寫入 (每段最多 16 bytes)
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                record = cls.create_intel_hex_record(i, chunk)
                f.write(record + '\n')
        
        return filepath
    
    @classmethod
    def create_test_file(cls, format_type: str, data: bytes = None) -> Tuple[str, str]:
        """
        建立測試檔案
        
        Args:
            format_type: 'raw' 或 'intel'
            data: 檔案資料 (預設為 0x00-0xFF)
        
        Returns:
            (filepath, format_type)
        """
        if data is None:
            data = bytes(range(256))
        
        if format_type == 'raw':
            filepath = cls.create_raw_hex_file(data)
        else:
            filepath = cls.create_intel_hex_file(data)
        
        return filepath, format_type
    
    @classmethod
    def get_standard_test_suite(cls) -> List[Dict[str, Any]]:
        """取得標準測試套件"""
        return [
            {
                'id': 'HEX-RAW-EMPTY',
                'name': 'Raw HEX 空檔案',
                'format': 'raw',
                'data': bytearray(),
            },
            {
                'id': 'HEX-RAW-SINGLE',
                'name': 'Raw HEX 單一字節',
                'format': 'raw',
                'data': bytearray([0xFF]),
            },
            {
                'id': 'HEX-RAW-MULTI',
                'name': 'Raw HEX 多行',
                'format': 'raw',
                'data': bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05]),
            },
            {
                'id': 'HEX-INTEL-SINGLE',
                'name': 'Intel HEX 單一記錄',
                'format': 'intel',
                'data': bytearray([0x00, 0x01, 0x02, 0x03]),
            },
            {
                'id': 'HEX-INTEL-MULTI',
                'name': 'Intel HEX 多記錄',
                'format': 'intel',
                'data': bytearray(range(64)),
            },
            {
                'id': 'HEX-INTEL-EXTENDED',
                'name': 'Intel HEX 擴展位址',
                'format': 'intel',
                'data': bytearray([0xAA, 0xBB, 0xCC, 0xDD]),
                'high_addr': 0x0800,
            },
        ]
