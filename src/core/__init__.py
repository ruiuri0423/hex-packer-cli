"""
Hex Packer CLI - Core Module
固件管線工具核心模組
"""

from .crc16 import calculate_custom_crc16
from .hex_parser import parse_hex_address, parse_m0_hex_file
from .mask_calculator import (
    validate_and_align_flash_address,
    calculate_dynamic_mask_bytes,
    calculate_enable_mask_with_gaps,
    detect_flash_address_gaps
)
from .register import parse_register_excel_to_buffer
from .packer import FirmwarePacker
from .viewer import RegisterViewer

__version__ = "1.2.3"
__all__ = [
    "calculate_custom_crc16",
    "parse_hex_address",
    "parse_m0_hex_file",
    "validate_and_align_flash_address",
    "calculate_dynamic_mask_bytes",
    "calculate_enable_mask_with_gaps",
    "detect_flash_address_gaps",
    "parse_register_excel_to_buffer",
    "FirmwarePacker",
    "RegisterViewer",
]
