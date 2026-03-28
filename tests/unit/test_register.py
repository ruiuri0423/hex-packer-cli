"""
Register Parser 模組單元測試
"""

import pytest
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.register import (
    parse_register_excel_to_buffer,
    parse_register_excel_with_mapping,
    validate_register_excel
)


class TestParseRegisterExcel:
    """寄存器 Excel 解析測試"""
    
    def test_function_exists(self):
        """測試函數存在"""
        assert callable(parse_register_excel_to_buffer)
        assert callable(parse_register_excel_with_mapping)
    
    def test_validate_nonexistent_file(self):
        """測試驗證不存在的檔案"""
        success, msg = validate_register_excel("/nonexistent/file.xlsx")
        assert success is False


class TestRegisterMapping:
    """寄存器映射測試"""
    
    def test_mapping_function_exists(self):
        """測試映射函數存在"""
        assert callable(parse_register_excel_with_mapping)


class TestRegisterExcelValidation:
    """寄存器 Excel 驗證測試"""
    
    def test_validation_with_nonexistent_file(self):
        """測試驗證不存在的檔案"""
        success, msg = validate_register_excel("/nonexistent/file.xlsx")
        assert success is False
        assert "not found" in msg.lower()
    
    def test_validation_without_pandas(self):
        """測試沒有 pandas 的情況"""
        # 嘗試匯入 pandas，如果失敗應該返回適當錯誤
        try:
            import pandas as pd
            # pandas 可用，跳過
            pass
        except ImportError:
            # pandas 不可用，應返回 False
            success, msg = validate_register_excel("/nonexistent/file.xlsx")
            assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
