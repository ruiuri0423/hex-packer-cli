"""
Mask Calculator Test Factory

產生 Mask 計算測試所需的各種測試資料。
"""

from typing import List, Dict, Any, Tuple


class MaskFactory:
    """Mask 計算測試資料工廠"""
    
    @classmethod
    def create_alignment_cases(cls) -> List[Dict[str, Any]]:
        """建立位址對齊測試案例"""
        base = 0x1000
        return [
            {
                'id': 'ALIGN-01',
                'name': 'Flash < Base',
                'item_addr': 0x0500,
                'base_addr': base,
                'expected_addr': base,
                'was_adjusted': True
            },
            {
                'id': 'ALIGN-02',
                'name': '非 256 對齊',
                'item_addr': 0x1234,
                'base_addr': base,
                'expected_addr': 0x1200,
                'was_adjusted': True
            },
            {
                'id': 'ALIGN-03',
                'name': '已是對齊',
                'item_addr': 0x1500,
                'base_addr': base,
                'expected_addr': 0x1500,
                'was_adjusted': False
            },
            {
                'id': 'ALIGN-04',
                'name': '等於 Base',
                'item_addr': base,
                'base_addr': base,
                'expected_addr': base,
                'was_adjusted': False
            },
            {
                'id': 'ALIGN-05',
                'name': '大於 Base',
                'item_addr': 0x2000,
                'base_addr': base,
                'expected_addr': 0x2000,
                'was_adjusted': False
            },
            {
                'id': 'ALIGN-06',
                'name': '非對齊 0x1F00',
                'item_addr': 0x1F00,
                'base_addr': base,
                'expected_addr': 0x1E00,
                'was_adjusted': True
            },
        ]
    
    @classmethod
    def create_mask_bytes_cases(cls) -> List[Dict[str, Any]]:
        """建立 Mask 位元組計算測試案例"""
        base = 0x1000
        return [
            {
                'id': 'MASK-01',
                'name': '單一表格',
                'max_addr': base,
                'base_addr': base,
                'expected_bytes': 1,
                'expected_bits': 1
            },
            {
                'id': 'MASK-02',
                'name': '兩表格',
                'max_addr': base + 0x100,
                'base_addr': base,
                'expected_bytes': 1,
                'expected_bits': 2
            },
            {
                'id': 'MASK-03',
                'name': '多表格 (17 bits)',
                'max_addr': base + 0x1000,
                'base_addr': base,
                'expected_bytes': 3,
                'expected_bits': 17
            },
            {
                'id': 'MASK-04',
                'name': '長距離 (65 bits)',
                'max_addr': base + 0x4000,
                'base_addr': base,
                'expected_bytes': 9,
                'expected_bits': 65
            },
        ]
    
    @classmethod
    def create_tables_with_gaps(cls, base_addr: int = 0x1000) -> List[Dict[str, Any]]:
        """建立有 Gap 的表格列表"""
        return [
            {'name': 'Table_A', 'addr': base_addr},                    # Bit 0
            {'name': 'Table_B', 'addr': base_addr + 0x100},            # Bit 1
            # Gap: Bit 2
            {'name': 'Table_C', 'addr': base_addr + 0x300},            # Bit 3
            # Gap: Bit 4-15
            {'name': 'Table_D', 'addr': base_addr + 0x1000},          # Bit 16
        ]
    
    @classmethod
    def create_continuous_tables(cls, base_addr: int = 0x1000, count: int = 3) -> List[Dict[str, Any]]:
        """建立連續表格列表"""
        return [
            {'name': f'Table_{chr(65+i)}', 'addr': base_addr + (i * 0x100)}
            for i in range(count)
        ]
    
    @classmethod
    def create_enabled_disabled_mix(cls, base_addr: int = 0x1000) -> List[Dict[str, Any]]:
        """建立混合 Enabled/Disabled 的表格"""
        return [
            {'name': 'Table_A', 'addr': base_addr, 'enabled': True},           # Bit 0
            {'name': 'Table_B', 'addr': base_addr + 0x100, 'enabled': False},   # Bit 1 - DISABLED
            {'name': 'Table_C', 'addr': base_addr + 0x200, 'enabled': True},    # Bit 2
            {'name': 'Table_D', 'addr': base_addr + 0x300, 'enabled': False},  # Bit 3 - DISABLED
            {'name': 'Table_E', 'addr': base_addr + 0x400, 'enabled': True},   # Bit 4
        ]
    
    @classmethod
    def calculate_expected_mask(cls, tables: List[Dict[str, Any]], base_addr: int) -> int:
        """計算預期 Mask 值"""
        mask = 0
        for table in tables:
            if table.get('enabled', True):  # 預設為 Enabled
                addr = table['addr']
                bit_pos = (addr - base_addr) // 256
                if bit_pos >= 0:
                    mask |= (1 << bit_pos)
        return mask
    
    @classmethod
    def create_gap_verification_cases(cls) -> List[Dict[str, Any]]:
        """建立 Gap 驗證測試案例"""
        base = 0x1000
        return [
            {
                'id': 'GAP-01',
                'name': '無 Gap (連續)',
                'tables': [
                    {'name': 'A', 'addr': base},
                    {'name': 'B', 'addr': base + 0x100},
                ],
                'expected_gap_count': 0
            },
            {
                'id': 'GAP-02',
                'name': '一個 Gap',
                'tables': [
                    {'name': 'A', 'addr': base},
                    {'name': 'B', 'addr': base + 0x300},  # Skip 0x1100-0x1200
                ],
                'expected_gap_count': 1
            },
            {
                'id': 'GAP-03',
                'name': '多個 Gap',
                'tables': [
                    {'name': 'A', 'addr': base},
                    {'name': 'B', 'addr': base + 0x100},
                    {'name': 'C', 'addr': base + 0x500},  # Skip 0x1200-0x1400
                    {'name': 'D', 'addr': base + 0x700},  # Skip 0x1600-0x1E00
                ],
                'expected_gap_count': 2
            },
            {
                'id': 'GAP-04',
                'name': '空列表',
                'tables': [],
                'expected_gap_count': 1,  # 整個範圍視為 Gap
                'expected_full_range': True
            },
        ]
