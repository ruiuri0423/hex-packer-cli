"""
GUI Logic 整合測試

測試 GUI 相關的業務邏輯（不依賴 GUI 環境）。
"""

import pytest
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.mask_calculator import (
    validate_and_align_flash_address,
    calculate_enable_mask_with_gaps,
    calculate_dynamic_mask_bytes
)
from core.viewer import RegisterViewer


class TestGUIFormValidationLogic:
    """GUI 表單驗證邏輯測試"""
    
    def test_safe_hex_conversion(self):
        """測試安全的十六進位轉換"""
        def safe_hex(val):
            v = str(val).strip().replace("0x", "").replace("0X", "")
            try:
                return int(v, 16) if v else ""
            except ValueError:
                return ""
        
        assert safe_hex("0xFF") == 0xFF
        assert safe_hex("FF") == 0xFF
        assert safe_hex("") == ""
        assert safe_hex("invalid") == ""
    
    def test_section_form_validation(self):
        """測試分區表單驗證"""
        def validate_section(name, max_len):
            errors = []
            
            if not name or not name.strip():
                errors.append("Section Name is required")
            
            try:
                length = int(max_len)
                if length <= 0:
                    errors.append("Max Length must be positive")
            except ValueError:
                errors.append("Max Length must be an integer")
            
            return errors
        
        # 有效輸入
        errors = validate_section("TEST", "1024")
        assert len(errors) == 0
        
        # 無效名稱
        errors = validate_section("", "1024")
        assert len(errors) == 1
        
        # 無效長度
        errors = validate_section("TEST", "invalid")
        assert len(errors) == 1


class TestGUIIntegrationListLogic:
    """GUI 整合清單邏輯測試"""
    
    def test_table_sorting_by_address(self):
        """測試按位址排序"""
        tables = [
            {'name': 'C', 'addr': 0x2000},
            {'name': 'A', 'addr': 0x1000},
            {'name': 'B', 'addr': 0x1500},
        ]
        
        sorted_tables = sorted(tables, key=lambda x: x['addr'])
        
        assert sorted_tables[0]['name'] == 'A'
        assert sorted_tables[1]['name'] == 'B'
        assert sorted_tables[2]['name'] == 'C'
    
    def test_mask_calculation_sync(self, base_address):
        """測試 Mask 計算同步"""
        base_addr = base_address
        tables = [
            {'name': 'Table_A', 'addr': base_addr, 'enabled': True},
            {'name': 'Table_B', 'addr': base_addr + 0x300, 'enabled': True},
        ]
        
        # 對齊
        for t in tables:
            t['addr'], _, _ = validate_and_align_flash_address(t['addr'], base_addr)
        
        # 計算 Mask
        enabled = [t for t in tables if t['enabled']]
        mask_val, mask_bytes, mapping = calculate_enable_mask_with_gaps(enabled, base_addr)
        
        # 驗證
        max_addr = max(t['addr'] for t in enabled)
        exp_bytes, exp_bits = calculate_dynamic_mask_bytes(max_addr, base_addr)
        
        assert mask_bytes == exp_bytes
        assert mask_val > 0  # 至少有一位被設定


class TestGUIEventHandlersLogic:
    """GUI 事件處理器邏輯測試"""
    
    def test_double_click_goto_tab(self):
        """測試雙擊跳轉邏輯"""
        def should_switch_tab(item_name, integration_list):
            return item_name in [t['name'] for t in integration_list]
        
        tables = [{'name': 'Table_A'}, {'name': 'Table_B'}]
        
        assert should_switch_tab('Table_A', tables) is True
        assert should_switch_tab('Table_C', tables) is False
    
    def test_selection_change_update_form(self):
        """測試選擇變更更新表單"""
        def get_selected_item(selection_id, integration_list):
            try:
                idx = int(selection_id)
                if 0 <= idx < len(integration_list):
                    return integration_list[idx]
            except (ValueError, TypeError):
                pass
            return None
        
        tables = [
            {'name': 'A', 'addr': 0x1000, 'enabled': True},
            {'name': 'B', 'addr': 0x2000, 'enabled': False},
        ]
        
        item = get_selected_item('1', tables)
        assert item is not None
        assert item['name'] == 'B'
        
        item = get_selected_item('99', tables)
        assert item is None


class TestGUITreeviewLogic:
    """GUI Treeview 邏輯測試"""
    
    def test_tree_refresh(self, base_address):
        """測試 Treeview 刷新邏輯"""
        def build_tree_values(tables, base_addr):
            values = []
            for idx, t in enumerate(tables):
                bit_info = ""
                if t.get('bit_position') is not None and t['bit_position'] >= 0:
                    bit_info = f" [Bit{t['bit_position']}]"
                elif not t['enabled']:
                    bit_info = " [DISABLED]"
                
                values.append((
                    t['name'],
                    f"0x{t['addr']:04X}",
                    "Yes" if t['enabled'] else "No",
                    t.get('status', 'OK') + bit_info
                ))
            return values
        
        tables = [
            {'name': 'A', 'addr': base_address, 'enabled': True, 'status': 'OK', 'bit_position': 0},
            {'name': 'B', 'addr': base_address + 0x1000, 'enabled': False, 'status': 'OK', 'bit_position': None},
        ]
        
        values = build_tree_values(tables, base_address)
        
        assert len(values) == 2
        assert "0x1000" in values[0]
        assert "Yes" in values[0]
        # values[1] 包含 ('B', '0x2000', 'No', 'OK [DISABLED]')
        # 第四個元素 (index 3) 包含 [DISABLED]
        assert "[DISABLED]" in values[1][3]


class TestGUIComboboxLogic:
    """GUI Combobox 邏輯測試"""
    
    def test_combobox_values_generation(self):
        """測試 Combobox 值生成"""
        def get_combobox_values(integration_list):
            return [item['name'] for item in integration_list]
        
        tables = [{'name': 'A'}, {'name': 'B'}, {'name': 'C'}]
        values = get_combobox_values(tables)
        
        assert values == ['A', 'B', 'C']
        assert len(values) == 3
    
    def test_auto_select_first(self):
        """測試自動選擇第一項"""
        def auto_select(values, current):
            if values and (not current or current not in values):
                return values[0]
            return current
        
        values = ['A', 'B', 'C']
        assert auto_select(values, '') == 'A'
        assert auto_select(values, 'B') == 'B'
        assert auto_select(values, 'X') == 'A'


class TestGUIMaskDisplayLogic:
    """GUI Mask 顯示邏輯測試"""
    
    def test_mask_label_format(self):
        """測試 Mask 標籤格式化"""
        def format_mask_label(mask_val, mask_bytes):
            return f"Enable Mask: 0x{mask_val & 0xFFFFFFFF:0{mask_bytes*2}X} ({mask_bytes} byte(s))"
        
        result = format_mask_label(0x0001, 1)
        assert "0x01" in result
        assert "1 byte" in result
        
        result = format_mask_label(0x0103, 2)
        assert "2 byte" in result


class TestGUIFileOperationsLogic:
    """GUI 檔案操作邏輯測試"""
    
    def test_export_to_text(self, temp_hex_file):
        """測試匯出為文字"""
        viewer = RegisterViewer()
        viewer.current_buffer = bytearray([i for i in range(256)])
        
        success, msg = viewer.export_to_text(temp_hex_file)
        assert success
        
        # 驗證檔案內容
        with open(temp_hex_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 256
    
    def test_file_dialog_patterns(self):
        """測試檔案對話框模式"""
        def get_file_filters(file_type):
            filters = {
                'csv': [("CSV Config", "*.csv")],
                'hex': [("HEX File", "*.hex")],
                'excel': [("Excel Files", "*.xlsx *.xls")],
            }
            return filters.get(file_type, [("All Files", "*.*")])
        
        assert get_file_filters('csv') == [("CSV Config", "*.csv")]
        assert get_file_filters('hex') == [("HEX File", "*.hex")]
        assert get_file_filters('unknown') == [("All Files", "*.*")]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
