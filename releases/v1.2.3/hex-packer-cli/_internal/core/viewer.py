"""
Register Viewer Module - 寄存器查看器
"""

from typing import List, Dict, Any, Tuple, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .crc16 import calculate_custom_crc16
from .hex_parser import parse_hex_address


class RegisterViewer:
    """
    寄存器查看器類別

    負責:
    - Excel 解析
    - 位元映射
    - Gap 檢測
    - CRC 嵌入
    """

    def __init__(self, treeview=None):
        """
        初始化寄存器查看器。

        Args:
            treeview: Tkinter Treeview 控制項 (可選)
        """
        self.tree = treeview
        self.current_map: List[Dict[str, Any]] = []
        self.current_buffer: Optional[bytearray] = None

    def add_gap_to_map(
        self,
        gap_start: int,
        gap_end: int
    ) -> Dict[str, Any]:
        """
        將計算出的 Gap 加入映射。

        Args:
            gap_start: Gap 起始位元
            gap_end: Gap 結束位元

        Returns:
            Gap 映射字典
        """
        low_addr = gap_start // 8
        loc_lsb = gap_start % 8
        high_addr = gap_end // 8
        loc_msb = gap_end % 8
        num_bits = gap_end - gap_start + 1

        gap = {
            'start_bit': gap_start,
            'high_addr': f"h{high_addr:04X}",
            'low_addr': f"h{low_addr:04X}",
            'loc_msb': str(loc_msb),
            'loc_lsb': str(loc_lsb),
            'name': "N/A",
            'msb': "",
            'lsb': "",
            'bits': str(num_bits),
            'init': "",
            'rw': "",
            'display_desc': "N/A",
            'raw_desc': "N/A",
            'is_gap': True
        }

        self.current_map.append(gap)
        return gap

    def process_and_map_excel(
        self,
        file_path: str,
        page_size: int = 256
    ) -> Tuple[bool, str]:
        """
        讀取 Excel，生成 256-byte 緩衝區並映射絕對位元。

        Args:
            file_path: Excel 檔案路徑
            page_size: 頁面大小 (預設 256)

        Returns:
            Tuple[成功與否, 訊息]
        """
        if not PANDAS_AVAILABLE:
            return False, "pandas not available"

        try:
            df = pd.read_excel(file_path).fillna("")
            regs = []
            total_cols = len(df.columns)

            for idx, row in df.iterrows():
                if total_cols < 10:
                    continue

                low_addr_int = parse_hex_address(row.iloc[1])
                high_addr_int = parse_hex_address(row.iloc[0])

                if low_addr_int < 0 or high_addr_int < 0:
                    continue

                try:
                    loc_msb = int(row.iloc[2])
                except ValueError:
                    loc_msb = 7

                try:
                    loc_lsb = int(row.iloc[3])
                except ValueError:
                    loc_lsb = 0

                # 絕對位元追蹤
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
                    'display_desc': display_desc,
                    'is_gap': False
                })

            # 填充 256-Byte 緩衝區
            page_buffer = bytearray(page_size)
            for reg in regs:
                init_str = reg['init'].replace('h', '').replace('0x', '').strip()
                if not init_str:
                    continue

                try:
                    init_val = int(init_str, 16)
                    shifted_val = init_val << int(reg['loc_lsb'])
                    span = (reg['high_int'] - reg['low_int']) + 1
                    max_bytes = max(span, (shifted_val.bit_length() + 7) // 8)

                    for i in range(max_bytes):
                        if reg['low_int'] + i < page_size - 2:
                            page_buffer[reg['low_int'] + i] |= (
                                (shifted_val >> (i * 8)) & 0xFF
                            )
                except ValueError:
                    pass

            # 計算並嵌入 CRC
            crc_val = calculate_custom_crc16(page_buffer[:page_size - 2])
            page_buffer[page_size - 2] = (crc_val >> 8) & 0xFF
            page_buffer[page_size - 1] = crc_val & 0xFF
            self.current_buffer = page_buffer

            # 建立結構化 UI 映射
            used_bits = [False] * ((page_size - 2) * 8)
            valid_regs = [r for r in regs if r['low_int'] < page_size - 2]

            # 標記所有已定義的絕對位元
            for reg in valid_regs:
                sb = reg['start_bit']
                eb = min(reg['end_bit'], (page_size - 2) * 8 - 1)
                if sb <= eb:
                    for b in range(sb, eb + 1):
                        if 0 <= b < len(used_bits):
                            used_bits[b] = True

            self.current_map = []

            # 加入有效的已定義寄存器
            for reg in valid_regs:
                self.current_map.append(reg)

            # 自動偵測並整合連續未定義位元為 Gap
            in_gap = False
            gap_start = 0

            for b in range(len(used_bits)):
                if not used_bits[b] and not in_gap:
                    in_gap = True
                    gap_start = b
                elif used_bits[b] and in_gap:
                    in_gap = False
                    gap_end = b - 1
                    self.add_gap_to_map(gap_start, gap_end)

            if in_gap:
                self.add_gap_to_map(gap_start, len(used_bits) - 1)

            # 按起始位元排序
            self.current_map.sort(key=lambda x: x.get('start_bit', 0))

            # 加入 CRC 欄位
            self.current_map.append({
                'start_bit': 999999,
                'high_addr': "h00FF",
                'low_addr': "h00FE",
                'loc_msb': "15",
                'loc_lsb': "0",
                'name': "AUTO_CRC16",
                'msb': "15",
                'lsb': "0",
                'bits': "16",
                'init': f"h{crc_val:04X}",
                'rw': "ro",
                'raw_desc': f"Auto-calculated CRC16\nPoly: 0x8005\nInit: 0x0052",
                'display_desc': f"Auto-calculated CRC16 (Poly: 0x8005, Init: 0x0052)",
                'is_gap': False,
                'is_crc': True
            })

            # 更新 Treeview
            if self.tree is not None:
                self.update_treeview(self.current_map)

            return True, f"Mapped 0x00 to 0xFF. Calculated CRC: 0x{crc_val:04X}."

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error processing file: {e}"

    def update_treeview(self, final_map: List[Dict[str, Any]]) -> None:
        """
        將映射渲染到 Treeview 控制項。

        Args:
            final_map: 映射列表
        """
        if self.tree is None:
            return

        # 清除現有項目
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, item in enumerate(final_map):
            values = (
                item.get('high_addr', ""),
                item.get('low_addr', ""),
                item.get('loc_msb', ""),
                item.get('loc_lsb', ""),
                item.get('name', ""),
                item.get('msb', ""),
                item.get('lsb', ""),
                item.get('bits', ""),
                item.get('init', ""),
                item.get('rw', ""),
                item.get('display_desc', "")
            )

            # Gap 樣式
            if item.get('is_gap', False):
                self.tree.insert(
                    "", "end",
                    iid=str(idx),
                    values=values,
                    tags=('unified_gap',)
                )
            # CRC 樣式
            elif item.get('is_crc', False):
                self.tree.insert(
                    "", "end",
                    iid=str(idx),
                    values=values,
                    tags=('crc',)
                )
            # 正常寄存器
            else:
                self.tree.insert(
                    "", "end",
                    iid=str(idx),
                    values=values,
                    tags=('reg',)
                )

        # 配置標籤樣式
        self.tree.tag_configure(
            'unified_gap',
            background='#ffeeba',
            foreground='#856404'
        )
        self.tree.tag_configure(
            'crc',
            background='#d4edda',
            foreground='#155724'
        )
        self.tree.tag_configure(
            'reg',
            background='#ffffff'
        )

    def get_register_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根據名稱取得寄存器。

        Args:
            name: 寄存器名稱

        Returns:
            寄存器資訊或 None
        """
        for reg in self.current_map:
            if reg.get('name') == name:
                return reg
        return None

    def export_to_text(self, output_path: str) -> Tuple[bool, str]:
        """
        將緩衝區匯出為文字檔。

        Args:
            output_path: 輸出檔案路徑

        Returns:
            Tuple[成功與否, 訊息]
        """
        if self.current_buffer is None:
            return False, "No buffer to export"

        try:
            with open(output_path, 'w') as f:
                for byte in self.current_buffer:
                    f.write(f"{byte:02X}\n")
            return True, output_path
        except Exception as e:
            return False, str(e)


if __name__ == "__main__":
    print("Register Viewer Module Test")
    print("=" * 50)
    print("Note: This module requires pandas and openpyxl")
    print("Install with: pip install pandas openpyxl")
