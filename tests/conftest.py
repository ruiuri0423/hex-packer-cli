"""
Pytest Configuration & Shared Fixtures

Hex Packer CLI - Test Suite Configuration

提供所有測試共享的 fixtures 和配置。
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# 確保 src/core 可以被匯入
SRC_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_ROOT))


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def project_root():
    """專案根目錄"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def src_root():
    """src 目錄"""
    return Path(__file__).parent.parent / "src"


@pytest.fixture(scope="session")
def test_data_root():
    """測試資料目錄"""
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


# ============================================================================
# Temporary File Fixtures
# ============================================================================

@pytest.fixture
def temp_hex_file():
    """臨時 HEX 檔案"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.hex', delete=False) as f:
        filepath = f.name
    
    yield filepath
    
    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)


@pytest.fixture
def temp_csv_file():
    """臨時 CSV 檔案"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        filepath = f.name
    
    yield filepath
    
    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)


@pytest.fixture
def temp_dir():
    """臨時目錄"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    
    # Cleanup
    import shutil
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


@pytest.fixture
def temp_txt_file():
    """臨時文字檔案"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        filepath = f.name
    
    yield filepath
    
    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)


@pytest.fixture
def temp_nonexistent_path():
    """產生一個不存在的檔案路徑（用於錯誤處理測試）"""
    import uuid
    return f"/nonexistent_{uuid.uuid4().hex[:8]}.test"


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_hex_data():
    """標準 HEX 資料樣本"""
    return bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])


@pytest.fixture
def sample_hex_string():
    """標準 HEX 字串"""
    return "00 01 02 03 04 05"


@pytest.fixture
def sample_intel_hex():
    """Intel HEX 格式樣本"""
    return ":06000100010203040506AB\n"


@pytest.fixture
def sample_raw_hex():
    """Raw HEX 格式樣本"""
    return "00 01 02 03 04 05\n"


@pytest.fixture
def base_address():
    """標準 Base 位址"""
    return 0x1000


@pytest.fixture
def sample_flash_tables(base_address):
    """標準 Flash 表格列表"""
    return [
        {'name': 'Table_A', 'addr': base_address},           # 0x1000 → Bit 0
        {'name': 'Table_B', 'addr': base_address + 0x300},   # 0x1300 → Bit 3
        {'name': 'Table_C', 'addr': base_address + 0x1000}, # 0x2000 → Bit 16
    ]


# ============================================================================
# CRC16 Fixtures
# ============================================================================

@pytest.fixture
def crc16_test_cases():
    """CRC16 測試案例集合"""
    return {
        'empty': {
            'input': bytearray(),
            'description': '空資料'
        },
        'single_zero': {
            'input': bytearray([0x00]),
            'description': '單一字節 0x00'
        },
        'single_ff': {
            'input': bytearray([0xFF]),
            'description': '單一字節 0xFF'
        },
        'multiple': {
            'input': bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05]),
            'description': '連續序列'
        },
        'mixed': {
            'input': bytearray([0xAA, 0xBB, 0xCC, 0xDD]),
            'description': '混合資料'
        },
        'all_zeros': {
            'input': bytearray([0x00] * 100),
            'description': '100 bytes 全零'
        },
        'all_ff': {
            'input': bytearray([0xFF] * 100),
            'description': '100 bytes 全 FF'
        },
        'large_data': {
            'input': bytearray([i % 256 for i in range(1000)]),
            'description': '1000 bytes 遞增'
        },
    }


@pytest.fixture
def crc16_expected_values():
    """CRC16 預期值 (用於迴歸測試)"""
    return {
        'single_zero': 0x81EF,  # 0x00 的 CRC
        'single_ff': 0x83ED,   # 0xFF 的 CRC
    }


# ============================================================================
# Mask Calculator Fixtures
# ============================================================================

@pytest.fixture
def mask_test_cases():
    """Mask 計算測試案例"""
    return [
        {
            'name': 'Flash < Base',
            'item_addr': 0x0500,
            'base_addr': 0x1000,
            'expected_addr': 0x1000,
            'was_adjusted': True
        },
        {
            'name': '非 256 對齊',
            'item_addr': 0x1234,
            'base_addr': 0x1000,
            'expected_addr': 0x1200,
            'was_adjusted': True
        },
        {
            'name': '已是對齊',
            'item_addr': 0x1500,
            'base_addr': 0x1000,
            'expected_addr': 0x1500,
            'was_adjusted': False
        },
        {
            'name': '等於 Base',
            'item_addr': 0x1000,
            'base_addr': 0x1000,
            'expected_addr': 0x1000,
            'was_adjusted': False
        },
    ]


@pytest.fixture
def mask_bytes_test_cases():
    """Mask 位元組計算測試案例"""
    return [
        {
            'name': '單一表格',
            'max_addr': 0x1000,
            'base_addr': 0x1000,
            'expected_bytes': 1,
            'expected_bits': 1
        },
        {
            'name': '兩表格',
            'max_addr': 0x1100,
            'base_addr': 0x1000,
            'expected_bytes': 1,
            'expected_bits': 2
        },
        {
            'name': '多表格',
            'max_addr': 0x2000,
            'base_addr': 0x1000,
            'expected_bytes': 3,
            'expected_bits': 17
        },
        {
            'name': '長距離',
            'max_addr': 0x5000,
            'base_addr': 0x1000,
            'expected_bytes': 9,
            'expected_bits': 65
        },
    ]


# ============================================================================
# HEX Parser Fixtures
# ============================================================================

@pytest.fixture
def address_parse_cases():
    """位址解析測試案例"""
    return [
        ('h00FF', 0x00FF),
        ('hFF', 0xFF),
        ('0xFF', 0xFF),
        ('0x1234', 0x1234),
        ('FF', 0xFF),
        ('1234', 0x1234),
        ('abcd', 0xABCD),
        ('ABCDEF', 0xABCDEF),
        (255, 255),
        (0x1234, 0x1234),
        ('', -1),
        ('invalid', -1),
        ('xyz', -1),
    ]


@pytest.fixture
def hex_write_read_cases():
    """HEX 寫入讀取測試案例"""
    return [
        bytearray(),
        bytearray([0xFF]),
        bytearray([0x00, 0x01, 0x02]),
        bytearray([0x00, 0xFF, 0xAA, 0x55]),
        bytearray([i % 256 for i in range(256)]),
    ]


# ============================================================================
# Packer Fixtures
# ============================================================================

@pytest.fixture
def minimal_section():
    """最小分區配置"""
    return {
        'name': 'TEST',
        'max_len': 1024,
        'file_path': '',
        'is_full': True,
        'inject_err': False,
        'target_sec': '',
        'size_offset': '',
        'size_offset_orig': '',
        'en_offset': '',
        'en_offset_orig': '',
        'en_bit': '',
        'en_val': 1,
        'crc_offset': '',
        'crc_offset_orig': '',
        'crc_bit': '',
        'crc_val': 1,
        'addr_offset': '',
        'addr_offset_orig': '',
        'mask_target': '',
        'mask_offset': '',
        'mask_offset_orig': '',
        'mask_val': 0,
        'calc_addr': 0,
        'bypass_crc': False
    }


@pytest.fixture
def sample_csv_config(minimal_section, temp_csv_file):
    """樣本 CSV 配置"""
    import pandas as pd
    
    df = pd.DataFrame([minimal_section])
    df.to_csv(temp_csv_file, index=False)
    
    return temp_csv_file


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_treeview(mocker):
    """Mock Tkinter Treeview"""
    return mocker.MagicMock()


@pytest.fixture
def mock_messagebox(mocker):
    """Mock Tkinter messagebox"""
    return mocker.patch('tkinter.messagebox')


@pytest.fixture
def mock_filedialog(mocker):
    """Mock Tkinter filedialog"""
    mock = mocker.MagicMock()
    mock.askopenfilename.return_value = ""
    mock.asksaveasfilename.return_value = ""
    return mock


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Pytest 配置鉤子"""
    config.addinivalue_line(
        "markers", "unit: 單元測試"
    )
    config.addinivalue_line(
        "markers", "integration: 整合測試"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速測試"
    )


def pytest_collection_modifyitems(config, items):
    """自動標記測試"""
    for item in items:
        # 根據路徑自動標記
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
        
        # 根據名稱自動標記慢速測試
        if "large_data" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)
