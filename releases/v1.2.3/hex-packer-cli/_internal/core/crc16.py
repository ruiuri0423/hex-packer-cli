"""
CRC16 Module - 平行 CRC16 計算
對應硬體 Verilog 邏輯

版本: 1.2.3
修改: 統一使用原始程式碼的實作邏輯，確保與硬體 Verilog 完全一致
"""

from typing import Union, List

# CRC16 參數
POLYNOMIAL = 0x8005  # CRC-16
INIT_VALUE = 0x0052  # 初始值


def calculate_custom_crc16(data: Union[bytearray, List[int]]) -> int:
    """
    平行 CRC16 計算對應硬體 Verilog 邏輯。

    多項式: 0x8005
    初始值: 0x0052
    
    此實作完全對應 FPGA/Verilog 的平行 CRC16 邏輯，
    每一個位元都有獨立的 XOR 運算對照表。

    Args:
        data: 輸入資料 (bytearray 或 8-bit 整數列表)

    Returns:
        16-bit CRC 值

    Example:
        >>> calculate_custom_crc16(bytearray([0x00, 0x01, 0x02]))
        12345
    """
    bo = INIT_VALUE  # 初始 CRC 值

    for d_in in data:
        # XOR input with current CRC
        x = bo ^ d_in

        # 提取位元 0-15
        x_bit = [(x >> i) & 1 for i in range(16)]

        # 初始化 new_bo 為全 0
        new_bo = [0] * 16

        # --- 平行位元 XOR 邏輯 (嚴格對應 Verilog) ---
        # 這些是根據 CRC 多項式 0x8005 推導出的邏輯表達式
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

        # 重構 16-bit CRC 值 (與原始程式碼完全一致)
        bo = 0
        for i in range(16):
            bo |= (new_bo[i] << i)

    return bo


def calculate_crc16_fast(data: Union[bytearray, List[int]]) -> int:
    """
    快速 CRC16 計算 - 統一使用 calculate_custom_crc16 的結果作為標準。

    Args:
        data: 輸入資料

    Returns:
        16-bit CRC 值
    """
    return calculate_custom_crc16(data)


if __name__ == "__main__":
    # 簡單測試
    test_data = bytearray([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])
    print(f"Test data: {list(test_data)}")
    print(f"CRC16: 0x{calculate_custom_crc16(test_data):04X}")
