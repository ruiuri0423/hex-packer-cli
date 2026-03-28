# GitHub Actions CI/CD

此目錄用於存放 GitHub Actions 工作流配置。

## 需要的 Token 權限

若要啟用 GitHub Actions CI，請使用具有以下權限的 Personal Access Token：

| Scope | 用途 |
|-------|------|
| `repo` | 推送程式碼 |
| `workflows` | 管理 GitHub Actions 工作流 |

## 手動啟用 CI

請在 GitHub repository 設定中啟用 Actions，或使用具有 `workflow` 權限的 token 推送 `.github/workflows/` 目錄。

## 測試命令

```bash
pip install pytest pandas openpyxl
python -m pytest tests/ -v
```
