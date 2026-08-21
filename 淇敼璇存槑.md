# 修改说明

> 水网工程水力调控智能平台 V1.0 — 成员2（数据库与业务后台）交付
> 更新日期：2026-08-01

## 一、修改文件清单

### 修改的文件
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `database/models.py` | 修改 | Alert 新增 handled_at；OperationLog 新增 log_type |
| `services/data_service.py` | 重写 | 逐行校验、ImportResult、防重复、CSV/Excel 导出 |
| `services/auth_service.py` | 重写 | 用户管理 7 个新函数、密码强度校验 |
| `services/log_service.py` | 修改 | add_log 增加 log_type 参数，query_logs 支持类型过滤 |
| `services/alert_service.py` | 修改 | handled_at 设置、日志集成、get_alert_by_id |
| `tests/smoke_test.py` | 保留 | 原有冒烟测试不动 |

### 新增的文件
| 文件 | 说明 |
|------|------|
| `services/backup_service.py` | 备份验证、JSON 恢复（安全/覆盖模式） |
| `tests/test_auth_service.py` | 用户认证测试（13 个用例） |
| `tests/test_data_service.py` | 导入导出测试（14 个用例） |
| `tests/test_alert_service.py` | 预警处理测试（3 个用例） |
| `tests/test_backup_service.py` | 备份恢复测试（5 个用例） |
| `数据表说明.md` | 13 张表的字段说明 + ER 关系 |
| `修改说明.md` | 本文档 |
| `PROJECT_PLAN.md` | 项目执行计划与进度追踪 |
| `database/` 目录下的 `.bak` 文件 | 原始文件备份 |

### 未修改的文件
`ui/`、`assets/`、`app.py`、`services/prediction_service.py`、`services/scheduling_service.py` — 均未修改。

## 二、功能变更详情

### Phase 1：数据库表结构
- `alerts` 表新增 `handled_at DATETIME`（记录预警处理时间）
- `operation_logs` 表新增 `log_type VARCHAR(32)`（分类：user/import/export/delete/alert/backup）
- 新增字段均为 NULLABLE，不影响已有数据

### Phase 2：导入导出
- 新增 `import_with_validation()` — 逐行校验 + 分级计数（inserted/updated/skipped）
- 新增 `validate_row()` — 单行校验，返回行号+字段+错误原因
- 新增 `export_table()` — 按类型/站点/时间范围导出 CSV 或 Excel
- 新增 `export_all_tables()` — 批量导出全部数据表为 ZIP
- `save_dataframe()` 保持向后兼容（仍返回 int）
- 导入校验新增：站点外键存在性检查、同文件内重复检测

### Phase 3：用户管理
- 新增 `list_users()` — 返回所有用户列表
- 新增 `set_user_enabled()` — 切换启用/禁用
- 新增 `delete_user()` — 软删除（enabled=False）
- 新增 `update_user_role()` — 修改角色
- 新增 `change_password()` — 旧密码验证 + 新密码强度校验
- 新增 `validate_password_strength()` — ≥8位 + 字母 + 数字
- `create_or_update_user()` 返回值改为 (bool, str)，创建时校验密码强度
- `add_log()` 支持 `log_type` 分类参数

### Phase 4：运维
- `update_alert_status()` 自动设置 `handled_at` + 写入操作日志
- 新增 `get_alert_by_id()` — 查询单条预警详情
- 新增 `create_json_backup_extended()` — 备份 + 返回校验和
- 新增 `verify_backup()` — JSON 完整性校验
- 新增 `restore_from_json()` — 安全模式（仅空表）/ 覆盖模式

## 三、测试

运行方式：
```bash
# 排除 smoke_test（使用独立 engine 避免冲突）
python -m pytest tests/test_auth_service.py tests/test_data_service.py tests/test_alert_service.py tests/test_backup_service.py -v
```

结果：38 个测试全部通过。

## 四、升级步骤

1. 备份现有数据库文件或运行 `create_json_backup_extended()`
2. 删除旧 SQLite 数据库（`database/platform_dev.db`）以便新字段生效
3. 重新运行 `initialize_database()` 创建完整 schema
4. 从备份恢复数据：`restore_from_json(backup_path, overwrite=True)`
