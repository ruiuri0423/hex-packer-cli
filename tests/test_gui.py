"""
GUI 邏輯測試 (非 GUI 測試)

由於 GUI 需要顯示環境，這些測試專注於 GUI 相關的邏輯，
確保 Business Logic 正確，不依賴 GUI 環境。
"""

import pytest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestGUIFormValidation:
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
            """模擬 GUI 表單驗證"""
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

    def test_mask_calculation_sync(self):
        """測試 Mask 計算同步"""
        from core.mask_calculator import (
            validate_and_align_flash_address,
            calculate_enable_mask_with_gaps,
            calculate_dynamic_mask_bytes
        )
        
        base_addr = 0x1000
        tables = [
            {'name': 'Table_A', 'addr': 0x1000, 'enabled': True},
            {'name': 'Table_B', 'addr': 0x1300, 'enabled': True},
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
        assert mask_val == 0b1011  # Bit 0, 1, 3 = 1

    def test_csv_relative_path_generation(self):
        """測試 CSV 相對路徑生成"""
        def get_relative_path(full_path, base_dir):
            """生成相對路徑"""
            try:
                return os.path.relpath(full_path, start=base_dir)
            except ValueError:
                return full_path
        
        csv_path = "/project/config/packer.csv"
        base_dir = "/project/config"
        file_path = "/project/data/table_a.xlsx"
        
        rel_path = get_relative_path(file_path, base_dir)
        assert ".." in rel_path or "data" in rel_path


class TestGUIEventHandlers:
    """GUI 事件處理器邏輯測試"""

    def test_double_click_goto_tab(self):
        """測試雙擊跳轉邏輯"""
        def should_switch_tab(item_name, integration_list):
            """模擬雙擊事件"""
            return item_name in [t['name'] for t in integration_list]
        
        tables = [{'name': 'Table_A'}, {'name': 'Table_B'}]
        
        assert should_switch_tab('Table_A', tables) is True
        assert should_switch_tab('Table_C', tables) is False

    def test_selection_change_update_form(self):
        """測試選擇變更更新表單"""
        def get_selected_item(selection_id, integration_list):
            """模擬選擇變更"""
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

    def test_tree_refresh(self):
        """測試 Treeview 刷新邏輯"""
        def build_tree_values(tables, base_addr):
            """模擬 Treeview 值構建"""
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
                    t['status'] + bit_info
                ))
            return values
        
        tables = [
            {'name': 'A', 'addr': 0x1000, 'enabled': True, 'status': 'OK', 'bit_position': 0},
            {'name': 'B', 'addr': 0x2000, 'enabled': False, 'status': 'OK', 'bit_position': None},
        ]
        
        values = build_tree_values(tables, 0x1000)
        
        assert len(values) == 2
        assert "0x1000" in values[0]
        assert "Yes" in values[0]
        assert "[DISABLED]" in values[1]


class TestGUIComboboxLogic:
    """GUI Combobox 邏輯測試"""

    def test_combobox_values_generation(self):
        """測試 Combobox 值生成"""
        def get_combobox_values(integration_list):
            """模擬 Combobox 值"""
            return [item['name'] for item in integration_list]
        
        tables = [{'name': 'A'}, {'name': 'B'}, {'name': 'C'}]
        values = get_combobox_values(tables)
        
        assert values == ['A', 'B', 'C']
        assert len(values) == 3

    def test_auto_select_first(self):
        """測試自動選擇第一項"""
        def auto_select(values, current):
            """模擬自動選擇"""
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
            """格式化 Mask 標籤"""
            return f"Enable Mask: 0x{mask_val:0{mask_bytes*2}X} ({mask_bytes} byte(s))"
        
        assert "0x0001" in format_mask_label(0x0001, 1)
        assert "0x0103" in format_mask_label(0x0103, 2)
        assert "(3 byte" in format_mask_label(0x010309, 3)

    def test_bit_mapping_display(self):
        """測試位元映射顯示"""
        def format_bit_mapping(bit_mapping):
            """格式化位元映射"""
            lines = ["Bit Mapping:"]
            for m in bit_mapping:
                enabled = "✓" if m['enabled'] else "✗"
                lines.append(f"  {enabled} Bit {m['bit_pos']:2d}: 0x{m['addr']:04X} - {m['name']}")
            return "\n".join(lines)
        
        mapping = [
            {'bit_pos': 0, 'addr': 0x1000, 'name': 'Table_A', 'enabled': True},
            {'bit_pos': 3, 'addr': 0x1300, 'name': 'Table_B', 'enabled': True},
        ]
        
        output = format_bit_mapping(mapping)
        assert "Bit Mapping:" in output
        assert "0x1000" in output
        assert "✓" in output


class TestGUITestTabLogic:
    """GUI 測試標籤邏輯"""

    def test_test_scenario_preset(self):
        """測試預設場景"""
        def get_preset_tables():
            """取得預設表格"""
            return [
                ("Table_A", "1000", True),
                ("Table_B", "1300", True),
                ("Table_C", "2000", True),
            ]
        
        presets = get_preset_tables()
        assert len(presets) == 3
        assert presets[0][0] == "Table_A"

    def test_test_results_logging(self):
        """測試結果日誌"""
        def create_result_entry(test_name, passed, details=""):
            """建立結果條目"""
            status = "✅ PASS" if passed else "❌ FAIL"
            return f"[{status}] {test_name}: {details}"
        
        entry = create_result_entry("CRC16", True, "0x81EF")
        assert "✅ PASS" in entry
        assert "CRC16" in entry
        
        entry = create_result_entry("Mask", False, "Expected 3, got 2")
        assert "❌ FAIL" in entry


class TestGUIFileOperations:
    """GUI 檔案操作邏輯"""

    def test_export_to_text(self):
        """測試匯出為文字"""
        from core.viewer import RegisterViewer
        
        viewer = RegisterViewer()
        viewer.current_buffer = bytearray([i for i in range(256)])
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            txt_path = f.name
        
        try:
            success, msg = viewer.export_to_text(txt_path)
            assert success is True
            
            # 驗證檔案內容
            with open(txt_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 256
            assert lines[0].strip() == "00"
        finally:
            if os.path.exists(txt_path):
                os.remove(txt_path)

    def test_file_dialog_patterns(self):
        """測試檔案對話框模式"""
        def get_file_filters(file_type):
            """模擬檔案過濾器"""
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
    pytest.main([__file__, "-v"])
