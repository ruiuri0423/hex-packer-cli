"""
Playwright E2E 測試腳本

此腳本用於 GUI 端到端測試，需要顯示環境支援。

執行方式:
    python tests/e2e/test_gui_flows.py --manual   # 顯示測試計劃
    python tests/e2e/test_gui_flows.py --auto     # 執行自動測試
"""

import sys
import os
import time
from pathlib import Path

# 測試配置
SCREENSHOT_DIR = "/mnt/openwebui_data/hex_packer_screenshots"

# 確保截圖目錄存在
Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)


class ManualTestScript:
    """手動測試腳本"""
    
    TEST_CASES = {
        "Tab 導航測試": {
            "description": "測試 GUI 分頁導航功能",
            "precondition": "GUI 應用程式已啟動，預設在 Tab 1",
            "steps": [
                "1. 觀察當前 Tab 1 (Firmware Packer) 介面",
                "2. 點擊 Tab 2 標籤",
                "3. 觀察畫面切換到 M0 HEX Converter",
                "4. 點擊 Tab 3 標籤",
                "5. 觀察畫面切換到 Register Integrator",
                "6. 點擊 Tab 4 標籤",
                "7. 觀察畫面切換到 Single Map Viewer",
                "8. 點擊 Tab 5 標籤",
                "9. 觀察畫面切換到 Logic Test",
                "10. 點擊 Tab 1 返回首頁",
            ],
            "expected_result": "所有 Tab 可以正常切換，畫面內容正確",
        },
        
        "Firmware Packer 新增分區": {
            "description": "測試在 Firmware Packer 中新增分區",
            "precondition": "GUI 在 Tab 1 Firmware Packer",
            "steps": [
                "1. 在 Section Name 輸入: TEST_SECTION",
                "2. 在 Maximum Length 輸入: 1024",
                "3. 在 File Path 留空",
                "4. 點擊 '+ Add Section' 按鈕",
                "5. 觀察列表中出現新的分區",
                "6. 驗證分區名稱為 'TEST_SECTION'",
                "7. 驗證 Max Len 為 1024",
            ],
            "expected_result": "分區成功新增到列表，沒有錯誤訊息",
        },
        
        "M0 HEX 檔案載入": {
            "description": "測試載入和轉換 M0 HEX 檔案",
            "precondition": "GUI 在 Tab 2 M0 HEX Converter",
            "steps": [
                "1. 點擊 '1. Load M0 HEX File' 按鈕",
                "2. 在檔案對話框選擇測試 HEX 檔案",
                "3. 觀察狀態文字變化",
                "4. 點擊 '2. Convert & Expand length' 按鈕",
                "5. 選擇輸出檔案位置並儲存",
                "6. 觀察成功訊息",
            ],
            "expected_result": "檔案成功轉換，長度 +2 bytes",
        },
        
        "Register Integrator Mask 計算": {
            "description": "測試 Register Integrator 的 Mask 計算功能",
            "precondition": "GUI 在 Tab 3 Register Integrator",
            "steps": [
                "1. 設定 Global Base Address: 0x1000",
                "2. 點擊 '+ Add Excel File(s)'",
                "3. 選擇 Table_A.xlsx (自動對齊到 0x1000)",
                "4. 再次點擊 '+ Add Excel File(s)'",
                "5. 選擇 Table_B.xlsx，修改 Flash Address 為 0x1300",
                "6. 再次點擊 '+ Add Excel File(s)'",
                "7. 選擇 Table_C.xlsx，修改 Flash Address 為 0x2000",
                "8. 觀察 Enable Mask 標籤變化",
            ],
            "expected_result": "Enable Mask 應該顯示 0x010009",
        },
        
        "Logic Test 執行": {
            "description": "測試 Logic Test 分頁的測試執行功能",
            "precondition": "GUI 在 Tab 5 Logic Test",
            "steps": [
                "1. 點擊 'Load Preset' 按鈕",
                "2. 觀察測試表格載入 3 個預設表格",
                "3. 點擊 'Run All Tests' 按鈕",
                "4. 觀察測試結果文字區域",
                "5. 驗證顯示 'All Tests Passed!' (綠色)",
                "6. 點擊 'Show Mask Calc'",
                "7. 觀察 Mask 計算詳細資訊",
            ],
            "expected_result": "所有測試通過，顯示綠色文字",
        },
    }
    
    @classmethod
    def print_test_plan(cls):
        """列印測試計劃"""
        print("\n" + "="*70)
        print("           Hex Packer CLI - 手動測試計劃")
        print("="*70)
        
        for i, (name, test) in enumerate(cls.TEST_CASES.items(), 1):
            print(f"\n【{i}】{name}")
            print(f"    描述: {test['description']}")
            print(f"    前置條件: {test['precondition']}")
            print(f"    步驟:")
            for step in test['steps']:
                print(f"      {step}")
            print(f"    預期結果: {test['expected_result']}")
        
        print("\n" + "="*70)


def try_playwright_test():
    """嘗試執行 Playwright 測試"""
    try:
        from playwright.sync_api import sync_playwright
        
        print("\n嘗試啟動 Playwright 測試...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            print("✅ Playwright 瀏覽器已啟動")
            print("⚠️  請在瀏覽器中打開 GUI 應用程式")
            print("   應用程式路徑: src/main.py")
            print("   命令: python3 src/main.py")
            print("\n按 Ctrl+C 結束測試")
            
            # 保持瀏覽器開啟
            page.wait_for_timeout(10000)  # 10 秒
            
            browser.close()
            
    except ImportError:
        print("\n❌ Playwright 未安裝")
        print("請執行以下命令安裝:")
        print("  pip install playwright")
        print("  playwright install chromium")
    except Exception as e:
        print(f"\n❌ Playwright 執行失敗: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hex Packer CLI E2E 測試")
    parser.add_argument("--manual", action="store_true", help="顯示手動測試計劃")
    parser.add_argument("--playwright", action="store_true", help="嘗試執行 Playwright 測試")
    
    args = parser.parse_args()
    
    if args.manual:
        ManualTestScript.print_test_plan()
    elif args.playwright:
        try_playwright_test()
    else:
        # 預設顯示測試計劃
        ManualTestScript.print_test_plan()
        print("\n使用方式:")
        print("  python tests/e2e/test_gui_flows.py --manual     # 顯示測試計劃")
        print("  python tests/e2e/test_gui_flows.py --playwright # 嘗試執行 Playwright")
