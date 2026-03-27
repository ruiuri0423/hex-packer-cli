import os
import sys
import random
import argparse
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time

# =========================================================================
# Shared Logic: Hex Parsing, M0 Intel HEX, and Parallel Hardware CRC16
# =========================================================================

def parse_hex_address(val):
    """Safely converts string hex addresses (e.g., 'h00FF', '0xFF') to integer."""
    val_str = str(val).strip().lower().replace('h', '').replace('0x', '')
    if not val_str: return -1
    try: return int(val_str, 16)
    except ValueError: return -1

def calculate_custom_crc16(data):
    """
    Parallel CRC16 calculation corresponding to hardware Verilog logic.
    Polynomial: 0x8005
    Initial value: 0x0052
    Input: bytearray or list of 8-bit integers.
    """
    bo = 0x0052  # Initial value: 16'h52

    for d_in in data:
        # Pre-calculate XOR sum to optimize performance (equivalent to b[i] ^ d[i])
        x = bo ^ d_in
        
        # Extract bits 0 to 15 from x
        x_bit = [(x >> i) & 1 for i in range(16)]
        
        new_bo = [0] * 16

        # --- Parallel Bitwise XOR Logic (Mapped strictly from Verilog) ---
        new_bo[15] = x_bit[0]^x_bit[1]^x_bit[2]^x_bit[3]^x_bit[4]^x_bit[5]^x_bit[6]^x_bit[7]^x_bit[8]^x_bit[9]^x_bit[10]^x_bit[11]^x_bit[12]^x_bit[14]^x_bit[15]
        new_bo[14] = x_bit[12]^x_bit[13]
        new_bo[13] = x_bit[11]^x_bit[12]
        new_bo[12] = x_bit[10]^x_bit[11]
        new_bo[11] = x_bit[9]^x_bit[10]
        new_bo[10] = x_bit[8]^x_bit[9]
        new_bo[9]  = x_bit[7]^x_bit[8]
        new_bo[8]  = x_bit[6]^x_bit[7]
        new_bo[7]  = x_bit[5]^x_bit[6]
        new_bo[6]  = x_bit[4]^x_bit[5]
        new_bo[5]  = x_bit[3]^x_bit[4]
        new_bo[4]  = x_bit[2]^x_bit[3]
        new_bo[3]  = x_bit[1]^x_bit[2]^x_bit[15]
        new_bo[2]  = x_bit[0]^x_bit[1]^x_bit[14]
        new_bo[1]  = x_bit[1]^x_bit[2]^x_bit[3]^x_bit[4]^x_bit[5]^x_bit[6]^x_bit[7]^x_bit[8]^x_bit[9]^x_bit[10]^x_bit[11]^x_bit[12]^x_bit[13]^x_bit[14]
        new_bo[0]  = x_bit[0]^x_bit[1]^x_bit[2]^x_bit[3]^x_bit[4]^x_bit[5]^x_bit[6]^x_bit[7]^x_bit[8]^x_bit[9]^x_bit[10]^x_bit[11]^x_bit[12]^x_bit[13]^x_bit[15]

        # Reconstruct the 16-bit integer from the bit array
        bo = 0
        for i in range(16):
            bo |= (new_bo[i] << i)
            
    return bo

def parse_register_excel_to_buffer(file_path):
    """Reads a Register Excel file, extracts Init values shifted by LSB, and returns a 256-byte array with CRC."""
    page_buffer = bytearray(256)
    try:
        df = pd.read_excel(file_path).fillna("")
        total_cols = len(df.columns)
        for idx, row in df.iterrows():
            if total_cols < 10: continue
            low = parse_hex_address(row.iloc[1])
            high = parse_hex_address(row.iloc[0])
            if low < 0 or high < 0: continue
            
            # Fetch LSB to determine the correct bitwise shift
            loc_lsb_str = str(row.iloc[3]).strip()
            try: loc_lsb = int(loc_lsb_str)
            except ValueError: loc_lsb = 0
            
            init_str = str(row.iloc[8]).replace('h', '').replace('0x', '').strip()
            if not init_str: continue
            try:
                init_val = int(init_str, 16)
                # Shift the value to its correct bit-field position
                shifted_val = init_val << loc_lsb 
                span = (high - low) + 1
                max_bytes = max(span, (shifted_val.bit_length() + 7) // 8)
                
                # Apply bitwise OR across required bytes safely
                for i in range(max_bytes):
                    if low + i < 254: 
                        page_buffer[low + i] |= ((shifted_val >> (i * 8)) & 0xFF)
            except ValueError: pass

        # Compute CRC for 0x00 to 0xFD
        crc_val = calculate_custom_crc16(page_buffer[:254])
        page_buffer[254] = (crc_val >> 8) & 0xFF  # MSB
        page_buffer[255] = crc_val & 0xFF         # LSB
        return True, page_buffer
    except Exception as e:
        return False, bytearray(256)

def parse_m0_hex_file(filepath):
    """Smart parser that auto-detects standard Intel HEX or Raw Space-separated HEX."""
    try:
        with open(filepath, 'r') as f:
            first_char = f.read(1)
            
        if first_char == ':': 
            # Mode 1: Standard Intel HEX
            memory = {}
            base_addr = 0
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line[0] != ':': continue
                    byte_count = int(line[1:3], 16)
                    address = int(line[3:7], 16)
                    record_type = int(line[7:9], 16)
                    
                    if record_type == 0: # Data Record
                        for i in range(byte_count): 
                            memory[base_addr + address + i] = int(line[9+i*2 : 11+i*2], 16)
                    elif record_type == 4: # Extended Linear Address
                        base_addr = int(line[9:13], 16) << 16
                        
            if not memory: return False, bytearray(), 0
            
            min_addr = min(memory.keys())
            max_addr = max(memory.keys())
            orig_size = (max_addr - min_addr) + 1
            
            # Build contiguous buffer padded with 0xFF for empty regions
            buf = bytearray([0xFF] * orig_size)
            for addr, val in memory.items(): 
                buf[addr - min_addr] = val
            return True, buf, orig_size
            
        else: 
            # Mode 2: Raw Space-Separated HEX matrix
            buf = bytearray()
            with open(filepath, 'r') as f:
                for line in f:
                    tokens = line.strip().split()
                    for token in tokens:
                        if token: buf.append(int(token, 16))
            return True, buf, len(buf)
            
    except Exception as e:
        return False, bytearray(), 0



# =========================================================================
# Tab3 Register Integrator Helper Functions (Enhanced Logic)
# =========================================================================

def validate_and_align_flash_address(item_addr, base_addr):
    """
    Validates flash address and auto-aligns to base address if necessary.
    
    Rules:
    - If item_addr < base_addr: align to base_addr
    - Flash addresses must be 256-byte aligned (bit 0-7 must be 0)
    
    Returns: (adjusted_addr, was_adjusted, alignment_warning)
    """
    was_adjusted = False
    alignment_warning = ""
    
    # 確保輸入是整數
    try:
        item_addr = int(item_addr)
        base_addr = int(base_addr)
    except (ValueError, TypeError):
        return base_addr, False, "Invalid address type"
    
    # Rule 3: If flash address < base address, auto-align to base address
    if item_addr < base_addr:
        item_addr = base_addr
        was_adjusted = True
        alignment_warning = f"Auto-aligned from below base to 0x{item_addr:04X}"
    
    # Rule 4: Ensure 256-byte alignment (Flash addresses must be in 256-byte blocks)
    if item_addr > 0 and item_addr % 256 != 0:
        old_addr = item_addr
        item_addr = (item_addr // 256) * 256
        alignment_warning = f"Auto-aligned from 0x{old_addr:04X} to 0x{item_addr:04X} (256-byte boundary)"
        was_adjusted = True
    
    return item_addr, was_adjusted, alignment_warning


def calculate_dynamic_mask_bytes(max_flash_addr, base_addr):
    """
    Calculate the required number of bytes to represent the enable mask.
    
    Rule 5:
    - Calculate bits needed = (max_flash_addr - base_addr) // 256
    - Convert to bytes: (bits_needed + 7) // 8
    - Minimum 1 byte
    
    Returns: (mask_byte_length, total_bits)
    """
    # 確保輸入是整數
    try:
        max_flash_addr = int(max_flash_addr)
        base_addr = int(base_addr)
    except (ValueError, TypeError):
        return 1, 0
    
    if max_flash_addr <= base_addr:
        return 1, 0
    
    # Calculate how many 256-byte blocks from base to max address
    offset = max_flash_addr - base_addr
    if offset <= 0:
        return 1, 0
    
    total_bits = (offset // 256) + 1  # +1 because Bit 0 = base_addr
    
    # Convert to bytes (each byte = 8 bits)
    mask_bytes = (total_bits + 7) // 8
    
    return max(1, mask_bytes), total_bits


def calculate_enable_mask_with_gaps(enabled_items, base_addr):
    """
    Calculate enable mask considering gaps/jumps in flash addresses.
    
    Rule 5-2:
    - For each enabled table, calculate bit position = (addr - base) // 256
    - Gaps in flash address = corresponding mask bit = 0
    - Return mask value and bit position mapping
    
    Returns: (mask_value, mask_byte_length, bit_mapping_info)
    """
    if not enabled_items:
        return 0, 1, []
    
    # Find max address to determine byte length
    max_addr = max(item['addr'] for item in enabled_items)
    mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
    
    # Calculate mask value (gaps will naturally have 0 in their bit positions)
    mask_value = 0
    bit_mapping = []
    
    for item in enabled_items:
        addr = item['addr']
        bit_pos = (addr - base_addr) // 256
        
        if 0 <= bit_pos < total_bits:
            mask_value |= (1 << bit_pos)
            bit_mapping.append({
                'name': item['name'],
                'addr': addr,
                'bit_pos': bit_pos,
                'enabled': True
            })
        else:
            bit_mapping.append({
                'name': item['name'],
                'addr': addr,
                'bit_pos': bit_pos,
                'enabled': False,
                'reason': 'out_of_range'
            })
    
    return mask_value, mask_bytes, bit_mapping


def detect_flash_address_gaps(enabled_items, base_addr, max_addr):
    """
    Detect gaps/jumps in flash addresses for HEX generation.
    
    Rule 6:
    - Identify ranges with no tables
    - These gaps will be filled with 0xFF padding
    
    Returns: list of (gap_start, gap_end) tuples in absolute addresses
    """
    # 確保所有輸入是整數
    try:
        base_addr = int(base_addr)
        max_addr = int(max_addr)
    except (ValueError, TypeError):
        return []
    
    if not enabled_items:
        return [(base_addr, max_addr + 255)]
    
    gaps = []
    try:
        sorted_items = sorted(enabled_items, key=lambda x: int(x['addr']))
    except (ValueError, TypeError, KeyError):
        return []
    
    # Check gap before first table
    try:
        first_addr = int(sorted_items[0]['addr'])
        if first_addr > base_addr:
            gaps.append((base_addr, first_addr - 256))
    except (ValueError, TypeError, KeyError, IndexError):
        pass
    
    # Check gaps between tables
    for i in range(len(sorted_items) - 1):
        try:
            current_addr = int(sorted_items[i]['addr'])
            next_addr = int(sorted_items[i + 1]['addr'])
        except (ValueError, TypeError, KeyError):
            continue
        
        current_end = current_addr + 256
        
        if next_addr > current_end:
            # There's a gap between current table end and next table start
            gaps.append((current_end, next_addr - 256))
    
    return gaps


# =========================================================================
# CLI Headless Execution Functions
# =========================================================================
def generate_integrated_hex_from_csv(csv_path, base_addr_hex_str, out_path):
    """CLI Worker: Parses CSV, generates the integrated hex map, and calculates dynamic Enable Mask.
    
    NEW Mask Calculation Logic (Enhanced):
    1. Get global base address
    2. Compare min Flash Address with global base address
    3. If flash_address < base_address: auto-align to base_address
    4. Flash addresses must be 256-byte aligned
    5. Calculate enable mask bytes based on MAX flash address - base_address
       - Total length = max_flash_addr - base_addr (in bits, converted to bytes)
       - Gap areas in flash address = corresponding mask bit = 0
    6. Gap areas filled with 0xFF padding in HEX output
    """
    print(f"[*] Parsing Integrator Config: {csv_path}")
    try:
        df = pd.read_csv(csv_path).fillna("")
        base_addr = int(base_addr_hex_str, 16)
        all_items = []  # All items (enabled + disabled) for mask calculation
        enabled_items = []  # Only enabled items for output
        base_dir = os.path.dirname(csv_path)

        # First pass: collect all items with their properties
        for _, row in df.iterrows():
            addr = int(str(row.get("Address_Hex", "0")).replace("0x", ""), 16)
            is_enabled = str(row.get("Enabled", "Yes")).strip().lower() in ["yes", "true", "1", "y"]
            rel_path = str(row.get("Relative_Path", ""))
            name = str(row.get("Name", ""))
            all_items.append({
                'addr': addr, 
                'enabled': is_enabled, 
                'rel_path': rel_path, 
                'name': name
            })

        # Sort by Flash Address
        all_items.sort(key=lambda x: x['addr'])
        
        # NEW: Validate and auto-align all addresses
        print(f"[*] Global Base Address: 0x{base_addr:04X}")
        print(f"[*] Validating and auto-aligning Flash Addresses...")
        
        for item in all_items:
            old_addr = item['addr']
            item['addr'], was_adjusted, warning = validate_and_align_flash_address(item['addr'], base_addr)
            if was_adjusted:
                print(f"    [A] {item['name'][:25]:25s}: 0x{old_addr:04X} -> 0x{item['addr']:04X}")
                if warning:
                    print(f"        {warning}")
        
        # NEW: Calculate dynamic mask with proper byte length based on max address
        enabled_addr_list = [item for item in all_items if item['enabled']]
        
        if enabled_addr_list:
            max_addr = max(item['addr'] for item in enabled_addr_list)
            mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
            
            print(f"[*] Max Flash Address: 0x{max_addr:04X}")
            print(f"[*] Total Enable Bits needed: {total_bits}")
            print(f"[*] Mask Byte Length: {mask_bytes} byte(s)")
            
            # Calculate mask value (gaps automatically = 0)
            dynamic_mask = 0
            for item in enabled_addr_list:
                bit_position = (item['addr'] - base_addr) // 256
                if 0 <= bit_position < 128:  # Support up to 128 bits (16 bytes)
                    dynamic_mask |= (1 << bit_position)
            
            print(f"[*] Enable Mask (Hex): 0x{dynamic_mask:0{mask_bytes*2}X}")
        else:
            dynamic_mask = 0
            mask_bytes = 1
            total_bits = 0
            print(f"[*] No enabled tables - Mask: 0x0000")
        
        # Debug: Print bit-to-address mapping
        print(f"\n[*] Bit-to-Address Mapping (Base 0x{base_addr:04X} + Bit*N*256):")
        gap_count = 0
        last_end = base_addr
        for item in all_items:
            if item['enabled']:
                bit_pos = (item['addr'] - base_addr) // 256
                # Detect gap
                if item['addr'] > last_end + 256:
                    gap_count += 1
                    gap_size = (item['addr'] - last_end) // 256
                    print(f"    [GAP #{gap_count}] 0x{last_end:04X} - 0x{item['addr']-256:04X} ({gap_size} blocks = Mask bits = 0)")
                print(f"    ├── Bit {bit_pos:2d}: 0x{item['addr']:04X} - {item['name'][:20]}")
                last_end = item['addr'] + 256
        
        # Second pass: collect enabled items with buffers
        for item in all_items:
            if item['enabled']:
                if not item['rel_path']: continue
                full_path = os.path.normpath(os.path.join(base_dir, item['rel_path']))
                success, buf = parse_register_excel_to_buffer(full_path)
                if success: 
                    enabled_items.append({'addr': item['addr'], 'buffer': buf, 'name': item['name']})
                else: 
                    print(f"[-] Error parsing {full_path}"); return False, 0

        if not enabled_items: print("[-] No enabled tables found."); return False, 0

        # NEW: Calculate total output size with proper gap handling
        max_addr = max([item['addr'] for item in enabled_items])
        total_size = (max_addr - base_addr) + 256
        integrated_buffer = bytearray([0xFF] * total_size)
        
        print(f"\n[*] Generating Integrated HEX (Size: {total_size} bytes)...")
        print(f"[*] Gap areas will be filled with 0xFF padding")

        # Fill in enabled tables (gaps remain as 0xFF padding - already initialized)
        for item in enabled_items:
            start = item['addr'] - base_addr
            integrated_buffer[start:start+256] = item['buffer']
            print(f"    ├── Placed {item['name'][:20]:20s} at 0x{item['addr']:04X}")

        with open(out_path, 'w') as f:
            for byte in integrated_buffer: f.write(f"{byte:02X}\n")
            
        print(f"\n[+] Integrator Generated successfully: {out_path}")
        print(f"[+] Total Output Size: {total_size} bytes (includes gap padding)")
        return True, dynamic_mask
        
    except Exception as e:
        print(f"[-] Integrator Error: {e}")
        import traceback; traceback.print_exc()
        return False, 0


# =========================================================================
# Core 1: Firmware Packer Backend
# =========================================================================
class FirmwarePacker:
    def __init__(self):
        self.sections = []

    def load_csv_config(self, file_path):
        """Loads Packer configuration from CSV."""
        
        # Helper to prevent pandas from turning "14" into "14.0" (float) when column has mixed blanks
        def clean_str(val):
            s = str(val).strip()
            if s.endswith('.0'): return s[:-2]
            return s
            
        def safe_int(val, default=""):
            s = str(val).strip()
            if not s: return default
            try: 
                if s.lower().startswith("0x") or s.lower().startswith("-0x"):
                    return int(s, 16)
                return int(float(s))
            except ValueError: return default

        try:
            df = pd.read_csv(file_path).fillna("")
            new_sections = []
            for _, row in df.iterrows():
                sec = {
                    'name': str(row.get('name', '')),
                    'max_len': safe_int(row.get('max_len'), 1024),
                    'file_path': str(row.get('file_path', '')),
                    'is_full': bool(row.get('is_full', True)),
                    'inject_err': bool(row.get('inject_err', False)),
                    'target_sec': str(row.get('target_sec', '')),
                    
                    'size_offset': safe_int(row.get('size_offset')),
                    'size_offset_orig': clean_str(row.get('size_offset_orig')),
                    
                    'en_offset': safe_int(row.get('en_offset')),
                    'en_offset_orig': clean_str(row.get('en_offset_orig')),
                    'en_bit': safe_int(row.get('en_bit')),
                    'en_val': safe_int(row.get('en_val'), 1),
                    
                    'crc_offset': safe_int(row.get('crc_offset')),
                    'crc_offset_orig': clean_str(row.get('crc_offset_orig')),
                    'crc_bit': safe_int(row.get('crc_bit')),
                    'crc_val': safe_int(row.get('crc_val'), 1),
                    
                    'addr_offset': safe_int(row.get('addr_offset')),
                    'addr_offset_orig': clean_str(row.get('addr_offset_orig')),
                    
                    'mask_target': str(row.get('mask_target', '')),
                    'mask_offset': safe_int(row.get('mask_offset')),
                    'mask_offset_orig': clean_str(row.get('mask_offset_orig')),
                    'mask_val': safe_int(row.get('mask_val'), 0),
                    
                    'calc_addr': 0, 
                    'bypass_crc': bool(row.get('bypass_crc', False))
                }
                new_sections.append(sec)
            self.sections = new_sections
            return True, f"Loaded {len(self.sections)} sections."
        except Exception as e: return False, str(e)

    def save_csv_config(self, file_path):
        """Saves Packer configuration to CSV."""
        if not self.sections: return False, "No sections to save."
        try:
            pd.DataFrame(self.sections).to_csv(file_path, index=False)
            return True, file_path
        except Exception as e: return False, str(e)

    def calculate_addresses(self):
        """Calculates dynamic absolute addresses for header cross-referencing."""
        current_addr = 0
        for sec in self.sections:
            sec['calc_addr'] = current_addr
            current_addr += sec['max_len']

    def generate_firmware_hex(self, output_file="all_crc.hex"):
        """Pure Python logic: File Reading, Rule Validation, Padding, Parameter Injection, and strict CRC computation."""
        if not self.sections: return False, "Section list is empty!"
        self.calculate_addresses()

        buffers = {}
        actual_lens = {}

        # ---------------------------------------------------------
        # Phase 1: Buffer Initialization, Padding & Rule Validation
        # ---------------------------------------------------------
        for sec in self.sections:
            N = sec['name']
            max_len = sec['max_len']

            if sec['file_path'] and os.path.exists(sec['file_path']):
                try:
                    with open(sec['file_path'], 'r') as f:
                        lines = [l.strip() for l in f if l.strip()]
                    
                    actual_len = len(lines)
                    
                    # Rule Check: File length must be <= max_len
                    if actual_len > max_len:
                        return False, f"Error: File length ({actual_len}) exceeds Max Length ({max_len}) for section '{N}'."
                    
                    # Rule Check: File must be large enough to hold CRC if not bypassed
                    if not sec.get('bypass_crc', False) and actual_len < 2:
                        return False, f"Error: File length ({actual_len}) is too small to embed CRC16 for section '{N}'."
                    
                    # Padding Logic: If is_full is True, buffer size becomes max_len, otherwise remains actual_len
                    buf_size = max_len if sec['is_full'] else actual_len
                    buf = bytearray([0xFF] * buf_size)
                    
                    for i in range(actual_len): 
                        buf[i] = int(lines[i], 16)
                        
                except Exception as e: 
                    return False, f"Error reading {sec['file_path']}: {e}"
            else: 
                # No file provided: Generate Random Data
                # Rule: Padding is forced to 1 (True), buffer size is exactly max_len
                # Rule: Random length generated must be <= max_len
                actual_len = random.randint(2, max_len) if max_len >= 2 else max_len
                buf = bytearray([0xFF] * max_len)
                for i in range(actual_len): 
                    buf[i] = random.getrandbits(8)
            
            buffers[N] = buf
            actual_lens[N] = actual_len

        # ---------------------------------------------------------
        # Phase 2: Cross-Section Parameter Injection (BEFORE CRC)
        # ---------------------------------------------------------
        for sec in self.sections:
            N = sec['name']
            
            # Legacy parameter injections
            T = sec['target_sec']
            if T and T in buffers:
                target_buf = buffers[T]
                if sec['size_offset'] != "":
                    off = int(sec['size_offset'])
                    if off < len(target_buf): target_buf[off] = actual_lens[N] & 0xFF
                    if off + 1 < len(target_buf): target_buf[off+1] = (actual_lens[N] >> 8) & 0xFF
                if sec['addr_offset'] != "":
                    off = int(sec['addr_offset'])
                    addr = sec['calc_addr']
                    if off < len(target_buf): target_buf[off] = addr & 0xFF
                    if off + 1 < len(target_buf): target_buf[off+1] = (addr >> 8) & 0xFF
                    if off + 2 < len(target_buf): target_buf[off+2] = (addr >> 16) & 0xFF
                if sec['en_offset'] != "" and sec['en_bit'] != "":
                    off = int(sec['en_offset'])
                    if off < len(target_buf):
                        bit = int(sec['en_bit']); val = int(sec['en_val'])
                        if val: target_buf[off] |= (1 << bit)
                        else: target_buf[off] &= ~(1 << bit)
                if sec['crc_offset'] != "" and sec['crc_bit'] != "":
                    off = int(sec['crc_offset'])
                    if off < len(target_buf):
                        bit = int(sec['crc_bit']); val = int(sec['crc_val'])
                        if val: target_buf[off] |= (1 << bit)
                        else: target_buf[off] &= ~(1 << bit)

            # Mask Injection (Dynamic Byte Length Calculation)
            M_Target = sec.get('mask_target', "")
            if M_Target and M_Target in buffers and sec.get('mask_offset', "") != "":
                mask_buf = buffers[M_Target]
                off = int(sec['mask_offset'])
                mask_val = int(sec.get('mask_val', 0))
                
                # Dynamic Byte Calculation: Determines the minimum bytes needed for mask (minimum 1 byte)
                byte_length = max(1, (mask_val.bit_length() + 7) // 8)
                
                # Little Endian Write into the Target Section
                for i in range(byte_length):
                    if off + i < len(mask_buf):
                        mask_buf[off + i] = (mask_val >> (i * 8)) & 0xFF

        # ---------------------------------------------------------
        # Phase 3: Exact CRC Calculation & Error Injection
        # ---------------------------------------------------------
        for sec in self.sections:
            N = sec['name']
            buf = buffers[N]
            L = actual_lens[N]  # Length strictly detected from file or random generator

            if not sec.get('bypass_crc', False) and L >= 2:
                # Calculate CRC on data strictly up to (L - 3)
                # Then place CRC into the exact positions: [L-2] and [L-1]
                crc_val = calculate_custom_crc16(buf[:L-2])

                # === CLI Mode: Display CRC Error Injection Info ===
                if sec.get('inject_err', False):
                    wrong_crc = crc_val ^ 0xFFFF  # Invert all 16 bits
                    print(f"[*] CRC Error Injection Detected for Section: '{N}'")
                    print(f"    ├── Correct CRC: 0x{crc_val:04X}")
                    print(f"    └── Injected CRC: 0x{wrong_crc:04X}")

                buf[L-2] = (crc_val >> 8) & 0xFF  # MSB
                buf[L-1] = crc_val & 0xFF         # LSB

                if sec.get('inject_err', False):
                    buf[L-1] ^= 0xFF  # XOR LSB to invert all bits

        # ---------------------------------------------------------
        # Phase 4: Write Final Output Hex
        # ---------------------------------------------------------
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for sec in self.sections:
                    N = sec['name']
                    for byte in buffers[N]: f.write(f"{byte:02X}\n")
            return True, f"Successfully generated HEX file:\n{output_file}"
        except Exception as e: return False, f"Write error: {str(e)}"


# =========================================================================
# Core 2: Single Map Register Viewer Backend 
# =========================================================================
class RegisterViewer:
    def __init__(self, treeview):
        self.tree = treeview
        self.current_map = []   
        self.current_buffer = None 

    def add_gap_to_map(self, gap_start, gap_end):
        """Helper to inject a calculated bit/byte gap into the display map."""
        low_addr = gap_start // 8
        loc_lsb = gap_start % 8
        high_addr = gap_end // 8
        loc_msb = gap_end % 8
        num_bits = gap_end - gap_start + 1
        
        self.current_map.append({
            'start_bit': gap_start,
            'high_addr': f"h{high_addr:04X}",
            'low_addr': f"h{low_addr:04X}",
            'loc_msb': str(loc_msb),
            'loc_lsb': str(loc_lsb),
            'name': "N/A",
            'msb': "", 'lsb': "", 'bits': str(num_bits),
            'init': "", 'rw': "",
            'display_desc': "N/A",
            'raw_desc': "N/A"
        })

    def process_and_map_excel(self, file_path):
        """Reads Excel, generates 256-byte buffer, and maps absolute bits for unified gaps."""
        try:
            df = pd.read_excel(file_path).fillna("")
            regs = []
            total_cols = len(df.columns)

            for idx, row in df.iterrows():
                if total_cols < 10: continue
                low_addr_int = parse_hex_address(row.iloc[1])
                high_addr_int = parse_hex_address(row.iloc[0])
                if low_addr_int < 0 or high_addr_int < 0: continue
                
                try: loc_msb = int(row.iloc[2])
                except ValueError: loc_msb = 7
                try: loc_lsb = int(row.iloc[3])
                except ValueError: loc_lsb = 0

                # Absolute bit tracking (from bit 0 up to bit 2031 for 254 bytes)
                start_bit = low_addr_int * 8 + loc_lsb
                end_bit = high_addr_int * 8 + loc_msb
                
                if end_bit < start_bit:
                    end_bit = start_bit
                
                raw_desc = str(row.iloc[10]).strip() if total_cols > 10 else ""
                display_desc = raw_desc.replace('\n', ' ↵ ').replace('\r', '')

                regs.append({
                    'start_bit': start_bit,
                    'end_bit': end_bit,
                    'high_int': high_addr_int,
                    'low_int': low_addr_int,
                    'high_addr': f"h{high_addr_int:04X}",
                    'low_addr': f"h{low_addr_int:04X}",
                    'loc_msb': str(loc_msb),
                    'loc_lsb': str(loc_lsb),
                    'name': str(row.iloc[4]).strip(),
                    'msb': str(row.iloc[5]).strip(),
                    'lsb': str(row.iloc[6]).strip(),
                    'bits': str(row.iloc[7]).strip(),
                    'init': str(row.iloc[8]).strip(),
                    'rw': str(row.iloc[9]).strip(),
                    'raw_desc': raw_desc,
                    'display_desc': display_desc
                })

            # 1. Fill 256-Byte Local Memory Map
            page_buffer = bytearray(256)
            for r in regs:
                init_str = r['init'].replace('h', '').replace('0x', '').strip()
                if not init_str: continue
                try:
                    init_val = int(init_str, 16)
                    shifted_val = init_val << int(r['loc_lsb'])
                    span = (r['high_int'] - r['low_int']) + 1
                    max_bytes = max(span, (shifted_val.bit_length() + 7) // 8)
                    for i in range(max_bytes):
                        if r['low_int'] + i < 254: 
                            page_buffer[r['low_int'] + i] |= ((shifted_val >> (i * 8)) & 0xFF)
                except ValueError: pass

            crc_val = calculate_custom_crc16(page_buffer[:254])
            page_buffer[254] = (crc_val >> 8) & 0xFF
            page_buffer[255] = crc_val & 0xFF
            self.current_buffer = page_buffer

            # 2. Build Structural UI Map (Absolute Bit-Index Tracking for Unified Gaps)
            used_bits = [False] * (254 * 8)
            valid_regs = [r for r in regs if r['low_int'] < 254]
            
            # Mark all defined absolute bits as True
            for r in valid_regs:
                sb = r['start_bit']
                eb = min(r['end_bit'], 254 * 8 - 1)
                if sb <= eb:
                    for b in range(sb, eb + 1):
                        used_bits[b] = True
                        
            self.current_map = []
            # Append valid defined registers
            for r in valid_regs:
                self.current_map.append(r)
                
            # Scan the boolean array to automatically consolidate any contiguous undefined bits into a single "N/A" gap
            in_gap = False
            gap_start = 0
            for b in range(254 * 8):
                if not used_bits[b] and not in_gap:
                    in_gap = True
                    gap_start = b
                elif used_bits[b] and in_gap:
                    in_gap = False
                    gap_end = b - 1
                    self.add_gap_to_map(gap_start, gap_end)
                    
            if in_gap:
                self.add_gap_to_map(gap_start, 254 * 8 - 1)
                
            # Sort the combined map by starting bit logically
            self.current_map.sort(key=lambda x: x.get('start_bit', 0))

            # Append the mandatory CRC field at the end (Absolute Bit index simulated as maximum)
            self.current_map.append({
                'start_bit': 999999,
                'high_addr': "h00FF", 'low_addr': "h00FE", 'loc_msb': "15", 'loc_lsb': "0", 'name': "AUTO_CRC16",
                'msb': "15", 'lsb': "0", 'bits': "16", 'init': f"h{crc_val:04X}", 'rw': "ro", 
                'raw_desc': f"Auto-calculated CRC16\nPoly: 0x8005\nInit: 0x0052", 
                'display_desc': f"Auto-calculated CRC16 (Poly: 0x8005, Init: 0x0052)"
            })

            self.update_treeview(self.current_map)
            return True, f"Mapped 0x00 to 0xFF. Calculated CRC: 0x{crc_val:04X}."
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error processing file: {e}"

    def update_treeview(self, final_map):
        """Renders the structural map into the UI Treeview."""
        for item in self.tree.get_children(): self.tree.delete(item)
        for idx, item in enumerate(final_map):
            values = (
                item.get('high_addr',""), item.get('low_addr',""), item.get('loc_msb',""), item.get('loc_lsb',""),
                item.get('name',""), item.get('msb',""), item.get('lsb',""), item.get('bits',""), 
                item.get('init',""), item.get('rw',""), item.get('display_desc',"")
            )
            # Unified Gap styling for both bit-level and byte-level undefined spaces
            if item['name'] == "N/A": 
                self.tree.insert("", "end", iid=str(idx), values=values, tags=('unified_gap',))
            elif item['name'] == "AUTO_CRC16": 
                self.tree.insert("", "end", iid=str(idx), values=values, tags=('crc',))
            else: 
                self.tree.insert("", "end", iid=str(idx), values=values, tags=('reg',))
            
        self.tree.tag_configure('unified_gap', background='#ffeeba', foreground='#856404') 
        self.tree.tag_configure('crc', background='#d4edda', foreground='#155724')
        self.tree.tag_configure('reg', background='#ffffff')


# =========================================================================
# Main GUI Application
# =========================================================================
class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Firmware Pipeline Studio (Ultimate Flagship Edition)")
        self.root.geometry("1450x950")

        style = ttk.Style()
        style.configure("Treeview", rowheight=25, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        # Global States
        self.packer = FirmwarePacker()
        self.integration_list = [] 
        
        self.integrated_hex_path = ""
        self.integrator_csv_path = "" 
        self.packer_csv_path = ""
        self.editing_idx = None 
        self.current_mask_val = 0 
        
        # Shared Dictionary for Tab 3 & 4 Sync
        self.shared_files = {}

        self.notebook = ttk.Notebook(root)
        self.tab_packer = ttk.Frame(self.notebook)
        self.tab_m0 = ttk.Frame(self.notebook)
        self.tab_integrator = ttk.Frame(self.notebook)
        self.tab_viewer = ttk.Frame(self.notebook)
        self.tab_test = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_packer, text="1. Firmware Packer")
        self.notebook.add(self.tab_m0, text="2. M0 HEX Converter")
        self.notebook.add(self.tab_integrator, text="3. Register Integrator")
        self.notebook.add(self.tab_viewer, text="4. Single Map Viewer")
        self.notebook.add(self.tab_test, text="5. Logic Test")
        self.notebook.pack(expand=1, fill="both")

        self.setup_packer_tab()
        self.setup_m0_tab()
        self.setup_integrator_tab()
        self.setup_viewer_tab()
        self.setup_test_tab()
        
        self.notebook.select(self.tab_packer)

    # ---------------------------------------------------------------------
    # TAB 1: FIRMWARE PACKER 
    # ---------------------------------------------------------------------
    def setup_packer_tab(self):
        ctrl_frame = tk.LabelFrame(self.tab_packer, text=" Step 1: Manage Sections & Configuration ", pady=5, padx=10)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        
        btn_frame1 = tk.Frame(ctrl_frame)
        btn_frame1.pack(side=tk.LEFT, fill=tk.Y)
        tk.Button(btn_frame1, text="📂 Load Config (.csv)", command=self.btn_packer_load_config, bg="#ffc107", width=18).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(btn_frame1, text="💾 Save Config (.csv)", command=self.btn_packer_save_config, bg="#20c997", fg="white", width=18).grid(row=0, column=1, padx=2, pady=2)

        btn_frame2 = tk.Frame(ctrl_frame)
        btn_frame2.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(btn_frame2, text="✏ Edit Selected", command=self.btn_packer_edit, bg="#007bff", fg="white", width=15).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(btn_frame2, text="- Remove Selected", command=self.btn_packer_remove, bg="#dc3545", fg="white", width=15).grid(row=0, column=1, padx=2, pady=2)
        tk.Button(btn_frame2, text="Clear List", command=self.clear_packer_list, bg="#6c757d", fg="white", width=15).grid(row=0, column=2, padx=2, pady=2)

        add_frame = tk.LabelFrame(self.tab_packer, text=" Step 2: Add / Edit Section ", padx=10, pady=10)
        add_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(add_frame, text="Section Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.ent_sec_name = tk.Entry(add_frame, width=30)
        self.ent_sec_name.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Maximum Length (Decimal):").grid(row=0, column=2, sticky="w", padx=20, pady=2)
        self.ent_sec_len = tk.Entry(add_frame, width=30)
        self.ent_sec_len.grid(row=0, column=3, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="File Path:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.ent_sec_path = tk.Entry(add_frame, width=30)
        self.ent_sec_path.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Target Header Section:").grid(row=1, column=2, sticky="w", padx=20, pady=2)
        self.ent_sec_target = tk.Entry(add_frame, width=30)
        self.ent_sec_target.grid(row=1, column=3, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Size Offset (Hexadecimal):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.ent_sec_size_off = tk.Entry(add_frame, width=30)
        self.ent_sec_size_off.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Address Offset (Hexadecimal):").grid(row=2, column=2, sticky="w", padx=20, pady=2)
        self.ent_sec_addr_off = tk.Entry(add_frame, width=30)
        self.ent_sec_addr_off.grid(row=2, column=3, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Enable Offset(Hex) / Bit / Value:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        f_en = tk.Frame(add_frame)
        f_en.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        self.ent_sec_en_off = tk.Entry(f_en, width=12); self.ent_sec_en_off.pack(side=tk.LEFT)
        tk.Label(f_en, text="/").pack(side=tk.LEFT)
        self.ent_sec_en_bit = tk.Entry(f_en, width=6); self.ent_sec_en_bit.pack(side=tk.LEFT)
        tk.Label(f_en, text="/").pack(side=tk.LEFT)
        self.ent_sec_en_val = tk.Entry(f_en, width=6); self.ent_sec_en_val.pack(side=tk.LEFT)

        tk.Label(add_frame, text="CRC Offset(Hex) / Bit / Value:").grid(row=3, column=2, sticky="w", padx=20, pady=2)
        f_crc = tk.Frame(add_frame)
        f_crc.grid(row=3, column=3, sticky="w", padx=5, pady=2)
        self.ent_sec_crc_off = tk.Entry(f_crc, width=12); self.ent_sec_crc_off.pack(side=tk.LEFT)
        tk.Label(f_crc, text="/").pack(side=tk.LEFT)
        self.ent_sec_crc_bit = tk.Entry(f_crc, width=6); self.ent_sec_crc_bit.pack(side=tk.LEFT)
        tk.Label(f_crc, text="/").pack(side=tk.LEFT)
        self.ent_sec_crc_val = tk.Entry(f_crc, width=6); self.ent_sec_crc_val.pack(side=tk.LEFT)

        # Mask Injection Fields
        tk.Label(add_frame, text="Mask Target Section:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.ent_sec_mask_target = tk.Entry(add_frame, width=30)
        self.ent_sec_mask_target.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Mask Offset(Hex) / Val(Hex):").grid(row=4, column=2, sticky="w", padx=20, pady=2)
        f_mask = tk.Frame(add_frame)
        f_mask.grid(row=4, column=3, sticky="w", padx=5, pady=2)
        self.ent_sec_mask_off = tk.Entry(f_mask, width=12); self.ent_sec_mask_off.pack(side=tk.LEFT)
        tk.Label(f_mask, text="/").pack(side=tk.LEFT)
        self.ent_sec_mask_val = tk.Entry(f_mask, width=12); self.ent_sec_mask_val.pack(side=tk.LEFT)

        # Checkboxes and Action Buttons
        f_chk = tk.Frame(add_frame)
        f_chk.grid(row=5, column=0, columnspan=2, sticky="w", padx=5, pady=10)
        self.var_sec_full = tk.BooleanVar(value=True)
        tk.Checkbutton(f_chk, text="Full Padding (0xFF)", variable=self.var_sec_full).pack(side=tk.LEFT)
        self.var_sec_err = tk.BooleanVar()
        tk.Checkbutton(f_chk, text="Inject CRC Error", variable=self.var_sec_err, fg="red").pack(side=tk.LEFT, padx=15)
        self.var_sec_bypass = tk.BooleanVar()
        tk.Checkbutton(f_chk, text="Bypass CRC Calc", variable=self.var_sec_bypass).pack(side=tk.LEFT, padx=15)

        f_actions = tk.Frame(add_frame)
        f_actions.grid(row=5, column=3, sticky="e", padx=5, pady=10)
        self.btn_manual_add = tk.Button(f_actions, text="+ Add Section", command=self.btn_manual_add_section, bg="#17a2b8", fg="white", font=("Arial", 10, "bold"), width=15)
        self.btn_manual_add.pack(side=tk.LEFT, padx=5)
        self.btn_manual_update = tk.Button(f_actions, text="✔ Update Section", command=self.btn_manual_update_section, bg="#ffc107", font=("Arial", 10, "bold"), width=15, state=tk.DISABLED)
        self.btn_manual_update.pack(side=tk.LEFT, padx=5)

        tree_frame = tk.Frame(self.tab_packer, padx=10, pady=5)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("Name", "Max Len", "Dynamic Addr", "Target Header", "Bypass CRC")
        self.packer_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.packer_tree.heading(col, text=col)
            self.packer_tree.column(col, anchor="center")
        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.packer_tree.yview)
        self.packer_tree.configure(yscroll=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.packer_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        order_frame = tk.Frame(self.tab_packer, padx=10, pady=10)
        order_frame.pack(fill=tk.X)
        tk.Button(order_frame, text="▲ Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        tk.Button(order_frame, text="▼ Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)
        
        tk.Button(order_frame, text="Generate Final HEX File", command=self.generate_firmware, bg="#28a745", fg="white", font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=5)
        tk.Button(order_frame, text="📋 Copy CLI Command", command=self.btn_copy_cli_command, bg="#000000", fg="#00ff00", font=("Courier", 11, "bold")).pack(side=tk.RIGHT, padx=15)

    def refresh_packer_tree(self):
        self.packer.calculate_addresses()
        for item in self.packer_tree.get_children(): self.packer_tree.delete(item)
        for idx, sec in enumerate(self.packer.sections):
            addr_hex = f"0x{sec['calc_addr']:06X}"
            target = sec['target_sec'] if sec['target_sec'] else "None"
            bypass = "Yes" if sec.get('bypass_crc', False) else "No"
            self.packer_tree.insert("", "end", iid=str(idx), values=(sec['name'], sec['max_len'], addr_hex, target, bypass))

    def clear_packer_form(self):
        self.ent_sec_name.delete(0, tk.END); self.ent_sec_len.delete(0, tk.END); self.ent_sec_path.delete(0, tk.END)
        self.ent_sec_target.delete(0, tk.END); self.ent_sec_size_off.delete(0, tk.END); self.ent_sec_addr_off.delete(0, tk.END)
        self.ent_sec_en_off.delete(0, tk.END); self.ent_sec_en_bit.delete(0, tk.END); self.ent_sec_en_val.delete(0, tk.END)
        self.ent_sec_crc_off.delete(0, tk.END); self.ent_sec_crc_bit.delete(0, tk.END); self.ent_sec_crc_val.delete(0, tk.END)
        self.ent_sec_mask_target.delete(0, tk.END); self.ent_sec_mask_off.delete(0, tk.END); self.ent_sec_mask_val.delete(0, tk.END)
        self.var_sec_full.set(True); self.var_sec_err.set(False); self.var_sec_bypass.set(False)
        self.btn_manual_add.config(state=tk.NORMAL); self.btn_manual_update.config(state=tk.DISABLED)
        self.editing_idx = None

    def _get_sec_dict_from_form(self):
        name = self.ent_sec_name.get().strip(); max_len_str = self.ent_sec_len.get().strip()
        if not name or not max_len_str: messagebox.showwarning("Warning", "Section Name and Maximum Length are required!"); return None
        try: max_len = int(max_len_str)
        except ValueError: messagebox.showwarning("Warning", "Maximum Length must be an integer!"); return None
        
        def safe_hex(val):
            v = val.strip().replace("0x", "").replace("0X", "")
            try: return int(v, 16) if v else ""
            except ValueError: return ""

        return {
            'name': name, 'max_len': max_len, 'file_path': self.ent_sec_path.get().strip(),
            'is_full': self.var_sec_full.get(), 'inject_err': self.var_sec_err.get(), 'target_sec': self.ent_sec_target.get().strip(),
            'size_offset': safe_hex(self.ent_sec_size_off.get()), 'size_offset_orig': self.ent_sec_size_off.get().strip(),
            'addr_offset': safe_hex(self.ent_sec_addr_off.get()), 'addr_offset_orig': self.ent_sec_addr_off.get().strip(),
            'en_offset': safe_hex(self.ent_sec_en_off.get()), 'en_offset_orig': self.ent_sec_en_off.get().strip(),
            'en_bit': int(self.ent_sec_en_bit.get()) if self.ent_sec_en_bit.get().strip() else "", 'en_val': int(self.ent_sec_en_val.get()) if self.ent_sec_en_val.get().strip() else 1,
            'crc_offset': safe_hex(self.ent_sec_crc_off.get()), 'crc_offset_orig': self.ent_sec_crc_off.get().strip(),
            'crc_bit': int(self.ent_sec_crc_bit.get()) if self.ent_sec_crc_bit.get().strip() else "", 'crc_val': int(self.ent_sec_crc_val.get()) if self.ent_sec_crc_val.get().strip() else 1,
            'mask_target': self.ent_sec_mask_target.get().strip(),
            'mask_offset': safe_hex(self.ent_sec_mask_off.get()), 'mask_offset_orig': self.ent_sec_mask_off.get().strip(),
            'mask_val': safe_hex(self.ent_sec_mask_val.get()),
            'calc_addr': 0, 'bypass_crc': self.var_sec_bypass.get()
        }

    def btn_manual_add_section(self):
        sec = self._get_sec_dict_from_form()
        if sec: self.packer.sections.append(sec); self.refresh_packer_tree(); self.clear_packer_form()

    def btn_manual_update_section(self):
        if self.editing_idx is None: return
        sec = self._get_sec_dict_from_form()
        if sec: self.packer.sections[self.editing_idx] = sec; self.refresh_packer_tree(); self.clear_packer_form()

    def btn_packer_edit(self):
        selected = self.packer_tree.selection()
        if not selected: return
        idx = int(selected[0]); self.editing_idx = idx; sec = self.packer.sections[idx]
        self.clear_packer_form(); self.editing_idx = idx   
        
        self.ent_sec_name.insert(0, sec['name']); self.ent_sec_len.insert(0, str(sec['max_len'])); self.ent_sec_path.insert(0, sec['file_path'])
        self.ent_sec_target.insert(0, sec['target_sec']); self.ent_sec_size_off.insert(0, sec['size_offset_orig']); self.ent_sec_addr_off.insert(0, sec['addr_offset_orig'])
        self.ent_sec_en_off.insert(0, sec['en_offset_orig']); self.ent_sec_en_bit.insert(0, str(sec['en_bit']) if sec['en_bit'] != "" else "")
        self.ent_sec_en_val.insert(0, str(sec['en_val']) if sec['en_val'] != "" else ""); self.ent_sec_crc_off.insert(0, sec['crc_offset_orig'])
        self.ent_sec_crc_bit.insert(0, str(sec['crc_bit']) if sec['crc_bit'] != "" else ""); self.ent_sec_crc_val.insert(0, str(sec['crc_val']) if sec['crc_val'] != "" else "")
        
        self.ent_sec_mask_target.insert(0, sec.get('mask_target', ''))
        self.ent_sec_mask_off.insert(0, sec.get('mask_offset_orig', ''))
        mask_v = sec.get('mask_val', '')
        self.ent_sec_mask_val.insert(0, f"{mask_v:X}" if type(mask_v)==int else str(mask_v))

        self.var_sec_full.set(sec['is_full']); self.var_sec_err.set(sec['inject_err']); self.var_sec_bypass.set(sec.get('bypass_crc', False))
        self.btn_manual_add.config(state=tk.DISABLED); self.btn_manual_update.config(state=tk.NORMAL)

    def btn_packer_save_config(self, auto_prompt=True):
        if not self.packer.sections:
            if auto_prompt: messagebox.showwarning("Warning", "No sections to save.")
            return False, ""
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Config", "*.csv")], initialfile="packer_config.csv")
        if save_path:
            success, msg = self.packer.save_csv_config(save_path)
            if success:
                self.packer_csv_path = save_path
                if auto_prompt: messagebox.showinfo("Success", f"Config saved to:\n{save_path}")
                return True, save_path
            else:
                if auto_prompt: messagebox.showerror("Error", msg)
        return False, ""

    def btn_packer_load_config(self):
        load_path = filedialog.askopenfilename(filetypes=[("CSV Config", "*.csv")])
        if not load_path: return
        success, msg = self.packer.load_csv_config(load_path)
        if success: self.packer_csv_path = load_path; self.refresh_packer_tree(); messagebox.showinfo("Success", msg)
        else: messagebox.showerror("Error", msg)

    def btn_packer_remove(self):
        selected = self.packer_tree.selection()
        if not selected: return
        indices = [int(item) for item in selected]; indices.sort(reverse=True)
        for idx in indices: del self.packer.sections[idx]
        self.refresh_packer_tree(); self.clear_packer_form()

    def move_up(self):
        selected = self.packer_tree.selection()
        if not selected: return
        idx = int(selected[0])
        if idx > 0:
            self.packer.sections[idx], self.packer.sections[idx-1] = self.packer.sections[idx-1], self.packer.sections[idx]
            self.refresh_packer_tree(); self.packer_tree.selection_set(str(idx-1))

    def move_down(self):
        selected = self.packer_tree.selection()
        if not selected: return
        idx = int(selected[0])
        if idx < len(self.packer.sections) - 1:
            self.packer.sections[idx], self.packer.sections[idx+1] = self.packer.sections[idx+1], self.packer.sections[idx]
            self.refresh_packer_tree(); self.packer_tree.selection_set(str(idx+1))

    def clear_packer_list(self):
        if messagebox.askyesno("Confirm", "Clear all sections?"):
            self.packer.sections = []; self.packer_csv_path = ""
            self.refresh_packer_tree(); self.clear_packer_form()

    def generate_firmware(self):
        if not self.packer.sections: return
        save_path = filedialog.asksaveasfilename(defaultextension=".hex", initialfile="all_crc.hex", filetypes=[("HEX File", "*.hex")])
        if save_path:
            success, msg = self.packer.generate_firmware_hex(save_path)
            if success: messagebox.showinfo("Success", msg)
            else: messagebox.showerror("Error", msg)

    def btn_copy_cli_command(self):
        if not self.packer.sections:
            messagebox.showwarning("Warning", "Please setup Tab 1 before generating CLI.")
            return
            
        if not self.packer_csv_path:
            if messagebox.askyesno("Config Required", "CLI needs a saved Packer CSV file.\nDo you want to save it now?"):
                success, config_path = self.btn_packer_save_config(auto_prompt=False)
                if not success: return
            else: return

        cli_reg = ""
        if self.integration_list and self.integrator_csv_path:
            base = self.ent_base_addr.get().strip()
            out = self.integrated_hex_path if self.integrated_hex_path else "All_Registers.hex"
            cli_reg = f' --reg_csv "{self.integrator_csv_path}" --reg_base {base} --reg_out "{out}"'

        cli_m0 = ""
        if hasattr(self, 'm0_file_path') and self.m0_file_path:
            out = self.m0_output_path if self.m0_output_path else "M0_fw.hex"
            cli_m0 = f' --m0_in "{self.m0_file_path}" --m0_out "{out}"'

        script_path = os.path.abspath(sys.argv[0])
        cmd = f'python "{script_path}" --cli --config "{self.packer_csv_path}" --output "all_crc.hex"{cli_m0}{cli_reg}'
        
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        messagebox.showinfo("Copied to Clipboard!", f"CLI Command ready:\n\n{cmd}\n\nPaste this into your Terminal to automate the entire build pipeline.")

    # ---------------------------------------------------------------------
    # TAB 2: M0 HEX CONVERTER
    # ---------------------------------------------------------------------
    def setup_m0_tab(self):
        frame = tk.LabelFrame(self.tab_m0, text=" M0 HEX to Firmware Converter ", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        tk.Label(frame, text="Supports Standard Intel HEX (.hex) OR Raw Space-Separated HEX (.txt/.hex)", font=("Arial", 11)).pack(pady=10)
        tk.Button(frame, text="1. Load M0 HEX File", command=self.btn_m0_load, bg="#007bff", fg="white", font=("Arial", 11, "bold"), width=30).pack(pady=10)
        self.lbl_m0_status = tk.Label(frame, text="File Status: No file loaded.", fg="gray", font=("Courier", 11)); self.lbl_m0_status.pack(pady=5)
        tk.Button(frame, text="2. Convert & Expand length (+2 Bytes for CRC)", command=self.btn_m0_convert, bg="#6f42c1", fg="white", font=("Arial", 11, "bold"), width=40).pack(pady=15)
        self.btn_m0_send = tk.Button(frame, text="3. Send to Firmware Packer ➡", command=self.btn_m0_send_packer, bg="#17a2b8", fg="white", font=("Arial", 11, "bold"), width=30, state=tk.DISABLED)
        self.btn_m0_send.pack(pady=10)

        self.m0_file_path = ""; self.m0_output_path = ""; self.m0_buffer = bytearray(); self.m0_orig_size = 0

    def btn_m0_load(self):
        filepath = filedialog.askopenfilename(filetypes=[("HEX Files", "*.hex *.txt"), ("All Files", "*.*")])
        if not filepath: return
        success, buf, orig_size = parse_m0_hex_file(filepath)
        if success:
            self.m0_file_path = filepath; self.m0_buffer = buf; self.m0_orig_size = orig_size
            self.lbl_m0_status.config(text=f"Loaded: {os.path.basename(filepath)}\nOriginal Payload Size: {orig_size} Bytes", fg="green")
        else:
            messagebox.showerror("Parse Error", "Failed to parse HEX file. Ensure format is correct.")
            self.lbl_m0_status.config(text="Error parsing file.", fg="red")

    def btn_m0_convert(self):
        if not self.m0_file_path: return
        expanded_buffer = bytearray(self.m0_buffer)
        expanded_buffer.extend([0xFF, 0xFF]) # Append 2 dummy bytes for future CRC
        expanded_size = self.m0_orig_size + 2
        
        default_name = os.path.basename(self.m0_file_path).replace('.hex', '').replace('.txt', '') + "_fw.hex"
        save_path = filedialog.asksaveasfilename(defaultextension=".hex", initialfile=default_name, filetypes=[("Raw 1-byte HEX", "*.hex")])
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    for byte in expanded_buffer: f.write(f"{byte:02X}\n")
                self.m0_output_path = save_path; self.btn_m0_send.config(state=tk.NORMAL)
                messagebox.showinfo("Success", f"File converted successfully.\nExpanded Length: {expanded_size} Bytes\nSaved to: {save_path}")
            except Exception as e: messagebox.showerror("Write Error", str(e))

    def btn_m0_send_packer(self):
        if not self.m0_output_path: return
        total_len = self.m0_orig_size + 2
        name = os.path.basename(self.m0_file_path).replace('.hex', '').replace('.txt', '').upper()
        sec = {
            'name': name, 'max_len': total_len, 'file_path': self.m0_output_path, 'is_full': True, 'inject_err': False, 'target_sec': "", 
            'size_offset': "", 'size_offset_orig': "", 'en_offset': "", 'en_offset_orig': "", 'en_bit': "", 'en_val': 1, 
            'crc_offset': "", 'crc_offset_orig': "", 'crc_bit': "", 'crc_val': 1, 'addr_offset': "", 'addr_offset_orig': "", 'calc_addr': 0, 
            'bypass_crc': False # DO NOT bypass. CRC will be calculated on the detected length in Tab 1
        }
        self.packer.sections.append(sec); self.refresh_packer_tree()
        self.packer_tree.selection_set(str(len(self.packer.sections) - 1)); self.btn_packer_edit() 
        self.notebook.select(self.tab_packer)
        messagebox.showinfo("Success", f"Section '{name}' added to Packer.\nYou can now configure Target Header and click 'Update Section'.")

    # ---------------------------------------------------------------------
    # TAB 3: REGISTER INTEGRATOR (With Enable Mask Injection)
    # ---------------------------------------------------------------------
    def setup_integrator_tab(self):
        load_frame = tk.LabelFrame(self.tab_integrator, text=" Step 1: Manage Register Tables & Configuration ", padx=10, pady=10)
        load_frame.pack(fill=tk.X, padx=10, pady=5)
        btn_frame = tk.Frame(load_frame); btn_frame.pack(side=tk.LEFT)
        row0 = tk.Frame(btn_frame); row0.pack(fill=tk.X, pady=2)
        tk.Button(row0, text="+ Add Excel File(s)", command=self.btn_int_add_files, bg="#007bff", fg="white", width=20).pack(side=tk.LEFT, padx=2)
        tk.Button(row0, text="- Remove Selected", command=self.btn_int_remove, bg="#dc3545", fg="white", width=20).pack(side=tk.LEFT, padx=2)
        row1 = tk.Frame(btn_frame); row1.pack(fill=tk.X, pady=2)
        tk.Button(row1, text="📂 Load Config (.csv)", command=self.btn_int_load_config, bg="#ffc107", width=20).pack(side=tk.LEFT, padx=2)
        tk.Button(row1, text="💾 Save Config (.csv)", command=self.btn_int_save_config, bg="#20c997", fg="white", width=20).pack(side=tk.LEFT, padx=2)

        self.lbl_mask = tk.Label(load_frame, text="Enable Mask: 0x0000 (1 byte)", fg="#d35400", font=("Courier", 14, "bold"))
        self.lbl_mask.pack(side=tk.RIGHT, padx=15)
        
        # NEW: Label for mask byte length
        self.lbl_mask_bytes = tk.Label(load_frame, text="Mask Bytes: 1", fg="#27ae60", font=("Courier", 10, "bold"))
        self.lbl_mask_bytes.pack(side=tk.RIGHT, padx=15)
        
        # Debug label for bit mapping visualization
        self.lbl_mask_debug = tk.Label(load_frame, text="Bit Mapping: ", fg="#666666", font=("Courier", 9))
        self.lbl_mask_debug.pack(side=tk.RIGHT, padx=15)

        tree_frame = tk.Frame(self.tab_integrator, padx=10, pady=5); tree_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(tree_frame, text="💡 Tip: Double-click any row to view its complete Memory Map in Tab 4.", fg="gray").pack(anchor="w")

        columns = ("Name", "Flash Address (Hex)", "Enabled", "Status")
        self.int_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns: self.int_tree.heading(col, text=col); self.int_tree.column(col, anchor="center")
        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.int_tree.yview)
        self.int_tree.configure(yscroll=scroll_y.set); scroll_y.pack(side=tk.RIGHT, fill=tk.Y); self.int_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.int_tree.bind("<<TreeviewSelect>>", self.on_int_tree_select); self.int_tree.bind("<Double-1>", self.on_int_tree_double_click_goto)

        edit_frame = tk.LabelFrame(self.tab_integrator, text=" Step 2: Edit Selected Table ", padx=10, pady=10)
        edit_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(edit_frame, text="Flash Address (Hex):").pack(side=tk.LEFT, padx=5)
        self.ent_flash_addr_int = tk.Entry(edit_frame, width=15); self.ent_flash_addr_int.pack(side=tk.LEFT, padx=5)
        self.var_enable_int = tk.BooleanVar()
        tk.Checkbutton(edit_frame, text="Enable (Include in Mask)", variable=self.var_enable_int).pack(side=tk.LEFT, padx=15)
        tk.Button(edit_frame, text="Update Row", command=self.btn_int_update_row, bg="#ffc107", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        action_frame = tk.LabelFrame(self.tab_integrator, text=" Step 3: Generate & Export ", padx=10, pady=10)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Mask Injection Config
        mask_frame = tk.Frame(action_frame)
        mask_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(mask_frame, text="Global Base Address (Hex): 0x").pack(side=tk.LEFT, padx=5)
        self.ent_base_addr = tk.Entry(mask_frame, width=10); self.ent_base_addr.insert(0, "0000"); self.ent_base_addr.pack(side=tk.LEFT, padx=5)
        
        tk.Label(mask_frame, text=" |  Mask Target Section:").pack(side=tk.LEFT, padx=5)
        self.ent_int_mask_target = tk.Entry(mask_frame, width=10); self.ent_int_mask_target.insert(0, "SYS"); self.ent_int_mask_target.pack(side=tk.LEFT, padx=5)
        tk.Label(mask_frame, text="Mask Offset (Hex): 0x").pack(side=tk.LEFT, padx=5)
        self.ent_int_mask_off = tk.Entry(mask_frame, width=10); self.ent_int_mask_off.pack(side=tk.LEFT, padx=5)

        # Actions
        btn_action_frame = tk.Frame(action_frame)
        btn_action_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(btn_action_frame, text="1. Generate Integrated HEX", command=self.btn_int_generate, bg="#6f42c1", fg="white", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=5)
        self.btn_int_send = tk.Button(btn_action_frame, text="2. Send to Firmware Packer ➡", command=self.btn_int_send_packer, bg="#17a2b8", fg="white", font=("Arial", 11, "bold"), state=tk.DISABLED)
        self.btn_int_send.pack(side=tk.LEFT, padx=15)

    def btn_int_add_files(self):
        """Add Excel files with auto-alignment to base address."""
        files = filedialog.askopenfilenames(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not files: return
        
        try:
            base_addr = int(self.ent_base_addr.get().strip(), 16)
        except ValueError:
            base_addr = 0
        
        added_count = 0
        for f in files:
            name = os.path.basename(f); self.shared_files[name] = f
            success, buffer = parse_register_excel_to_buffer(f)
            status = "Parsed + CRC" if success else "Error Parsing"
            
            # NEW: Default address starts at base_addr (auto-aligned)
            initial_addr = base_addr
            self.integration_list.append({
                "name": name, 
                "path": f, 
                "addr": initial_addr,  # Start at base address
                "enabled": True, 
                "buffer": buffer, 
                "status": status,
                "bit_position": 0
            })
            added_count += 1
        
        print(f"[+] Added {added_count} table(s) with base-aligned initial addresses")
        self.refresh_int_tree(); self.update_view_combobox() 

    def btn_int_remove(self):
        selected = self.int_tree.selection()
        if not selected: return
        indices = [int(item) for item in selected]; indices.sort(reverse=True)
        for idx in indices: del self.integration_list[idx]
        self.refresh_int_tree()

    def btn_int_save_config(self):
        if not self.integration_list: return
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Config", "*.csv")])
        if save_path:
            data = []
            base_dir = os.path.dirname(save_path)
            for item in self.integration_list:
                try: rel_path = os.path.relpath(item['path'], start=base_dir)
                except ValueError: rel_path = item['path'] 
                data.append({"Name": item['name'], "Relative_Path": rel_path, "Address_Hex": f"0x{item['addr']:04X}", "Enabled": "Yes" if item['enabled'] else "No"})
            try: pd.DataFrame(data).to_csv(save_path, index=False); self.integrator_csv_path = save_path; messagebox.showinfo("Success", f"Config saved to:\n{save_path}")
            except Exception as e: messagebox.showerror("Error", str(e))

    def btn_int_load_config(self):
        load_path = filedialog.askopenfilename(filetypes=[("CSV Config", "*.csv")])
        if not load_path: return
        base_dir = os.path.dirname(load_path)
        try:
            df = pd.read_csv(load_path).fillna("")
            new_list = []
            for idx, row in df.iterrows():
                name = str(row.get("Name", "")); rel_path = str(row.get("Relative_Path", ""))
                addr_str = str(row.get("Address_Hex", "0")).replace("0x", ""); enabled_str = str(row.get("Enabled", "Yes")).strip().lower()
                if not rel_path: continue
                full_path = os.path.normpath(os.path.join(base_dir, rel_path))
                success, buffer = parse_register_excel_to_buffer(full_path)
                try: addr_int = int(addr_str, 16)
                except ValueError: addr_int = 0
                is_enabled = True if enabled_str in ["yes", "true", "1", "y"] else False
                actual_name = name if name else os.path.basename(full_path)
                new_list.append({"name": actual_name, "path": full_path, "addr": addr_int, "enabled": is_enabled, "buffer": buffer, "status": "Parsed + CRC" if success else "Error Parsing"})
                self.shared_files[actual_name] = full_path
            self.integration_list = new_list; self.integrator_csv_path = load_path; self.refresh_int_tree(); self.update_view_combobox()
            messagebox.showinfo("Success", f"Loaded config with {len(self.integration_list)} tables.")
        except Exception as e: messagebox.showerror("Error", str(e))

    def refresh_int_tree(self):
        # Sort by Flash Address (required for correct bit mapping)
        self.integration_list.sort(key=lambda x: x['addr'])
        
        # Get base address from UI
        try:
            base_addr = int(self.ent_base_addr.get().strip(), 16)
        except ValueError:
            base_addr = 0
        
        # NEW: Validate and auto-align all addresses on refresh
        adjustments = []
        for item in self.integration_list:
            old_addr = item['addr']
            item['addr'], was_adjusted, warning = validate_and_align_flash_address(item['addr'], base_addr)
            if was_adjusted:
                adjustments.append({
                    'name': item['name'],
                    'old': old_addr,
                    'new': item['addr'],
                    'warning': warning
                })
        
        # Show adjustment dialog if any addresses were auto-aligned
        if adjustments:
            adj_text = "\n".join([f"• {a['name']}: 0x{a['old']:04X} → 0x{a['new']:04X}" + (f"\n  {a['warning']}" if a['warning'] else "") for a in adjustments])
            # Only show first 5 adjustments to avoid long dialogs
            if len(adjustments) > 5:
                adj_text += f"\n... and {len(adjustments) - 5} more auto-alignments"
            print(f"[Auto-Align] {len(adjustments)} table(s) auto-aligned to base address")
        
        # Build mask based on ADDRESS GAP from Base with dynamic byte length
        enabled_items = [item for item in self.integration_list if item['enabled']]
        
        if enabled_items:
            max_addr = max(item['addr'] for item in enabled_items)
            mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
            
            # Calculate mask value (gaps automatically = 0)
            mask = 0
            for item in enabled_items:
                bit_position = (item['addr'] - base_addr) // 256
                if 0 <= bit_position < 128:  # Support up to 128 bits
                    mask |= (1 << bit_position)
                    item['bit_position'] = bit_position
                else:
                    item['bit_position'] = -1
        else:
            mask = 0
            mask_bytes = 1
            total_bits = 0
        
        self.current_mask_val = mask
        self.current_mask_bytes = mask_bytes  # NEW: Store byte length for GUI display
        self.lbl_mask.config(text=f"Enable Mask: 0x{mask:0{mask_bytes*2}X} ({mask_bytes} byte(s))")
        self.lbl_mask_bytes.config(text=f"Mask Bytes: {mask_bytes}")
        
        # Debug info for understanding the bit mapping
        self._debug_mask_mapping()
        
    def _debug_mask_mapping(self):
        """Display detailed bit-to-address mapping for debugging with gap detection."""
        # Get base address from UI
        try:
            base_addr = int(self.ent_base_addr.get().strip(), 16)
        except ValueError:
            base_addr = 0
            
        # Sort by address for mapping display
        sorted_list = sorted(self.integration_list, key=lambda x: x['addr'])
        
        debug_parts = []
        gap_indicators = []
        last_end = base_addr
        
        for item in sorted_list:
            addr = item['addr']
            bit_pos = (addr - base_addr) // 256
            name = item['name'][:8]  # Truncate name for display
            
            # Detect gap before this table
            if addr > last_end + 256:
                gap_size = (addr - last_end) // 256
                gap_indicators.append(f"Gap({gap_size})")
            
            if item['enabled'] and 0 <= bit_pos < 128:
                debug_parts.append(f"B{bit_pos}:0x{addr:04X}")
            else:
                status = "ENABLED" if item['enabled'] else "DIS"
                debug_parts.append(f"-:0x{addr:04X}")  # '-' means disabled or out of range
            
            last_end = max(last_end, addr + 256)
        
        # Show gaps in debug
        if gap_indicators:
            gap_text = " | ".join(gap_indicators[:4])
            if hasattr(self, 'lbl_mask_debug'):
                self.lbl_mask_debug.config(text=f"Map: {debug_parts[:6]} | Gaps: {gap_text}")
        else:
            if hasattr(self, 'lbl_mask_debug'):
                self.lbl_mask_debug.config(text=f"Map: {' | '.join(debug_parts[:8])}")
        
        # Real-time GUI Sync: Update Mask in Packer Sections actively
        mask = self.current_mask_val
        for sec in self.packer.sections:
            if sec.get('mask_target', '').strip() != '':
                sec['mask_val'] = mask
                
        # If user is currently editing a section in Tab 1, update the form
        if self.editing_idx is not None and self.packer.sections[self.editing_idx].get('mask_target', '').strip() != '':
            self.ent_sec_mask_val.delete(0, tk.END)
            byte_len = getattr(self, 'current_mask_bytes', 1)
            self.ent_sec_mask_val.insert(0, f"{mask:0{byte_len*2}X}")
        
        for item in self.int_tree.get_children(): self.int_tree.delete(item)
        for idx, item in enumerate(self.integration_list):
            bit_info = ""
            if item.get('bit_position', None) is not None and item['bit_position'] >= 0:
                bit_info = f" [Bit{item['bit_position']}]"
            self.int_tree.insert("", "end", iid=str(idx), 
                values=(item['name'], f"0x{item['addr']:04X}", "Yes" if item['enabled'] else "No", item['status'] + bit_info))

    def on_int_tree_select(self, event):
        selected = self.int_tree.selection()
        if not selected: return
        item = self.integration_list[int(selected[0])]
        self.ent_flash_addr_int.delete(0, tk.END); self.ent_flash_addr_int.insert(0, f"{item['addr']:04X}")
        self.var_enable_int.set(item['enabled'])

    def on_int_tree_double_click_goto(self, event):
        selected = self.int_tree.selection()
        if not selected: return
        self.notebook.select(self.tab_viewer); self.update_view_combobox(auto_select=self.integration_list[int(selected[0])]['name'])

    def btn_int_update_row(self):
        selected = self.int_tree.selection()
        if not selected: return
        idx = int(selected[0])
        try: self.integration_list[idx]['addr'] = int(self.ent_flash_addr_int.get().strip(), 16)
        except ValueError: messagebox.showerror("Error", "Invalid Hex Address!"); return
        self.integration_list[idx]['enabled'] = self.var_enable_int.get()
        self.refresh_int_tree()

    def btn_int_generate(self):
        """Generate integrated HEX with new logic:
        1. Validate and auto-align all addresses
        2. Calculate dynamic mask bytes based on max address
        3. Fill gaps with 0xFF
        """
        enabled_items = [item for item in self.integration_list if item['enabled']]
        if not enabled_items: messagebox.showwarning("Warning", "No tables are enabled!"); return
        
        try: 
            base_addr = int(self.ent_base_addr.get().strip(), 16)
        except ValueError: 
            messagebox.showerror("Error", "Invalid Global Base Address!"); 
            return
        
        # NEW: Validate and auto-align all enabled items
        alignment_log = []
        for item in enabled_items:
            old_addr = item['addr']
            item['addr'], was_adjusted, warning = validate_and_align_flash_address(item['addr'], base_addr)
            if was_adjusted:
                alignment_log.append(f"• {item['name']}: 0x{old_addr:04X} → 0x{item['addr']:04X}")
        
        if alignment_log:
            log_text = "\n".join(alignment_log[:10])
            if len(alignment_log) > 10:
                log_text += f"\n... and {len(alignment_log) - 10} more"
            print(f"[Auto-Align] {len(alignment_log)} table(s) auto-aligned")
        
        enabled_items.sort(key=lambda x: x['addr'])
        
        # NEW: Calculate dynamic mask bytes based on max address
        max_addr = max([item['addr'] for item in enabled_items])
        mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        
        # Calculate total output size (includes gap padding)
        total_size = (max_addr - base_addr) + 256 
        
        # NEW: Initialize buffer with 0xFF (gaps will be 0xFF)
        integrated_buffer = bytearray([0xFF] * total_size) 
        
        # NEW: Detect and report gaps
        gaps = detect_flash_address_gaps(enabled_items, base_addr, max_addr)
        gap_report = ""
        if len(gaps) > 1:  # More than just the potential end gap
            gap_report = f"\nGap areas detected: {len(gaps)} (filled with 0xFF)"
        
        # Fill in enabled tables (gaps remain as 0xFF)
        placement_log = []
        for item in enabled_items:
            start = item['addr'] - base_addr
            integrated_buffer[start:start+256] = item['buffer']
            placement_log.append(f"0x{item['addr']:04X}")
        
        save_path = filedialog.asksaveasfilename(defaultextension=".hex", initialfile="All_Registers.hex", filetypes=[("HEX File", "*.hex")])
        if save_path:
            try:
                with open(save_path, 'w') as f:
                    for byte in integrated_buffer: f.write(f"{byte:02X}\n")
                self.integrated_hex_path = save_path; self.btn_int_send.config(state=tk.NORMAL)
                
                # NEW: Enhanced success message
                success_msg = (
                    f"Integrated HEX saved to:\n{save_path}\n\n"
                    f"Base Address: 0x{base_addr:04X}\n"
                    f"Max Address: 0x{max_addr:04X}\n"
                    f"Total Size: {total_size} bytes\n"
                    f"Enable Bits: {total_bits}\n"
                    f"Mask Bytes: {mask_bytes}\n"
                    f"Tables placed at: {', '.join(placement_log[:5])}"
                )
                if len(placement_log) > 5:
                    success_msg += f"\n... and {len(placement_log) - 5} more"
                if gap_report:
                    success_msg += gap_report
                    
                messagebox.showinfo("Success", success_msg)
            except Exception as e: messagebox.showerror("Error", str(e))

    def btn_int_send_packer(self):
        if not self.integrated_hex_path: return
        with open(self.integrated_hex_path, 'r') as f: file_size = sum(1 for line in f if line.strip())
        
        mask_target = self.ent_int_mask_target.get().strip()
        mask_offset = self.ent_int_mask_off.get().strip()
        
        # Pass safe hex string representation
        mask_offset_str = mask_offset.replace('0x', '')
        try: mask_off_int = int(mask_offset_str, 16) if mask_offset_str else ""
        except ValueError: mask_off_int = ""
        
        sec = {
            'name': "ALL_REGISTERS", 'max_len': file_size, 'file_path': self.integrated_hex_path,
            'is_full': True, 'inject_err': False, 'target_sec': "", 'size_offset': "", 'size_offset_orig': "", 
            'en_offset': "", 'en_offset_orig': "", 'en_bit': "", 'en_val': 1, 'crc_offset': "", 'crc_offset_orig': "", 
            'crc_bit': "", 'crc_val': 1, 'addr_offset': "", 'addr_offset_orig': "", 'calc_addr': 0, 
            'mask_target': mask_target, 'mask_offset': mask_off_int, 'mask_offset_orig': mask_offset_str, 
            'mask_val': self.current_mask_val,
            'bypass_crc': True 
        }
        self.packer.sections.append(sec); self.refresh_packer_tree()
        self.packer_tree.selection_set(str(len(self.packer.sections) - 1)); self.btn_packer_edit() 
        self.notebook.select(self.tab_packer)

    # ---------------------------------------------------------------------
    # TAB 4: SINGLE MAP VIEWER UI 
    # ---------------------------------------------------------------------
    def setup_viewer_tab(self):
        ctrl_frame = tk.LabelFrame(self.tab_viewer, text=" Viewer Controls (Synced with Integrator) ", padx=10, pady=10)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(ctrl_frame, text="Select Target Table:").pack(side=tk.LEFT, padx=5)
        self.combo_viewer_files = ttk.Combobox(ctrl_frame, width=50, state="readonly"); self.combo_viewer_files.pack(side=tk.LEFT, padx=5)
        self.combo_viewer_files.bind("<<ComboboxSelected>>", self.on_view_combo_select)
        tk.Button(ctrl_frame, text="Export Table to TXT", command=self.btn_view_export_txt, bg="#6f42c1", fg="white", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=5)

        tree_frame = tk.Frame(self.tab_viewer, padx=10, pady=5); tree_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("High Address", "Low Address", "Loc MSB", "Loc LSB", "Name", "MSB", "LSB", "Bits", "Init", "r/w", "Description")
        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL); scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        self.viewer_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.viewer_tree.yview); scroll_x.config(command=self.viewer_tree.xview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y); scroll_x.pack(side=tk.BOTTOM, fill=tk.X); self.viewer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for col in columns: self.viewer_tree.heading(col, text=col); self.viewer_tree.column(col, width=200 if col in ["Name", "Description"] else 85, anchor="center" if col not in ["Name", "Description"] else "w")
        
        self.viewer = RegisterViewer(self.viewer_tree)
        self.viewer_tree.bind("<<TreeviewSelect>>", self.on_view_tree_select)

        details_frame = tk.LabelFrame(self.tab_viewer, text=" Selected Register Details ", padx=10, pady=10); details_frame.pack(fill=tk.X, padx=10, pady=10)
        self.txt_details = tk.Text(details_frame, height=5, wrap=tk.WORD, bg="#f8f9fa", font=("Courier", 10)); self.txt_details.pack(fill=tk.BOTH, expand=True); self.txt_details.config(state=tk.DISABLED) 

    def update_view_combobox(self, auto_select=None):
        file_list = [item['name'] for item in self.integration_list]
        self.combo_viewer_files['values'] = file_list
        if auto_select and auto_select in file_list: self.combo_viewer_files.set(auto_select); self.on_view_combo_select(None)
        elif len(file_list) > 0 and not self.combo_viewer_files.get(): self.combo_viewer_files.current(0); self.on_view_combo_select(None)
        elif not file_list: self.combo_viewer_files.set(''); self.viewer.update_treeview([])

    def on_view_combo_select(self, event):
        selected_name = self.combo_viewer_files.get().strip()
        if not selected_name: return
        target_item = next((item for item in self.integration_list if item['name'] == selected_name), None)
        if target_item:
            success, msg = self.viewer.process_and_map_excel(target_item['path'])
            if success: self.txt_details.config(state=tk.NORMAL); self.txt_details.delete("1.0", tk.END); self.txt_details.config(state=tk.DISABLED)

    def on_view_tree_select(self, event):
        selected = self.viewer_tree.selection()
        if not selected: return
        idx = int(selected[0]); raw_data = self.viewer.current_map[idx]
        detail_text = f"Name : {raw_data.get('name','')}\nAddr : {raw_data.get('high_addr','')} ~ {raw_data.get('low_addr','')}\nBits : {raw_data.get('bits','')} bit(s) [MSB: {raw_data.get('msb','')} | LSB: {raw_data.get('lsb','')}]\nInit : {raw_data.get('init','')}  |  R/W: {raw_data.get('rw','')}\n" + "-" * 60 + "\nDescription:\n" + str(raw_data.get('raw_desc','')) + "\n"
        self.txt_details.config(state=tk.NORMAL); self.txt_details.delete("1.0", tk.END); self.txt_details.insert(tk.END, detail_text); self.txt_details.config(state=tk.DISABLED)

    def setup_test_tab(self):
        """Setup Test Tab"""
        self.test_controller = TestTabController(self.tab_test, self)
    
    def btn_view_export_txt(self):
        if self.viewer.current_buffer is None: return
        default_name = self.combo_viewer_files.get().strip().replace('.xlsx', '').replace('.xls', '') + "_init.txt"
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=default_name, filetypes=[("Text Files", "*.txt")])
        if save_path:
            try:
                with open(save_path, 'w') as f:
                    for byte in self.viewer.current_buffer: f.write(f"{byte:02X}\n")
                messagebox.showinfo("Success", f"Table exported to:\n{save_path}")
            except Exception as e: messagebox.showerror("Error", str(e))



# =========================================================================
# Core 3: Test Tab - Logic Verification & Demo
# =========================================================================
class TestTabController:
    """Controller for Test Tab functionality"""
    
    def __init__(self, parent_frame, app_ref):
        self.parent = parent_frame
        self.app = app_ref
        self.test_results = []
        self.setup_ui()
    
    def setup_ui(self):
        """Setup Test Tab UI"""
        # Title
        title_frame = tk.Frame(self.parent)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(title_frame, text="Tab3 Register Integrator Logic Test Suite", 
                 font=("Arial", 14, "bold"), fg="#2c3e50").pack(side=tk.LEFT)
        
        # Test Scenario Frame
        scenario_frame = tk.LabelFrame(self.parent, text=" Test Scenario Setup ", padx=15, pady=10)
        scenario_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Base Address
        tk.Label(scenario_frame, text="Base Address (Hex): 0x").pack(side=tk.LEFT, padx=5)
        self.ent_test_base = tk.Entry(scenario_frame, width=10)
        self.ent_test_base.insert(0, "1000")
        self.ent_test_base.pack(side=tk.LEFT, padx=5)
        
        # Test Tables Section
        tables_frame = tk.LabelFrame(self.parent, text=" Test Tables ", padx=10, pady=5)
        tables_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Table for test tables
        cols = ("Name", "Flash Address (Hex)", "Enabled")
        self.test_table_tree = ttk.Treeview(tables_frame, columns=cols, show="headings", height=6)
        for col in cols:
            self.test_table_tree.heading(col, text=col)
            self.test_table_tree.column(col, anchor="center")
        scroll_y = ttk.Scrollbar(tables_frame, orient=tk.VERTICAL, command=self.test_table_tree.yview)
        self.test_table_tree.configure(yscroll=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.test_table_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Add/Remove buttons
        btn_frame = tk.Frame(tables_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="+ Add Table", command=self.add_test_table, 
                  bg="#27ae60", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="- Remove Selected", command=self.remove_test_table, 
                  bg="#e74c3c", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Load Preset", command=self.load_preset, 
                  bg="#3498db", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        
        # Control Buttons
        control_frame = tk.Frame(self.parent)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(control_frame, text="▶ Run All Tests", command=self.run_all_tests,
                  bg="#9b59b6", fg="white", font=("Arial", 11, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="🔄 Run Single Test", command=self.run_single_test,
                  bg="#f39c12", fg="white", font=("Arial", 10), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="📊 Show Mask Calc", command=self.show_mask_calc,
                  bg="#16a085", fg="white", font=("Arial", 10), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="🧹 Clear Results", command=self.clear_results,
                  bg="#95a5a6", fg="white", width=12).pack(side=tk.RIGHT, padx=5)
        
        # Results Frame
        results_frame = tk.LabelFrame(self.parent, text=" Test Results ", padx=10, pady=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Text widget for results
        self.txt_results = tk.Text(results_frame, wrap=tk.WORD, bg="#1e1e1e", fg="#00ff00", 
                                   font=("Courier", 10), insertbackground="white")
        scroll_y_res = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.txt_results.yview)
        self.txt_results.configure(yscroll=scroll_y_res.set)
        scroll_y_res.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_results.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Status Bar
        self.status_bar = tk.Label(self.parent, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Initialize with preset tables
        self.load_preset()
    
    def load_preset(self):
        """Load preset test tables"""
        self.test_table_tree.delete()
        preset_tables = [
            ("Table_A", "1000", True),
            ("Table_B", "1300", True),
            ("Table_C", "2000", True),
        ]
        for name, addr, enabled in preset_tables:
            self.test_table_tree.insert("", "end", values=(name, addr, "Yes" if enabled else "No"))
        self.update_status("Preset loaded: 3 tables")
    
    def add_test_table(self):
        """Add a new test table"""
        try:
            base_addr = int(self.ent_test_base.get(), 16)
        except ValueError:
            base_addr = 0x1000
        
        child_count = len(self.test_table_tree.get_children())
        default_name = f"Table_{child_count + 1}"
        default_addr = (child_count * 256 + base_addr)
        default_addr_hex = f"{default_addr:04X}"
        self.test_table_tree.insert("", "end", values=(default_name, default_addr_hex, "Yes"))
        self.update_status(f"Added: {default_name}")
    
    def remove_test_table(self):
        """Remove selected test table"""
        selected = self.test_table_tree.selection()
        if selected:
            self.test_table_tree.delete(selected)
            self.update_status("Table removed")
    
    def get_test_tables(self):
        """Get all test tables as list"""
        tables = []
        for item in self.test_table_tree.get_children():
            values = self.test_table_tree.item(item)["values"]
            if len(values) < 3:
                continue
            name, addr_str, enabled = values[0], values[1], values[2]
            # 確保所有值都是字符串
            name = str(name) if name else ""
            addr_str = str(addr_str) if addr_str else "0"
            enabled = str(enabled) if enabled else "No"
            try:
                addr = int(addr_str, 16)
            except (ValueError, AttributeError):
                addr = 0
            tables.append({
                'name': name,
                'addr': addr,
                'enabled': enabled.lower() == "yes"
            })
        return tables
    
    def update_status(self, msg):
        """Update status bar"""
        self.status_bar.config(text=f"Status: {msg}")
        self.parent.update()
    
    def log(self, msg, color=None):
        """Log message to results text"""
        if color:
            self.txt_results.tag_config(color, foreground=color)
            self.txt_results.insert(tk.END, msg + "\n", color)
        else:
            self.txt_results.insert(tk.END, msg + "\n")
        self.txt_results.see(tk.END)
        self.parent.update()
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        self.txt_results.delete("1.0", tk.END)
        self.log("=" * 70)
        self.log("       Tab3 Register Integrator Logic Test Suite", "#00FFFF")
        self.log("=" * 70)
        self.log("")
        
        tables = self.get_test_tables()
        if not tables:
            self.log("❌ No tables configured!", "#FF0000")
            return
        
        try:
            base_addr = int(self.ent_test_base.get(), 16)
        except ValueError:
            self.log("❌ Invalid Base Address!", "#FF0000")
            return
        
        self.log(f"Base Address: 0x{base_addr:04X}")
        self.log(f"Tables Count: {len(tables)}")
        self.log("")
        
        # Test 1: Address Alignment
        self.log("【TEST 1】Address Alignment & Validation", "#FFFF00")
        self.log("-" * 40)
        self.run_alignment_test(tables, base_addr)
        self.log("")
        
        # Test 2: Mask Calculation
        self.log("【TEST 2】Dynamic Mask Calculation", "#FFFF00")
        self.log("-" * 40)
        self.run_mask_test(tables, base_addr)
        self.log("")
        
        # Test 3: Gap Detection
        self.log("【TEST 3】Flash Address Gap Detection", "#FFFF00")
        self.log("-" * 40)
        self.run_gap_test(tables, base_addr)
        self.log("")
        
        # Test 4: HEX Generation
        self.log("【TEST 4】HEX Buffer Generation", "#FFFF00")
        self.log("-" * 40)
        self.run_hex_test(tables, base_addr)
        self.log("")
        
        # Summary
        self.log("=" * 70)
        self.log("       Test Complete!", "#00FF00")
        self.log("=" * 70)
        self.update_status("All tests completed")
    
    def run_alignment_test(self, tables, base_addr):
        """Run alignment test"""
        self.log("Testing auto-alignment rules...")
        self.log("")
        
        for table in tables:
            old_addr = table['addr']
            new_addr, adjusted, warning = validate_and_align_flash_address(old_addr, base_addr)
            
            if adjusted:
                self.log(f"  ⚠️  {table['name']}: 0x{old_addr:04X} → 0x{new_addr:04X}", "#FFA500")
                if warning:
                    self.log(f"      {warning}", "#888888")
            else:
                self.log(f"  ✓ {table['name']}: 0x{new_addr:04X} (no change)", "#00FF00")
        
        self.log("")
        self.log("✅ Test 1 Complete")
    
    def run_mask_test(self, tables, base_addr):
        """Run mask calculation test"""
        enabled_tables = [t for t in tables if t['enabled']]
        
        if not enabled_tables:
            self.log("❌ No enabled tables!", "#FF0000")
            return
        
        # Calculate
        max_addr = max(t['addr'] for t in enabled_tables)
        mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        mask_val, _, bit_mapping = calculate_enable_mask_with_gaps(enabled_tables, base_addr)
        
        self.log(f"Max Address: 0x{max_addr:04X}")
        self.log(f"Total Bits: {total_bits}")
        self.log(f"Mask Bytes: {mask_bytes}")
        self.log(f"Enable Mask: 0x{mask_val:0{mask_bytes*2}X}")
        self.log("")
        self.log("Bit Mapping:")
        
        for m in bit_mapping:
            gap_note = ""
            # Check if there's a gap before this table
            for i, t in enumerate(enabled_tables):
                if t['addr'] == m['addr'] and i > 0:
                    prev_addr = enabled_tables[i-1]['addr']
                    if m['addr'] > prev_addr + 256:
                        gap_blocks = (m['addr'] - prev_addr) // 256 - 1
                        gap_note = f" ← Gap before! ({gap_blocks} blocks)"
                    break
            self.log(f"  Bit {m['bit_pos']:2d}: 0x{m['addr']:04X} - {m['name']}{gap_note}", "#00FFFF")
        
        self.log("")
        self.log("✅ Test 2 Complete")
    
    def run_gap_test(self, tables, base_addr):
        """Run gap detection test"""
        enabled_tables = [t for t in tables if t['enabled']]
        
        if not enabled_tables:
            self.log("❌ No enabled tables!", "#FF0000")
            return
        
        max_addr = max(t['addr'] for t in enabled_tables)
        gaps = detect_flash_address_gaps(enabled_tables, base_addr, max_addr)
        
        if len(gaps) <= 1:
            self.log("✓ No gaps detected - continuous memory layout", "#00FF00")
        else:
            self.log(f"Found {len(gaps)} gap(s):")
            for i, (start, end) in enumerate(gaps, 1):
                blocks = (end - start) // 256 + 1
                self.log(f"  Gap #{i}: 0x{start:04X} ~ 0x{end:04X} ({blocks} blocks) → Mask bit = 0", "#FFA500")
                self.log(f"      Memory range: [{start - base_addr}] ~ [{end - base_addr}]")
        
        self.log("")
        self.log("✅ Test 3 Complete")
    
    def run_hex_test(self, tables, base_addr):
        """Run HEX buffer generation test"""
        enabled_tables = [t for t in tables if t['enabled']]
        
        if not enabled_tables:
            self.log("❌ No enabled tables!", "#FF0000")
            return
        
        # Create mock buffer
        def create_mock_buffer(name):
            buf = bytearray([0xFF] * 256)
            buf[0] = ord(name[0]) if name else 0xAA
            buf[1] = ord(name[1]) if len(name) > 1 else 0xBB
            buf[0xFE] = 0xAB
            buf[0xFF] = 0xCD
            return buf
        
        max_addr = max(t['addr'] for t in enabled_tables)
        total_size = (max_addr - base_addr) + 256
        
        # Initialize with 0xFF (gap padding)
        buffer = bytearray([0xFF] * total_size)
        
        self.log(f"Buffer Size: {total_size} bytes")
        self.log(f"Initialized with: 0xFF (Gap padding)")
        self.log("")
        self.log("Placing tables:")
        
        for t in enabled_tables:
            start = t['addr'] - base_addr
            buffer[start:start+256] = create_mock_buffer(t['name'])
            self.log(f"  ✓ {t['name']}: 0x{t['addr']:04X} → Buffer[{start}:{start+256}]", "#00FF00")
        
        # Verify gaps
        self.log("")
        self.log("Verifying gaps are 0xFF:")
        enabled_addrs = [(t['addr'], t['addr'] + 256) for t in enabled_tables]
        
        all_gaps_ff = True
        for t in enabled_tables:
            for other_start, other_end in enabled_addrs:
                if t['addr'] == other_start:
                    continue
                # Check gap before this table
                prev_end = other_end
                if t['addr'] > prev_end:
                    gap_start = t['addr'] - base_addr
                    prev_end_abs = prev_end - base_addr
                    gap_data = buffer[prev_end_abs:gap_start]
                    all_ff = all(b == 0xFF for b in gap_data)
                    if not all_ff:
                        all_gaps_ff = False
        
        if all_gaps_ff:
            self.log("  ✓ All gaps filled with 0xFF", "#00FF00")
        else:
            self.log("  ⚠️ Some gaps not filled with 0xFF", "#FFA500")
        
        self.log("")
        self.log("✅ Test 4 Complete")
    
    def run_single_test(self):
        """Run single quick test"""
        self.txt_results.delete("1.0", tk.END)
        self.log("【Quick Single Test】")
        self.log("-" * 40)
        
        tables = self.get_test_tables()
        try:
            base_addr = int(self.ent_test_base.get(), 16)
        except ValueError:
            self.log("❌ Invalid Base Address!", "#FF0000")
            return
        
        enabled_tables = [t for t in tables if t['enabled']]
        if not enabled_tables:
            self.log("❌ No enabled tables!", "#FF0000")
            return
        
        max_addr = max(t['addr'] for t in enabled_tables)
        mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        mask_val, _, bit_mapping = calculate_enable_mask_with_gaps(enabled_tables, base_addr)
        
        self.log(f"Base: 0x{base_addr:04X} | Max: 0x{max_addr:04X}")
        self.log(f"Mask: 0x{mask_val:0{mask_bytes*2}X} ({mask_bytes} bytes, {total_bits} bits)")
        self.log("")
        for m in bit_mapping:
            self.log(f"  Bit {m['bit_pos']:2d}: 0x{m['addr']:04X} - {m['name']}", "#00FFFF")
    
    def show_mask_calc(self):
        """Show detailed mask calculation"""
        self.txt_results.delete("1.0", tk.END)
        self.log("【Mask Calculation Details】", "#FFFF00")
        self.log("=" * 50)
        
        tables = self.get_test_tables()
        try:
            base_addr = int(self.ent_test_base.get(), 16)
        except ValueError:
            self.log("❌ Invalid Base Address!", "#FF0000")
            return
        
        enabled_tables = [t for t in tables if t['enabled']]
        if not enabled_tables:
            self.log("❌ No enabled tables!", "#FF0000")
            return
        
        self.log(f"Formula:")
        self.log(f"  Bit_Position = (Flash_Addr - Base_Addr) // 256")
        self.log(f"  Mask_Bytes = (Total_Bits + 7) // 8")
        self.log("")
        
        max_addr = max(t['addr'] for t in enabled_tables)
        mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        
        self.log(f"Calculation:")
        self.log(f"  Base = 0x{base_addr:04X}")
        self.log(f"  Max = 0x{max_addr:04X}")
        self.log(f"  Offset = Max - Base = 0x{max_addr - base_addr:04X} ({max_addr - base_addr} bytes)")
        self.log(f"  Total_Bits = Offset / 256 + 1 = {total_bits}")
        self.log(f"  Mask_Bytes = ({total_bits} + 7) // 8 = {mask_bytes}")
        self.log("")
        
        mask_val = 0
        for t in enabled_tables:
            bit_pos = (t['addr'] - base_addr) // 256
            offset = t['addr'] - base_addr
            mask_val |= (1 << bit_pos)
            self.log(f"  {t['name']}:")
            self.log(f"    Addr = 0x{t['addr']:04X}")
            self.log(f"    Offset = 0x{offset:04X} ({offset} bytes)")
            self.log(f"    Bit = {offset} // 256 = {bit_pos}")
            self.log(f"    Mask |= (1 << {bit_pos})")
            self.log("")
        
        self.log(f"Final Mask: 0x{mask_val:0{mask_bytes*2}X}")
    
    def clear_results(self):
        """Clear results"""
        self.txt_results.delete("1.0", tk.END)
        self.update_status("Results cleared")


# =========================================================================
# Execution Entry Point (CLI & GUI Routing)
# =========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firmware Pipeline Studio (Pro)")
    parser.add_argument('--cli', action='store_true', help='Run in headless CLI mode')
    parser.add_argument('--config', type=str, help='Path to Packer CSV config file')
    parser.add_argument('--output', type=str, default='all_crc.hex', help='Output HEX file path')
    
    # CLI parameters for M0 & Integrator
    parser.add_argument('--m0_in', type=str, help='Input M0 Raw/Intel HEX file')
    parser.add_argument('--m0_out', type=str, help='Output parsed M0 HEX file')
    parser.add_argument('--reg_csv', type=str, help='Input Integrator Config CSV')
    parser.add_argument('--reg_base', type=str, default="0000", help='Global Base Address (Hex)')
    parser.add_argument('--reg_out', type=str, help='Output Integrated Register HEX')

    args, unknown = parser.parse_known_args()

    if args.cli:
        if not args.config: 
            print("[-] Error: --config is required in CLI mode.")
            sys.exit(1)
        
        print("[*] Running Firmware Pipeline CLI...")
        
        # Step 1: Process M0 Hex if provided
        if args.m0_in and args.m0_out:
            print(f"[*] Processing M0 Hex: {args.m0_in}")
            success, buf, orig_size = parse_m0_hex_file(args.m0_in)
            if success:
                expanded_buffer = bytearray(buf); expanded_buffer.extend([0xFF, 0xFF])
                with open(args.m0_out, 'w') as f:
                    for byte in expanded_buffer: f.write(f"{byte:02X}\n")
                print(f"[+] M0 Firmware Generated: {args.m0_out}")
            else: 
                print("[-] Error parsing M0 Hex.")
                sys.exit(1)

        # Step 2: Process Register Integrator if provided
        dynamic_mask = None
        if args.reg_csv and args.reg_out:
            success, calc_mask = generate_integrated_hex_from_csv(args.reg_csv, args.reg_base, args.reg_out)
            if not success:
                sys.exit(1)
            dynamic_mask = calc_mask

        # Step 3: Run Final Packer
        packer = FirmwarePacker()
        print(f"[*] Loading Packer configuration from: {args.config}")
        success, msg = packer.load_csv_config(args.config)
        if not success: 
            print(f"[-] Error loading config: {msg}")
            sys.exit(1)
            
        # Core Fix: Dynamically update Mask Values inside the Packer Sections
        # Any section that defines a mask target will receive the newly calculated Mask
        if dynamic_mask is not None:
            updated = False
            for sec in packer.sections:
                if sec.get('mask_target', '').strip() != "":
                    sec['mask_val'] = dynamic_mask
                    updated = True
                    print(f"[*] Dynamically updated Enable Mask in Packer config to: 0x{dynamic_mask:X}")
            if not updated:
                print("[-] Warning: No section with 'mask_target' found in Packer config to inject the mask.")
            
        print(f"[*] Generating Final Firmware...")
        success, msg = packer.generate_firmware_hex(args.output)
        if success: 
            print(f"[+] Success: {msg}")
        else: 
            print(f"[-] Error generating firmware: {msg}")
            sys.exit(1)
    else:
        # Launch Graphical User Interface
        root = tk.Tk()
        app = AppGUI(root)
        root.mainloop()
