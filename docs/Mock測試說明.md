# 🔍 Mock 測試說明

## 什麼是 Mock？

**Mock** 是「模擬對象」的意思。在測試中，我們用 Mock 來**模擬**真實的 GUI 元件（如按鈕、輸入框等），而不是真的創建一個 GUI 視窗。

---

## 為什麼需要 Mock？

### 問題情境
```
真實 GUI 測試需要:
┌─────────────────────────────────────────┐
│  ❌ 需要顯示器/視窗環境                   │
│  ❌ 需要實際的 Tkinter 視窗              │
│  ❌ 測試執行緩慢                          │
│  ❌ 難以自動化 CI/CD 流程                │
└─────────────────────────────────────────┘
```

### Mock 測試的優點
```
┌─────────────────────────────────────────┐
│  ✅ 不需要顯示器/視窗環境                 │
│  ✅ 不需要實際的 Tkinter                 │
│  ✅ 測試執行快速                          │
│  ✅ 容易自動化 CI/CD                     │
│  ✅ 專注測試「邏輯」而非「外觀」          │
└─────────────────────────────────────────┘
```

---

## 實際範例

### 傳統 GUI 測試（需要真實視窗）
```python
import tkinter as tk

# 需要真的創建視窗
root = tk.Tk()
entry = tk.Entry(root)
entry.insert(0, "0xFF")

# 需要真的點擊按鈕
def on_click():
    value = entry.get()
    # 驗證邏輯
    assert value == "0xFF"

button = tk.Button(root, text="Click", command=on_click)
root.mainloop()  # 需要視窗環境
```

### Mock 測試（不需要真實視窗）
```python
from unittest.mock import Mock

# 模擬 GUI 元件
mock_entry = Mock()
mock_button = Mock()

# 設定回傳值
mock_entry.get.return_value = "0xFF"

# 測試邏輯
def on_click():
    value = mock_entry.get()
    # 驗證邏輯
    return value == "0xFF"

# 執行測試
assert on_click() is True
```

---

## Mock vs 真實測試 比較

| 特性 | Mock 測試 | 真實 GUI 測試 |
|------|------------|----------------|
| **環境需求** | 只需要 Python | 需要顯示器 + Tkinter |
| **執行速度** | ⚡ 快 (毫秒) | 🐢 慢 (秒) |
| **穩定性** | ✅ 高 (不受 UI 變更影響) | ⚠️ 低 (UI 變更可能破壞測試) |
| **測試重點** | 商業邏輯 | UI 互動流程 |
| **自動化難度** | 簡單 | 複雜 |
| **適用場景** | 單元測試 | E2E 測試 |

---

## 我們的測試策略

```
┌─────────────────────────────────────────────────────────────────┐
│                        測試金字塔                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                          ▲                                      │
│                         /E\          E2E (Playwright)           │
│                        /2  \         - 真實 GUI 測試            │
│                       /      \        - 完整流程驗證             │
│                      /________\                                    │
│                                                                 │
│                     ▲                    Unit Tests (Mock)       │
│                    /M\                   - 商業邏輯驗證         │
│                   /3  \                  - 快速執行              │
│                  /      \                - 不需顯示器           │
│                 /________\                                      │
│                                                                 │
│              ▲                                                    │
│             /I\                Integration Tests                  │
│            /1  \               - 模組之間協作                    │
│           /______\                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

說明:
- E: E2E 測試 (少量)
- M: Mock 單元測試 (大量)
- I: 整合測試 (適量)
```

---

## 程式碼範例

### 範例 1: Mock 輸入框

```python
from unittest.mock import Mock

# 模擬輸入框
entry = Mock()
entry.get.return_value = "0xFF"  # 設定回傳值

# 測試驗證函數
def validate_hex(text):
    cleaned = text.replace("0x", "").replace("h", "")
    return int(cleaned, 16)

# 執行測試
result = validate_hex(entry.get())
assert result == 255  # 0xFF = 255
```

### 範例 2: Mock 按鈕狀態

```python
button = Mock()

# 模擬點擊事件
button.invoke()
button.invoke.assert_called_once()  # 驗證被呼叫

# 模擬狀態變更
button.config(state="disabled")
button.config.assert_called_with(state="disabled")
```

### 範例 3: Mock Treeview

```python
tree = Mock()
tree.selection.return_value = ["1"]  # 模擬選擇第二項
tree.get_children.return_value = ["0", "1", "2"]

# 測試選擇邏輯
def get_selected(tree, items):
    selection = tree.selection()
    if selection:
        idx = int(selection[0])
        return items[idx]
    return None

items = ["A", "B", "C"]
result = get_selected(tree, items)
assert result == "B"
```

---

## 總結

| 問題 | 答案 |
|------|------|
| Mock 是什麼？ | 模擬物件，用來代替真實的 GUI 元件 |
| 為什麼用 Mock？ | 不需要視窗環境、測試快速、容易自動化 |
| Mock 測試什麼？ | GUI 的商業邏輯（如驗證、計算、狀態更新） |
| 什麼不測？ | GUI 的外觀、排版、顏色等 |

---

*文件更新時間: 2026-03-28*
