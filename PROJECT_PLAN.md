# 水网工程水力调控智能平台 V2.0 Web门户版

 # 项目执行计划 — 成员2：数据库与业务后台

> 最后更新：2026-08-01
> 状态：全部 5 个 Phase 已完成

## 架构决策

| 决策 | 方案 | 原因 |
|------|------|------|
| ORM | SQLAlchemy 2.0（已有） | 与现有代码一致，支持 SQLite/PostgreSQL 双模式 |
| 密码 | PBKDF2-SHA256 / 260k 迭代（已有） | 安全且已实现，无需更换 |
| 导入策略 | 逐行跳过 | 坏行不入库，有效行正常写入，报告所有失败行号+原因 |
| 导出格式 | CSV + Excel | 满足日常使用，CSV 便于程序处理，Excel 便于人工查看 |
| 密码规则 | 8位+字母+数字 | 最低安全标准 |
| 用户删除 | 软删除（enabled=False） | 保留审计轨迹 |

## 修改范围约束

- **可修改**：`database/`、`services/data_service.py`、`services/auth_service.py`、`services/log_service.py`、`services/alert_service.py`、`services/template_service.py`
- **禁止修改**：`ui/`、`assets/`、`app.py`、`services/prediction_service.py`、`services/scheduling_service.py`

## Phase 进度

| Phase | 状态 | 完成日期 |
|-------|------|----------|
| Phase 1: 数据库表结构优化 | ✅ 已完成 | 2026-08-01 |
| Phase 2: 导入导出核心功能 | ✅ 已完成 | 2026-08-01 |
| Phase 3: 用户管理与安全 | ✅ 已完成 | 2026-08-01 |
| Phase 4: 运维功能 | ✅ 已完成 | 2026-08-01 |
| Phase 5: 测试与交付文档 | ✅ 已完成 | 2026-08-01 |

## Phase 1 任务

- [x] 1.1 Alert 表增加 `handled_at` 字段
- [x] 1.2 OperationLog 表增加 `log_type` 字段
- [x] 1.3 验证唯一编号完整性
- [x] 1.4 更新 init_db.py 确保新字段生效

## Phase 2 任务

- [x] 2.1 重构导入校验：逐行 + 行号报告
- [x] 2.2 防止重复导入：inserted/updated/skipped 计数
- [x] 2.3 数据导出：CSV + Excel

## Phase 3 任务

- [x] 3.1 用户管理：list_users / set_user_enabled / delete_user / change_password
- [x] 3.2 密码复杂度校验：validate_password_strength
- [x] 3.3 操作日志全面覆盖

## Phase 4 任务

- [x] 4.1 预警确认：handled_at + 日志
- [x] 4.2 数据库备份恢复检查：verify_backup + restore_from_json

## Phase 5 任务

- [x] 5.1 后台函数测试
- [x] 5.2 交付文档：数据表说明.md + 修改说明.md + 导入模板更新

## 现有代码审查摘要（2026-08-01）

### 数据模型（database/models.py）
- 13 个模型，覆盖用户、站点、河道、闸门、泵站、4 种监测数据、预测、调度、预警、日志、模型注册、上传文件
- Alert 缺 `handled_at`，OperationLog 缺 `log_type`

### 服务层
- auth_service：PBKDF2 哈希 + 认证 + create_or_update_user（缺禁用/密码修改/列表）
- data_service：导入/查询/备份（缺逐行校验、错误报告、CSV/Excel 导出）
- log_service：基本日志框架（缺 delete/alert/export/user 操作的日志调用）
- alert_service：阈值预警 + 状态更新（缺 handled_at 设置和日志）
- template_service：内存模板 + Excel 导出工具函数

### 测试
- 仅有 tests/smoke_test.py（1 个测试）
