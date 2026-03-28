"""
CRC16 Test Factory

產生 CRC16 測試所需的各種測試資料。
"""

import random
from typing import List, Dict, Any


class CRC16Factory:
    """CRC16 測試資料工廠"""
    
    # CRC16 參數
    POLYNOMIAL = 0x8005
    INIT_VALUE = 0x0052
    
    @classmethod
    def create_empty_data(cls) -> bytearray:
        """建立空資料"""
        return bytearray()
    
    @classmethod
    def create_single_byte(cls, value: int = 0x00) -> bytearray:
        """建立單一字節資料"""
        return bytearray([value & 0xFF])
    
    @classmethod
    def create_sequential(cls, length: int, start: int = 0) -> bytearray:
        """建立連續序列"""
        return bytearray([(start + i) & 0xFF for i in range(length)])
    
    @classmethod
    def create_random(cls, length: int, seed: int = None) -> bytearray:
        """建立隨機資料"""
        if seed is not None:
            random.seed(seed)
        return bytearray([random.randint(0, 255) for _ in range(length)])
    
    @classmethod
    def create_all_zeros(cls, length: int) -> bytearray:
        """建立全零資料"""
        return bytearray([0x00] * length)
    
    @classmethod
    def create_all_ff(cls, length: int) -> bytearray:
        """建立全 FF 資料"""
        return bytearray([0xFF] * length)
    
    @classmethod
    def create_pattern(cls, pattern: int, length: int) -> bytearray:
        """建立重複模式資料"""
        return bytearray([pattern & 0xFF] * length)
    
    @classmethod
    def create_alternating(cls, length: int) -> bytearray:
        """建立交替模式 (0x00, 0xFF, 0x00, 0xFF...)"""
        return bytearray([0x00 if i % 2 == 0 else 0xFF for i in range(length)])
    
    @classmethod
    def create_incremental(cls, length: int) -> bytearray:
        """建立遞增資料 (0x00, 0x01, 0x02...)"""
        return bytearray([i & 0xFF for i in range(length)])
    
    @classmethod
    def create_decremental(cls, length: int) -> bytearray:
        """建立遞減資料 (0xFF, 0xFE, 0xFD...)"""
        return bytearray([(0xFF - i) & 0xFF for i in range(length)])
    
    @classmethod
    def get_standard_test_suite(cls) -> List[Dict[str, Any]]:
        """取得標準測試套件"""
        return [
            {
                'id': 'CRC-EMPTY',
                'name': '空資料',
                'data': cls.create_empty_data(),
                'expected_type': int
            },
            {
                'id': 'CRC-SINGLE-00',
                'name': '單一字節 0x00',
                'data': cls.create_single_byte(0x00),
                'expected_type': int
            },
            {
                'id': 'CRC-SINGLE-FF',
                'name': '單一字節 0xFF',
                'data': cls.create_single_byte(0xFF),
                'expected_type': int
            },
            {
                'id': 'CRC-SEQUENCE',
                'name': '連續序列 0-5',
                'data': cls.create_sequential(6),
                'expected_type': int
            },
            {
                'id': 'CRC-MIXED',
                'name': '混合資料',
                'data': bytearray([0xAA, 0xBB, 0xCC, 0xDD]),
                'expected_type': int
            },
            {
                'id': 'CRC-100-ZEROS',
                'name': '100 bytes 全零',
                'data': cls.create_all_zeros(100),
                'expected_type': int
            },
            {
                'id': 'CRC-100-FF',
                'name': '100 bytes 全 FF',
                'data': cls.create_all_ff(100),
                'expected_type': int
            },
            {
                'id': 'CRC-256-PATTERN',
                'name': '256 bytes 重複模式',
                'data': cls.create_pattern(0x5A, 256),
                'expected_type': int
            },
            {
                'id': 'CRC-256-ALTERNATING',
                'name': '256 bytes 交替模式',
                'data': cls.create_alternating(256),
                'expected_type': int
            },
            {
                'id': 'CRC-1000-INCREMENTAL',
                'name': '1000 bytes 遞增',
                'data': cls.create_incremental(1000),
                'expected_type': int
            },
        ]
    
    @classmethod
    def get_regression_values(cls) -> Dict[str, int]:
        """取得迴歸測試預期值"""
        return {
            'CRC-SINGLE-00': 0x81EF,
            'CRC-SINGLE-FF': 0x83ED,
            'CRC-SEQUENCE': cls._compute_reference_crc(bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])),
        }
    
    @classmethod
    def _compute_reference_crc(cls, data: bytearray) -> int:
        """計算參考 CRC (用於驗證)"""
        from core.crc16 import calculate_custom_crc16
        return calculate_custom_crc16(data)
