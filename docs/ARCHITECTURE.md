# Project OS - Architecture

## 1. Architecture Pattern
- Lớp giao diện: MVC / UI-centric.
- Lớp nghiệp vụ: Service Layer.
- Lớp lưu trữ: Repository Pattern.
- Dependency injection đơn giản.

## 2. Tech Stack
- Python 3.11+
- PyWebView và HTML/CSS/JavaScript cho giao diện desktop
- `pathlib` cho thao tác đường dẫn
- JSON cho lưu trữ local storage (settings và metadata)
- `pytest`, `ruff`, `mypy` cho kiểm thử và chất lượng code.

## 3. Core Components
- **UI**: static frontend trong `web/`, kết nối backend qua `ApiBridge`.
- **Services**: `workspace_scan_service`, `project_service`, `file_service`, `delivery_service`, `ai_service`.
- **Repositories**: `settings_repository`, `project_repository`.
- **Utils**: `atomic_json` (đảm bảo an toàn dữ liệu khi lưu JSON), `path_validator`.
