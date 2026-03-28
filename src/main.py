#!/usr/bin/env python3
"""
Firmware Pipeline Studio (Ultimate Flagship Edition)
Hex Packer CLI - 固件管線工具

版本: 1.2.3
"""

import os
import sys
import random
import argparse
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time

# 確保可以從 core 匯入模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

# 匯入核心模組
from core.crc16 import calculate_custom_crc16
from core.hex_parser import parse_hex_address, parse_m0_hex_file, write_hex_file
from core.mask_calculator import (
    validate_and_align_flash_address,
    calculate_dynamic_mask_bytes,
    calculate_enable_mask_with_gaps,
    detect_flash_address_gaps
)
from core.register import parse_register_excel_to_buffer
from core.packer import FirmwarePacker
from core.viewer import RegisterViewer


# =========================================================================
# CLI Headless Execution Functions
# =========================================================================
def generate_integrated_hex_from_csv(csv_path, base_addr_hex_str, out_path):
    """CLI Worker: Parses CSV, generates the integrated hex map, and calculates dynamic Enable Mask."""
    print(f"[*] Parsing Integrator Config: {csv_path}")
    try:
        df = pd.read_csv(csv_path).fillna("")
        base_addr = int(base_addr_hex_str, 16)
        all_items = []
        enabled_items = []
        base_dir = os.path.dirname(csv_path)

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

        all_items.sort(key=lambda x: x['addr'])
        
        print(f"[*] Global Base Address: 0x{base_addr:04X}")
        print(f"[*] Validating and auto-aligning Flash Addresses...")
        
        for item in all_items:
            old_addr = item['addr']
            item['addr'], was_adjusted, warning = validate_and_align_flash_address(item['addr'], base_addr)
            if was_adjusted:
                print(f"    [A] {item['name'][:25]:25s}: 0x{old_addr:04X} -> 0x{item['addr']:04X}")
        
        enabled_addr_list = [item for item in all_items if item['enabled']]
        
        if enabled_addr_list:
            max_addr = max(item['addr'] for item in enabled_addr_list)
            mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
            
            print(f"[*] Max Flash Address: 0x{max_addr:04X}")
            print(f"[*] Total Enable Bits needed: {total_bits}")
            print(f"[*] Mask Byte Length: {mask_bytes} byte(s)")
            
            dynamic_mask = 0
            for item in enabled_addr_list:
                bit_position = (item['addr'] - base_addr) // 256
                if 0 <= bit_position < 128:
                    dynamic_mask |= (1 << bit_position)
            
            print(f"[*] Enable Mask (Hex): 0x{dynamic_mask:0{mask_bytes*2}X}")
        else:
            dynamic_mask = 0
            mask_bytes = 1
            total_bits = 0
            print(f"[*] No enabled tables - Mask: 0x0000")
        
        print(f"\n[*] Bit-to-Address Mapping (Base 0x{base_addr:04X} + Bit*N*256):")
        last_end = base_addr
        for item in all_items:
            if item['enabled']:
                bit_pos = (item['addr'] - base_addr) // 256
                if item['addr'] > last_end + 256:
                    gap_size = (item['addr'] - last_end) // 256
                    print(f"    [GAP] 0x{last_end:04X} - 0x{item['addr']-256:04X} ({gap_size} blocks = Mask bits = 0)")
                print(f"    ├── Bit {bit_pos:2d}: 0x{item['addr']:04X} - {item['name'][:20]}")
                last_end = item['addr'] + 256
        
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

        max_addr = max([item['addr'] for item in enabled_items])
        total_size = (max_addr - base_addr) + 256
        integrated_buffer = bytearray([0xFF] * total_size)
        
        print(f"\n[*] Generating Integrated HEX (Size: {total_size} bytes)...")
        for item in enabled_items:
            start = item['addr'] - base_addr
            integrated_buffer[start:start+256] = item['buffer']
            print(f"    ├── Placed {item['name'][:20]:20s} at 0x{item['addr']:04X}")

        with open(out_path, 'w') as f:
            for byte in integrated_buffer: f.write(f"{byte:02X}\n")
            
        print(f"\n[+] Integrator Generated successfully: {out_path}")
        return True, dynamic_mask
        
    except Exception as e:
        print(f"[-] Integrator Error: {e}")
        import traceback; traceback.print_exc()
        return False, 0


# =========================================================================
# GUI Application (保留原有完整實作)
# =========================================================================
class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Firmware Pipeline Studio (Ultimate Flagship Edition)")
        self.root.geometry("1450x950")

        style = ttk.Style()
        style.configure("Treeview", rowheight=25, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        self.packer = FirmwarePacker()
        self.integration_list = [] 
        
        self.integrated_hex_path = ""
        self.integrator_csv_path = "" 
        self.packer_csv_path = ""
        self.editing_idx = None 
        self.current_mask_val = 0 
        
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

    # TAB 1: FIRMWARE PACKER 
    def setup_packer_tab(self):
        ctrl_frame = tk.LabelFrame(self.tab_packer, text=" Step 1: Manage Sections & Configuration ", pady=5, padx=10)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        
        btn_frame1 = tk.Frame(ctrl_frame)
        btn_frame1.pack(side=tk.LEFT, fill=tk.Y)
        tk.Button(btn_frame1, text="Load Config (.csv)", command=self.btn_packer_load_config, bg="#ffc107", width=18).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(btn_frame1, text="Save Config (.csv)", command=self.btn_packer_save_config, bg="#20c997", fg="white", width=18).grid(row=0, column=1, padx=2, pady=2)

        btn_frame2 = tk.Frame(ctrl_frame)
        btn_frame2.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(btn_frame2, text="Edit Selected", command=self.btn_packer_edit, bg="#007bff", fg="white", width=15).grid(row=0, column=0, padx=2, pady=2)
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

        tk.Label(add_frame, text="Size Offset (Hex):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.ent_sec_size_off = tk.Entry(add_frame, width=30)
        self.ent_sec_size_off.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Address Offset (Hex):").grid(row=2, column=2, sticky="w", padx=20, pady=2)
        self.ent_sec_addr_off = tk.Entry(add_frame, width=30)
        self.ent_sec_addr_off.grid(row=2, column=3, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Enable Offset/Bit/Val:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        f_en = tk.Frame(add_frame)
        f_en.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        self.ent_sec_en_off = tk.Entry(f_en, width=12); self.ent_sec_en_off.pack(side=tk.LEFT)
        tk.Label(f_en, text="/").pack(side=tk.LEFT)
        self.ent_sec_en_bit = tk.Entry(f_en, width=6); self.ent_sec_en_bit.pack(side=tk.LEFT)
        tk.Label(f_en, text="/").pack(side=tk.LEFT)
        self.ent_sec_en_val = tk.Entry(f_en, width=6); self.ent_sec_en_val.pack(side=tk.LEFT)

        tk.Label(add_frame, text="CRC Offset/Bit/Val:").grid(row=3, column=2, sticky="w", padx=20, pady=2)
        f_crc = tk.Frame(add_frame)
        f_crc.grid(row=3, column=3, sticky="w", padx=5, pady=2)
        self.ent_sec_crc_off = tk.Entry(f_crc, width=12); self.ent_sec_crc_off.pack(side=tk.LEFT)
        tk.Label(f_crc, text="/").pack(side=tk.LEFT)
        self.ent_sec_crc_bit = tk.Entry(f_crc, width=6); self.ent_sec_crc_bit.pack(side=tk.LEFT)
        tk.Label(f_crc, text="/").pack(side=tk.LEFT)
        self.ent_sec_crc_val = tk.Entry(f_crc, width=6); self.ent_sec_crc_val.pack(side=tk.LEFT)

        tk.Label(add_frame, text="Mask Target:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.ent_sec_mask_target = tk.Entry(add_frame, width=30)
        self.ent_sec_mask_target.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        tk.Label(add_frame, text="Mask Offset/Val:").grid(row=4, column=2, sticky="w", padx=20, pady=2)
        f_mask = tk.Frame(add_frame)
        f_mask.grid(row=4, column=3, sticky="w", padx=5, pady=2)
        self.ent_sec_mask_off = tk.Entry(f_mask, width=12); self.ent_sec_mask_off.pack(side=tk.LEFT)
        tk.Label(f_mask, text="/").pack(side=tk.LEFT)
        self.ent_sec_mask_val = tk.Entry(f_mask, width=12); self.ent_sec_mask_val.pack(side=tk.LEFT)

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
        self.btn_manual_update = tk.Button(f_actions, text="Update Section", command=self.btn_manual_update_section, bg="#ffc107", font=("Arial", 10, "bold"), width=15, state=tk.DISABLED)
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
        tk.Button(order_frame, text="Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        tk.Button(order_frame, text="Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)
        
        tk.Button(order_frame, text="Generate Final HEX File", command=self.generate_firmware, bg="#28a745", fg="white", font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=5)

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

    def btn_packer_save_config(self):
        if not self.packer.sections: messagebox.showwarning("Warning", "No sections to save."); return
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Config", "*.csv")], initialfile="packer_config.csv")
        if save_path:
            success, msg = self.packer.save_csv_config(save_path)
            if success: self.packer_csv_path = save_path; messagebox.showinfo("Success", f"Config saved to:\n{save_path}")
            else: messagebox.showerror("Error", msg)

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

    # TAB 2: M0 HEX CONVERTER
    def setup_m0_tab(self):
        frame = tk.LabelFrame(self.tab_m0, text=" M0 HEX to Firmware Converter ", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        tk.Label(frame, text="Supports Standard Intel HEX (.hex) OR Raw Space-Separated HEX (.txt/.hex)", font=("Arial", 11)).pack(pady=10)
        tk.Button(frame, text="1. Load M0 HEX File", command=self.btn_m0_load, bg="#007bff", fg="white", font=("Arial", 11, "bold"), width=30).pack(pady=10)
        self.lbl_m0_status = tk.Label(frame, text="File Status: No file loaded.", fg="gray", font=("Courier", 11)); self.lbl_m0_status.pack(pady=5)
        tk.Button(frame, text="2. Convert & Expand length (+2 Bytes for CRC)", command=self.btn_m0_convert, bg="#6f42c1", fg="white", font=("Arial", 11, "bold"), width=40).pack(pady=15)
        self.btn_m0_send = tk.Button(frame, text="3. Send to Firmware Packer", command=self.btn_m0_send_packer, bg="#17a2b8", fg="white", font=("Arial", 11, "bold"), width=30, state=tk.DISABLED)
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
            messagebox.showerror("Parse Error", "Failed to parse HEX file.")
            self.lbl_m0_status.config(text="Error parsing file.", fg="red")

    def btn_m0_convert(self):
        if not self.m0_file_path: return
        expanded_buffer = bytearray(self.m0_buffer)
        expanded_buffer.extend([0xFF, 0xFF])
        expanded_size = self.m0_orig_size + 2
        default_name = os.path.basename(self.m0_file_path).replace('.hex', '').replace('.txt', '') + "_fw.hex"
        save_path = filedialog.asksaveasfilename(defaultextension=".hex", initialfile=default_name, filetypes=[("Raw 1-byte HEX", "*.hex")])
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    for byte in expanded_buffer: f.write(f"{byte:02X}\n")
                self.m0_output_path = save_path; self.btn_m0_send.config(state=tk.NORMAL)
                messagebox.showinfo("Success", f"File converted successfully.\nExpanded Length: {expanded_size} Bytes")
            except Exception as e: messagebox.showerror("Write Error", str(e))

    def btn_m0_send_packer(self):
        if not self.m0_output_path: return
        total_len = self.m0_orig_size + 2
        name = os.path.basename(self.m0_file_path).replace('.hex', '').replace('.txt', '').upper()
        sec = {
            'name': name, 'max_len': total_len, 'file_path': self.m0_output_path, 'is_full': True, 'inject_err': False, 'target_sec': "", 
            'size_offset': "", 'size_offset_orig': "", 'en_offset': "", 'en_offset_orig': "", 'en_bit': "", 'en_val': 1, 
            'crc_offset': "", 'crc_offset_orig': "", 'crc_bit': "", 'crc_val': 1, 'addr_offset': "", 'addr_offset_orig': "", 'calc_addr': 0, 
            'bypass_crc': False
        }
        self.packer.sections.append(sec); self.refresh_packer_tree()
        self.packer_tree.selection_set(str(len(self.packer.sections) - 1)); self.btn_packer_edit() 
        self.notebook.select(self.tab_packer)
        messagebox.showinfo("Success", f"Section '{name}' added to Packer.")

    # TAB 3: REGISTER INTEGRATOR
    def setup_integrator_tab(self):
        load_frame = tk.LabelFrame(self.tab_integrator, text=" Step 1: Manage Register Tables ", padx=10, pady=10)
        load_frame.pack(fill=tk.X, padx=10, pady=5)
        btn_frame = tk.Frame(load_frame); btn_frame.pack(side=tk.LEFT)
        row0 = tk.Frame(btn_frame); row0.pack(fill=tk.X, pady=2)
        tk.Button(row0, text="+ Add Excel File(s)", command=self.btn_int_add_files, bg="#007bff", fg="white", width=20).pack(side=tk.LEFT, padx=2)
        tk.Button(row0, text="- Remove Selected", command=self.btn_int_remove, bg="#dc3545", fg="white", width=20).pack(side=tk.LEFT, padx=2)
        row1 = tk.Frame(btn_frame); row1.pack(fill=tk.X, pady=2)
        tk.Button(row1, text="Load Config (.csv)", command=self.btn_int_load_config, bg="#ffc107", width=20).pack(side=tk.LEFT, padx=2)
        tk.Button(row1, text="Save Config (.csv)", command=self.btn_int_save_config, bg="#20c997", fg="white", width=20).pack(side=tk.LEFT, padx=2)
        self.lbl_mask = tk.Label(load_frame, text="Enable Mask: 0x0000 (1 byte)", fg="#d35400", font=("Courier", 14, "bold"))
        self.lbl_mask.pack(side=tk.RIGHT, padx=15)

        tree_frame = tk.Frame(self.tab_integrator, padx=10, pady=5); tree_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(tree_frame, text="Tip: Double-click any row to view its Memory Map in Tab 4.", fg="gray").pack(anchor="w")
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
        mask_frame = tk.Frame(action_frame)
        mask_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(mask_frame, text="Global Base Address (Hex): 0x").pack(side=tk.LEFT, padx=5)
        self.ent_base_addr = tk.Entry(mask_frame, width=10); self.ent_base_addr.insert(0, "0000"); self.ent_base_addr.pack(side=tk.LEFT, padx=5)
        tk.Label(mask_frame, text="| Mask Target Section:").pack(side=tk.LEFT, padx=5)
        self.ent_int_mask_target = tk.Entry(mask_frame, width=10); self.ent_int_mask_target.insert(0, "SYS"); self.ent_int_mask_target.pack(side=tk.LEFT, padx=5)
        tk.Label(mask_frame, text="Mask Offset (Hex): 0x").pack(side=tk.LEFT, padx=5)
        self.ent_int_mask_off = tk.Entry(mask_frame, width=10); self.ent_int_mask_off.pack(side=tk.LEFT, padx=5)
        btn_action_frame = tk.Frame(action_frame)
        btn_action_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(btn_action_frame, text="1. Generate Integrated HEX", command=self.btn_int_generate, bg="#6f42c1", fg="white", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=5)
        self.btn_int_send = tk.Button(btn_action_frame, text="2. Send to Firmware Packer", command=self.btn_int_send_packer, bg="#17a2b8", fg="white", font=("Arial", 11, "bold"), state=tk.DISABLED)
        self.btn_int_send.pack(side=tk.LEFT, padx=15)

    def btn_int_add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not files: return
        try:
            base_addr = int(self.ent_base_addr.get().strip(), 16)
        except ValueError:
            base_addr = 0
        for f in files:
            name = os.path.basename(f); self.shared_files[name] = f
            success, buffer = parse_register_excel_to_buffer(f)
            status = "Parsed + CRC" if success else "Error Parsing"
            initial_addr = base_addr
            self.integration_list.append({
                "name": name, "path": f, "addr": initial_addr, "enabled": True, 
                "buffer": buffer, "status": status, "bit_position": 0
            })
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
        self.integration_list.sort(key=lambda x: x['addr'])
        try:
            base_addr = int(self.ent_base_addr.get().strip(), 16)
        except ValueError:
            base_addr = 0
        
        for item in self.integration_list:
            old_addr = item['addr']
            item['addr'], was_adjusted, warning = validate_and_align_flash_address(item['addr'], base_addr)
        
        enabled_items = [item for item in self.integration_list if item['enabled']]
        if enabled_items:
            max_addr = max(item['addr'] for item in enabled_items)
            mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
            mask_val, _, _ = calculate_enable_mask_with_gaps(enabled_items, base_addr)
        else:
            mask_val = 0
            mask_bytes = 1
        
        self.current_mask_val = mask_val
        self.lbl_mask.config(text=f"Enable Mask: 0x{mask_val:0{mask_bytes*2}X} ({mask_bytes} byte(s))")
        
        for item in self.int_tree.get_children(): self.int_tree.delete(item)
        for idx, item in enumerate(self.integration_list):
            bit_info = ""
            if item.get('bit_position', None) is not None and item['bit_position'] >= 0:
                bit_info = f" [Bit{item['bit_position']}]"
            elif not item['enabled']:
                bit_info = " [DISABLED]"
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
        all_tables = self.integration_list
        if not all_tables: messagebox.showwarning("Warning", "No tables loaded!"); return
        try: base_addr = int(self.ent_base_addr.get().strip(), 16)
        except ValueError: messagebox.showerror("Error", "Invalid Global Base Address!"); return
        
        for item in all_tables:
            item['addr'], was_adjusted, warning = validate_and_align_flash_address(item['addr'], base_addr)
        
        all_tables.sort(key=lambda x: x['addr'])
        max_addr = max([item['addr'] for item in all_tables])
        mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        total_size = (max_addr - base_addr) + 256 
        integrated_buffer = bytearray([0xFF] * total_size) 
        
        enabled_count = 0
        for item in all_tables:
            start = item['addr'] - base_addr
            integrated_buffer[start:start+256] = item['buffer']
            if item['enabled']: enabled_count += 1
        
        enabled_items = [item for item in all_tables if item['enabled']]
        mask_val, _, _ = calculate_enable_mask_with_gaps(enabled_items, base_addr)
        
        save_path = filedialog.asksaveasfilename(defaultextension=".hex", initialfile="All_Registers.hex", filetypes=[("HEX File", "*.hex")])
        if save_path:
            try:
                with open(save_path, 'w') as f:
                    for byte in integrated_buffer: f.write(f"{byte:02X}\n")
                self.integrated_hex_path = save_path; self.btn_int_send.config(state=tk.NORMAL)
                messagebox.showinfo("Success", f"Integrated HEX saved to:\n{save_path}\n\nTotal: {len(all_tables)} tables ({enabled_count} enabled)")
            except Exception as e: messagebox.showerror("Error", str(e))

    def btn_int_send_packer(self):
        if not self.integrated_hex_path: return
        with open(self.integrated_hex_path, 'r') as f: file_size = sum(1 for line in f if line.strip())
        mask_target = self.ent_int_mask_target.get().strip()
        mask_offset = self.ent_int_mask_off.get().strip().replace('0x', '')
        try: mask_off_int = int(mask_offset, 16) if mask_offset else ""
        except ValueError: mask_off_int = ""
        sec = {
            'name': "ALL_REGISTERS", 'max_len': file_size, 'file_path': self.integrated_hex_path,
            'is_full': True, 'inject_err': False, 'target_sec': "", 'size_offset': "", 'size_offset_orig': "", 
            'en_offset': "", 'en_offset_orig': "", 'en_bit': "", 'en_val': 1, 'crc_offset': "", 'crc_offset_orig': "", 
            'crc_bit': "", 'crc_val': 1, 'addr_offset': "", 'addr_offset_orig': "", 'calc_addr': 0, 
            'mask_target': mask_target, 'mask_offset': mask_off_int, 'mask_offset_orig': mask_offset, 
            'mask_val': self.current_mask_val, 'bypass_crc': True 
        }
        self.packer.sections.append(sec); self.refresh_packer_tree()
        self.packer_tree.selection_set(str(len(self.packer.sections) - 1)); self.btn_packer_edit() 
        self.notebook.select(self.tab_packer)

    # TAB 4: SINGLE MAP VIEWER
    def setup_viewer_tab(self):
        ctrl_frame = tk.LabelFrame(self.tab_viewer, text=" Viewer Controls ", padx=10, pady=10)
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
        detail_text = f"Name : {raw_data.get('name','')}\nAddr : {raw_data.get('high_addr','')} ~ {raw_data.get('low_addr','')}\nBits : {raw_data.get('bits','')} bit(s)\nInit : {raw_data.get('init','')}  |  R/W: {raw_data.get('rw','')}\n" + "-" * 60 + "\nDescription:\n" + str(raw_data.get('raw_desc','')) + "\n"
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
# Test Tab Controller
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
        title_frame = tk.Frame(self.parent)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(title_frame, text="Tab3 Register Integrator Logic Test Suite", 
                 font=("Arial", 14, "bold"), fg="#2c3e50").pack(side=tk.LEFT)
        
        scenario_frame = tk.LabelFrame(self.parent, text=" Test Scenario Setup ", padx=15, pady=10)
        scenario_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(scenario_frame, text="Base Address (Hex): 0x").pack(side=tk.LEFT, padx=5)
        self.ent_test_base = tk.Entry(scenario_frame, width=10)
        self.ent_test_base.insert(0, "1000")
        self.ent_test_base.pack(side=tk.LEFT, padx=5)
        
        tables_frame = tk.LabelFrame(self.parent, text=" Test Tables ", padx=10, pady=5)
        tables_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        cols = ("Name", "Flash Address (Hex)", "Enabled")
        self.test_table_tree = ttk.Treeview(tables_frame, columns=cols, show="headings", height=6)
        for col in cols:
            self.test_table_tree.heading(col, text=col)
            self.test_table_tree.column(col, anchor="center")
        scroll_y = ttk.Scrollbar(tables_frame, orient=tk.VERTICAL, command=self.test_table_tree.yview)
        self.test_table_tree.configure(yscroll=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.test_table_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        btn_frame = tk.Frame(tables_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="+ Add Table", command=self.add_test_table, 
                  bg="#27ae60", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="- Remove Selected", command=self.remove_test_table, 
                  bg="#e74c3c", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Load Preset", command=self.load_preset, 
                  bg="#3498db", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        
        control_frame = tk.Frame(self.parent)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(control_frame, text="Run All Tests", command=self.run_all_tests,
                  bg="#9b59b6", fg="white", font=("Arial", 11, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Show Mask Calc", command=self.show_mask_calc,
                  bg="#16a085", fg="white", font=("Arial", 10), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Clear Results", command=self.clear_results,
                  bg="#95a5a6", fg="white", width=12).pack(side=tk.RIGHT, padx=5)
        
        results_frame = tk.LabelFrame(self.parent, text=" Test Results ", padx=10, pady=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.txt_results = tk.Text(results_frame, wrap=tk.WORD, bg="#1e1e1e", fg="#00ff00", 
                                   font=("Courier", 10), insertbackground="white")
        scroll_y_res = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.txt_results.yview)
        self.txt_results.configure(yscroll=scroll_y_res.set)
        scroll_y_res.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_results.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.status_bar = tk.Label(self.parent, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
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
            self.log("No tables configured!", "#FF0000")
            return
        
        try:
            base_addr = int(self.ent_test_base.get(), 16)
        except ValueError:
            self.log("Invalid Base Address!", "#FF0000")
            return
        
        self.log(f"Base Address: 0x{base_addr:04X}")
        self.log(f"Tables Count: {len(tables)}")
        self.log("")
        
        enabled_tables = [t for t in tables if t['enabled']]
        if not enabled_tables:
            self.log("No enabled tables!", "#FF0000")
            return
        
        max_addr = max(t['addr'] for t in enabled_tables)
        mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        mask_val, _, bit_mapping = calculate_enable_mask_with_gaps(enabled_tables, base_addr)
        
        self.log("Mask Calculation Results:", "#FFFF00")
        self.log(f"  Max Address: 0x{max_addr:04X}")
        self.log(f"  Total Bits: {total_bits}")
        self.log(f"  Mask Bytes: {mask_bytes}")
        self.log(f"  Enable Mask: 0x{mask_val:0{mask_bytes*2}X}")
        self.log("")
        self.log("Bit Mapping:")
        for m in bit_mapping:
            self.log(f"  Bit {m['bit_pos']:2d}: 0x{m['addr']:04X} - {m['name']}", "#00FFFF")
        
        gaps = detect_flash_address_gaps(enabled_tables, base_addr, max_addr)
        self.log("")
        self.log("Gap Detection:")
        if len(gaps) <= 1:
            self.log("  No gaps detected - continuous memory layout", "#00FF00")
        else:
            self.log(f"  Found {len(gaps)} gap(s):", "#FFA500")
        
        self.log("")
        self.log("=" * 70)
        self.log("       All Tests Completed!", "#00FF00")
        self.log("=" * 70)
        self.update_status("All tests completed")
    
    def show_mask_calc(self):
        """Show detailed mask calculation"""
        self.txt_results.delete("1.0", tk.END)
        self.log("Mask Calculation Details", "#FFFF00")
        self.log("=" * 50)
        
        tables = self.get_test_tables()
        try:
            base_addr = int(self.ent_test_base.get(), 16)
        except ValueError:
            self.log("Invalid Base Address!", "#FF0000")
            return
        
        enabled_tables = [t for t in tables if t['enabled']]
        if not enabled_tables:
            self.log("No enabled tables!", "#FF0000")
            return
        
        self.log(f"Base = 0x{base_addr:04X}")
        max_addr = max(t['addr'] for t in enabled_tables)
        mask_bytes, total_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        mask_val, _, bit_mapping = calculate_enable_mask_with_gaps(enabled_tables, base_addr)
        
        self.log(f"Max = 0x{max_addr:04X}")
        self.log(f"Offset = 0x{max_addr - base_addr:04X} ({max_addr - base_addr} bytes)")
        self.log(f"Total_Bits = {total_bits}")
        self.log(f"Mask_Bytes = {mask_bytes}")
        self.log(f"Mask = 0x{mask_val:0{mask_bytes*2}X}")
        self.log("")
        for m in bit_mapping:
            self.log(f"  {m['name']}: Bit {m['bit_pos']:2d} at 0x{m['addr']:04X}", "#00FFFF")
    
    def clear_results(self):
        """Clear results"""
        self.txt_results.delete("1.0", tk.END)
        self.update_status("Results cleared")


# =========================================================================
# Execution Entry Point
# =========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firmware Pipeline Studio (Pro)")
    parser.add_argument('--cli', action='store_true', help='Run in headless CLI mode')
    parser.add_argument('--config', type=str, help='Path to Packer CSV config file')
    parser.add_argument('--output', type=str, default='all_crc.hex', help='Output HEX file path')
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

        dynamic_mask = None
        if args.reg_csv and args.reg_out:
            success, calc_mask = generate_integrated_hex_from_csv(args.reg_csv, args.reg_base, args.reg_out)
            if not success:
                sys.exit(1)
            dynamic_mask = calc_mask

        packer = FirmwarePacker()
        print(f"[*] Loading Packer configuration from: {args.config}")
        success, msg = packer.load_csv_config(args.config)
        if not success: 
            print(f"[-] Error loading config: {msg}")
            sys.exit(1)
            
        if dynamic_mask is not None:
            for sec in packer.sections:
                if sec.get('mask_target', '').strip() != "":
                    sec['mask_val'] = dynamic_mask
                    print(f"[*] Dynamically updated Enable Mask to: 0x{dynamic_mask:X}")
            
        print(f"[*] Generating Final Firmware...")
        success, msg = packer.generate_firmware_hex(args.output)
        if success: 
            print(f"[+] Success: {msg}")
        else: 
            print(f"[-] Error generating firmware: {msg}")
            sys.exit(1)
    else:
        root = tk.Tk()
        app = AppGUI(root)
        root.mainloop()
