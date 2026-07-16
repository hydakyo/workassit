# Project OS - Product Requirements Document

## 1. Overview
Project OS là ứng dụng desktop Local-First dành cho kỹ sư triển khai hạ tầng mạng và an ninh mạng.
Giúp quản lý project workspace trên ổ cứng Windows, tài liệu, cấu hình, workspace roots, metadata, file versioning, checklist, delivery package, và tích hợp AI local/cloud.

## 2. Goals
- Quản lý dự án dựa trên file system thực tế (Local-First).
- Không khóa dữ liệu vào database riêng, file dự án có thể truy cập trực tiếp bằng File Explorer.
- UI trực quan, không chặn luồng khi quét thư mục.
- Đảm bảo an toàn dữ liệu (Atomic JSON write).

## 3. Scope
Ứng dụng sẽ được phát triển qua nhiều giai đoạn (Phases).
Xem `PHASES.md` để biết thêm chi tiết.
