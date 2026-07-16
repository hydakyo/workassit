# Project OS - Architecture

## 1. Architecture Pattern
- Lớp giao diện: MVC / UI-centric.
- Lớp nghiệp vụ: Service Layer.
- Lớp lưu trữ: Repository Pattern.
- Dependency injection đơn giản.

## 2. Tech Stack
- Python 3.11+
- CustomTkinter / Tkinter cho giao diện
- `pathlib` cho thao tác đường dẫn
- JSON cho lưu trữ local storage (settings và metadata)
- `pytest`, `ruff`, `mypy` cho kiểm thử và chất lượng code.

## 3. Core Components
- **UI**: `main_window`, `dashboard_view`, `settings_view`.
- **Services**: `workspace_scan_service`, `task_executor`.
- **Repositories**: `settings_repository`, `project_repository`.
- **Utils**: `atomic_json` (đảm bảo an toàn dữ liệu khi lưu JSON), `path_validator`.
