"""
Register Viewer 模組單元測試
"""

import pytest
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.viewer import RegisterViewer


class TestRegisterViewerInit:
    """RegisterViewer 初始化測試"""
    
    def test_init_without_treeview(self):
        """測試不帶 Treeview 初始化"""
        viewer = RegisterViewer()
        assert viewer.tree is None
        assert viewer.current_map == []
        assert viewer.current_buffer is None
    
    def test_init_with_treeview(self):
        """測試帶 Treeview 初始化"""
        mock_tree = {"mock": "tree"}
        viewer = RegisterViewer(treeview=mock_tree)
        assert viewer.tree == mock_tree


class TestRegisterViewerGap:
    """RegisterViewer Gap 功能測試"""
    
    def test_add_gap_to_map(self):
        """測試加入 Gap 到映射"""
        viewer = RegisterViewer()
        
        gap = viewer.add_gap_to_map(
            gap_start=0,    # Bit 0
            gap_end=7       # Bit 7
        )
        
        assert 'is_gap' in gap
        assert gap['is_gap'] is True
        assert len(viewer.current_map) == 1
    
    def test_gap_calculation(self):
        """測試 Gap 計算"""
        viewer = RegisterViewer()
        
        # 測試簡單 Gap
        gap = viewer.add_gap_to_map(0, 255)
        
        # 驗證位址計算
        assert gap['low_addr'] == 'h0000'  # 0 // 8 = 0
        assert gap['high_addr'] == 'h001F'  # 255 // 8 = 31


class TestRegisterViewerExport:
    """RegisterViewer 匯出功能測試"""
    
    def test_export_without_buffer(self, temp_nonexistent_path):
        """測試沒有緩衝區時匯出"""
        viewer = RegisterViewer()
        # 沒有緩衝區時，無論路徑是否存在都應該返回 False
        success, msg = viewer.export_to_text(temp_nonexistent_path)
        assert success is False
    
    def test_export_with_buffer(self, temp_txt_file):
        """測試有緩衝區時匯出"""
        viewer = RegisterViewer()
        viewer.current_buffer = bytearray([i for i in range(256)])
        
        success, msg = viewer.export_to_text(temp_txt_file)
        assert success is True
        
        # 驗證檔案內容
        import os
        assert os.path.exists(temp_txt_file)
        with open(temp_txt_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 256


class TestRegisterViewerRegister:
    """RegisterViewer 寄存器查詢測試"""
    
    def test_get_register_by_name_empty(self):
        """測試空映射中查詢"""
        viewer = RegisterViewer()
        result = viewer.get_register_by_name("TEST")
        assert result is None
    
    def test_get_register_by_name_found(self):
        """測試查詢存在的寄存器"""
        viewer = RegisterViewer()
        viewer.current_map = [
            {'name': 'REG_A', 'addr': 0x00},
            {'name': 'REG_B', 'addr': 0x10},
        ]
        
        result = viewer.get_register_by_name('REG_A')
        assert result is not None
        assert result['name'] == 'REG_A'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
