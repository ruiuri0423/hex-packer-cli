#!/usr/bin/env python3
"""Integration tests for hex-packer-cli core functions."""

import sys
sys.path.insert(0, 'src')
from main import (
    generate_integrated_hex,
    validate_and_align_flash_address,
    calculate_dynamic_mask_bytes,
    calculate_enable_mask_with_gaps,
    detect_flash_address_gaps
)

def test_validate_and_align_flash_address():
    """Test address alignment."""
    addr, adj, warn = validate_and_align_flash_address(0x0100, 0x1000)
    assert addr == 0x1000, f'Expected 0x1000, got 0x{addr:04X}'
    print("[PASS] validate_and_align_flash_address")

def test_calculate_dynamic_mask_bytes():
    """Test mask bytes calculation."""
    bytes_val, bits = calculate_dynamic_mask_bytes(0x2000, 0x1000)
    assert bits == 5, f'Expected 5 bits, got {bits}'
    print("[PASS] calculate_dynamic_mask_bytes")

def test_calculate_enable_mask_with_gaps():
    """Test enable mask calculation."""
    tables = [
        {'name': 'A', 'addr': 0x1000, 'enabled': True},
        {'name': 'B', 'addr': 0x1300, 'enabled': True},
    ]
    mask_val, mask_bytes, mapping = calculate_enable_mask_with_gaps(tables, 0x1000)
    assert mask_val == 0b11, f'Expected 0b11, got {bin(mask_val)}'
    print("[PASS] calculate_enable_mask_with_gaps")

def test_detect_flash_address_gaps():
    """Test gap detection."""
    tables = [
        {'name': 'A', 'addr': 0x1000, 'enabled': True},
        {'name': 'B', 'addr': 0x1300, 'enabled': True},
    ]
    gaps = detect_flash_address_gaps(tables, 0x1000, 0x2000)
    assert len(gaps) == 1, f'Expected 1 gap, got {len(gaps)}'
    print("[PASS] detect_flash_address_gaps")

def test_generate_integrated_hex():
    """Test shared core function."""
    test_tables = [
        {'name': 'A', 'path': '', 'addr': 0x1000, 'enabled': True, 'buffer': bytearray([0xAA]*256)},
        {'name': 'B', 'path': '', 'addr': 0x1300, 'enabled': True, 'buffer': bytearray([0xBB]*256)},
        {'name': 'C', 'path': '', 'addr': 0x2000, 'enabled': False, 'buffer': bytearray([0xCC]*256)},
    ]
    result = generate_integrated_hex(test_tables, 0x1000, None, include_disabled=True)
    success, buf, mask_val, mask_bytes, total_size, e_count, d_count, alog, gcount = result
    assert success == True, 'generate_integrated_hex failed'
    assert e_count == 2, f'Expected 2 enabled, got {e_count}'
    assert d_count == 1, f'Expected 1 disabled, got {d_count}'
    print("[PASS] generate_integrated_hex (include_disabled=True)")

if __name__ == '__main__':
    print("Running integration tests...")
    print()
    
    test_validate_and_align_flash_address()
    test_calculate_dynamic_mask_bytes()
    test_calculate_enable_mask_with_gaps()
    test_detect_flash_address_gaps()
    test_generate_integrated_hex()
    
    print()
    print("All integration tests passed!")
