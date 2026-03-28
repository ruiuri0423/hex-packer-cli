"""
Packer Test Factory

產生 Packer 測試所需的各種測試資料和配置。
"""

import os
import tempfile
import pandas as pd
from typing import List, Dict, Any, Optional


class PackerFactory:
    """Packer 測試資料工廠"""
    
    @classmethod
    def create_section_template(cls, **overrides) -> Dict[str, Any]:
        """建立分區配置模板"""
        section = {
            'name': 'TEST',
            'max_len': 1024,
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
        }
        section.update(overrides)
        return section
    
    @classmethod
    def create_minimal_section(cls) -> Dict[str, Any]:
        """建立最小分區配置"""
        return cls.create_section_template()
    
    @classmethod
    def create_section_with_crc(cls, name: str = 'CRC_SECTION', max_len: int = 256) -> Dict[str, Any]:
        """建立帶 CRC 的分區"""
        return cls.create_section_template(
            name=name,
            max_len=max_len,
            bypass_crc=False
        )
    
    @classmethod
    def create_section_without_crc(cls, name: str = 'NO_CRC_SECTION') -> Dict[str, Any]:
        """建立不帶 CRC 的分區"""
        return cls.create_section_template(
            name=name,
            max_len=256,
            bypass_crc=True
        )
    
    @classmethod
    def create_section_with_size_injection(cls, target: str) -> Dict[str, Any]:
        """建立帶大小注入的分區"""
        return cls.create_section_template(
            name='SIZE_INJECT',
            target_sec=target,
            size_offset=0x00,
            size_offset_orig='0x00'
        )
    
    @classmethod
    def create_section_with_addr_injection(cls, target: str) -> Dict[str, Any]:
        """建立帶位址注入的分區"""
        return cls.create_section_template(
            name='ADDR_INJECT',
            target_sec=target,
            addr_offset=0x04,
            addr_offset_orig='0x04'
        )
    
    @classmethod
    def create_section_with_enable_bit(cls, target: str, offset: int = 0x08, bit: int = 0) -> Dict[str, Any]:
        """建立帶啟用位注入的分區"""
        return cls.create_section_template(
            name='ENABLE_INJECT',
            target_sec=target,
            en_offset=offset,
            en_bit=bit,
            en_val=1
        )
    
    @classmethod
    def create_section_with_mask(cls, target: str, mask_value: int) -> Dict[str, Any]:
        """建立帶 Mask 注入的分區"""
        return cls.create_section_template(
            name='MASK_INJECT',
            mask_target=target,
            mask_offset=0x10,
            mask_val=mask_value
        )
    
    @classmethod
    def create_multi_section_config(cls, count: int = 3) -> List[Dict[str, Any]]:
        """建立多分區配置"""
        sections = []
        for i in range(count):
            sections.append(cls.create_section_template(
                name=f'SECTION_{chr(65+i)}',
                max_len=256 * (i + 1)
            ))
        return sections
    
    @classmethod
    def create_firmware_config(cls) -> List[Dict[str, Any]]:
        """建立完整韌體配置"""
        return [
            cls.create_section_template(
                name='BOOTLOADER',
                max_len=4096,
                is_full=True,
                bypass_crc=False
            ),
            cls.create_section_template(
                name='APPLICATION',
                max_len=32768,
                is_full=True,
                bypass_crc=False
            ),
            cls.create_section_template(
                name='CONFIG',
                max_len=512,
                is_full=False,
                bypass_crc=False
            ),
            cls.create_section_with_crc(name='HEADER', max_len=256),
        ]
    
    @classmethod
    def create_csv_file(cls, sections: List[Dict[str, Any]] = None, filepath: str = None) -> str:
        """建立 CSV 設定檔"""
        if sections is None:
            sections = [cls.create_minimal_section()]
        
        if filepath is None:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                filepath = f.name
        
        df = pd.DataFrame(sections)
        df.to_csv(filepath, index=False)
        
        return filepath
    
    @classmethod
    def create_hex_file_from_section(cls, section: Dict[str, Any], filepath: str = None) -> str:
        """根據分區配置建立 HEX 檔案"""
        if filepath is None:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.hex', delete=False) as f:
                filepath = f.name
        
        data_size = section.get('max_len', 1024)
        
        with open(filepath, 'w') as f:
            for i in range(min(data_size, 100)):  # 限制為 100 行
                f.write(f"{(i % 256):02X}\n")
        
        return filepath
    
    @classmethod
    def create_workflow_test_case(cls, name: str) -> Dict[str, Any]:
        """建立工作流測試案例"""
        cases = {
            'minimal': {
                'name': '最小配置',
                'sections': [cls.create_minimal_section()],
                'expected_success': True
            },
            'empty': {
                'name': '空配置',
                'sections': [],
                'expected_success': False,
                'expected_error': 'empty'
            },
            'multi_section': {
                'name': '多分區',
                'sections': cls.create_multi_section_config(3),
                'expected_success': True
            },
            'with_crc_error': {
                'name': 'CRC 錯誤注入',
                'sections': [cls.create_section_template(inject_err=True)],
                'expected_success': True,
                'verify_crc_error': True
            },
            'bypass_crc': {
                'name': 'CRC 繞過',
                'sections': [cls.create_section_without_crc()],
                'expected_success': True,
                'verify_bypass': True
            },
            'size_injection': {
                'name': '大小注入',
                'sections': [
                    cls.create_section_template(name='TARGET', max_len=256),
                    cls.create_section_with_size_injection('TARGET')
                ],
                'expected_success': True,
                'verify_size_injection': True
            },
            'mask_injection': {
                'name': 'Mask 注入',
                'sections': [
                    cls.create_section_template(name='MASK_TARGET', max_len=256),
                    cls.create_section_with_mask('MASK_TARGET', 0x0103)
                ],
                'expected_success': True,
                'verify_mask_injection': True
            }
        }
        
        return cases.get(name, cases['minimal'])
