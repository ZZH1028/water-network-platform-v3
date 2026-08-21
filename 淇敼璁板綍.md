# 项目修改记录

> 水网工程水力调控智能平台 V1.0
> 建立日期：2026-08-01

---

## 项目修改规则

1. **不允许无记录修改代码**。任何代码变更必须先在本文件登记，再执行。
2. **修改前必须说明目的**。登记时写清楚为什么改、解决什么问题。
3. **修改后必须说明测试结果**。登记测试方法和通过情况。
4. **优先修改连接层**，不随意重构已有业务代码。`database/` 和 `services/` 核心逻辑保持稳定。
5. **前端接入时优先调用已有后台服务**，不在前端重复实现业务逻辑。
6. **每次修改追加记录**，按日期和阶段分组，不覆盖历史记录。

---

## 已完成修改（Phase 1-5：成员2 独立开发阶段）

> 阶段目标：数据库表结构优化、导入导出、用户管理、运维功能、测试。所有修改不涉及 app.py / ui / assets / prediction_service / scheduling_service。

---

### 文件：database/models.py

- **日期**：2026-08-01
- **阶段**：Phase 1 数据库表结构优化

**修改内容**：
1. `Alert` 类新增字段 `handled_at: Mapped[datetime | None]`（位于 `handled_by` 之后）
2. `OperationLog` 类新增字段 `log_type: Mapped[str | None]`（位于 `action` 之后）

**实现功能**：
- 预警记录可追踪处理时间
- 操作日志可按类型分类检索（user / import / export / delete / alert / backup）

**对应验收**：
- 表结构字段完整可用
- 新增字段不影响已有数据（均为 nullable）

**测试**：
- `python -c` 验证 `initialize_database()` 后 `alerts` 包含 `handled_at`、`operation_logs` 包含 `log_type`
- SQLAlchemy Inspector 确认列存在

---

### 文件：services/data_service.py

- **日期**：2026-08-01
- **阶段**：Phase 2 导入导出核心功能

**修改内容**：
1. 新增 `ImportResult` dataclass（total_rows / inserted / updated / skipped / errors）
2. 新增 `validate_row(dataset_type, row, row_index, valid_station_ids)` — 逐行校验
3. 重构 `validate_dataframe` — 返回值从 `list[str]` 改为 `tuple[list[str], list[dict]]`（⚠️ 接口变化）
4. 新增 `import_with_validation(dataset_type, df, username, uploaded_file)` — 完整导入流水线
5. 重构 `save_dataframe` — 委托 `import_with_validation`，返回 int 保持兼容
6. 新增 `export_table(dataset_type, format, station_id, date_from, date_to)` — 单表导出 CSV/XLSX
7. 新增 `export_all_tables(format)` — 批量导出 ZIP
8. 新增 `TIME_SERIES_TYPES`、`ENTITY_TYPES` 分类常量
9. 新增辅助函数 `_load_valid_station_ids()`、`_build_export_query()`、`_query_to_dataframe()`

**实现功能**：
- 导入时逐行校验：必填字段、外键存在性、日期格式、数值范围、经纬度范围
- 导入结果分级计数：inserted（新增）/ updated（覆盖）/ skipped（跳过重复）
- 错误报告含行号 + 字段名 + 原因
- CSV / Excel 导出，支持按站点和时间筛选
- 批量导出全部数据表为 ZIP

**对应验收**：
- 重复数据不会重复保存 ✅（unique constraint + skip 逻辑）
- 错误数据不会直接入库 ✅（逐行校验，坏行跳过）
- 导入失败时显示具体行号和错误原因 ✅

**测试**：
- `tests/test_data_service.py` 14 个用例全部通过
- 好数据 → 0 errors，正常入库
- 坏数据（不存在的站点、非法日期、非数字值、空值）→ 返回带行号的错误
- 重复导入 → skipped 计数正确
- CSV/XLSX/ZIP 导出 → 文件正常生成

---

### 文件：services/auth_service.py

- **日期**：2026-08-01
- **阶段**：Phase 3 用户管理与安全

**修改内容**：
1. 新增 `validate_password_strength(password)` → `(bool, str)` — 密码强度校验
2. 新增 `list_users()` → `list[dict]` — 用户列表
3. 新增 `set_user_enabled(username, enabled)` → `bool` — 启用/禁用
4. 新增 `delete_user(username)` → `bool` — 软删除
5. 新增 `update_user_role(username, role)` → `bool` — 角色修改
6. 新增 `change_password(username, old, new)` → `(bool, str)` — 密码修改
7. 修改 `create_or_update_user` — 返回值从 `None` 改为 `(bool, str)`，增加密码校验（⚠️ 接口变化）
8. 保留所有原有函数不变：`hash_password`、`verify_password`、`authenticate`

**实现功能**：
- 密码策略：≥8 位，含字母 + 数字
- 用户生命周期：创建、列表、禁用/启用、软删除、角色修改、密码修改
- 向后兼容：现有调用不受影响（app.py 未使用 create_or_update_user 返回值）

**对应验收**：
- 弱密码被拒绝 ✅
- 禁用用户无法登录 ✅
- 密码修改后旧密码失效 ✅

**测试**：
- `tests/test_auth_service.py` 13 个用例全部通过
- 覆盖：密码强度（4）、认证（3）、用户管理（5）、密码修改（3）

---

### 文件：services/log_service.py

- **日期**：2026-08-01
- **阶段**：Phase 3 操作日志完善

**修改内容**：
1. `add_log` 新增可选参数 `log_type: str = ""`
2. `query_logs` 新增可选参数 `log_type: str = ""`，支持按类型过滤
3. `query_logs` 返回 DataFrame 增加"类型"列

**实现功能**：
- 操作日志可分类标记（user / import / export / delete / alert / backup）
- 日志查询可按类型筛选

**对应验收**：
- 登录、导入、删除、预警处理等操作被记录 ✅

**测试**：
- `test_auth_service.py` 中隐式验证（通过 add_log 调用）
- 单独验证：带 log_type 的日志可写入、可按类型过滤

---

### 文件：services/alert_service.py

- **日期**：2026-08-01
- **阶段**：Phase 4 预警确认完善

**修改内容**：
1. `update_alert_status` — 增加设置 `handled_at = datetime.now()`，内部调用 `add_log(log_type="alert")`
2. `update_alert_status` 返回值从 `None` 改为 `bool`（⚠️ 接口变化）
3. 新增 `get_alert_by_id(alert_id)` → `dict | None`
4. 新增导入 `from services.log_service import add_log`

**实现功能**：
- 预警确认/解除时自动记录处理人和处理时间
- 操作自动写入日志
- 可查询单条预警完整信息

**对应验收**：
- 预警确认后 handled_by 和 handled_at 有值 ✅

**测试**：
- `tests/test_alert_service.py` 3 个用例全部通过
- 确认预警 → handled_by = "admin", handled_at 非 null
- 不存在的预警 → 返回 None

---

### 文件：services/backup_service.py（新增）

- **日期**：2026-08-01
- **阶段**：Phase 4 数据库备份恢复

**修改内容**：
1. 新文件，包含 3 个公开函数：
   - `create_json_backup_extended()` — 备份 + 返回元数据（路径/大小/MD5）
   - `verify_backup(backup_path)` — JSON 完整性校验（文件存在、JSON 可解析、表结构完整）
   - `restore_from_json(backup_path, overwrite=False)` — 安全模式（仅空表）/ 覆盖模式

**实现功能**：
- 全量 JSON 备份，含校验和
- 备份文件完整性验证
- 恢复支持安全（不覆盖）和覆盖两种模式

**对应验收**：
- 备份可验证完整性 ✅
- 恢复功能双模式可用 ✅

**测试**：
- `tests/test_backup_service.py` 5 个用例全部通过
- 备份生成 → 338KB, MD5 可验证
- 验证通过 → valid=True, 表结构完整
- 安全恢复 → 非空表跳过
- 覆盖恢复 → 数据完整写入

---

### 文件：tests/test_auth_service.py（新增）

- 13 个用例，覆盖密码校验、认证、用户管理、密码修改

### 文件：tests/test_data_service.py（新增）

- 14 个用例，覆盖逐行校验、导入、防重复、导出

### 文件：tests/test_alert_service.py（新增）

- 3 个用例，覆盖预警更新、查询

### 文件：tests/test_backup_service.py（新增）

- 5 个用例，覆盖备份、验证、恢复

---

### 文件：数据表说明.md（新增）

- 交付文档，13 张表字段说明 + ER 关系

### 文件：修改说明.md（新增）

- 交付文档，变更清单 + 升级步骤

### 文件：PROJECT_PLAN.md（新增）

- 项目执行计划，架构决策 + 进度追踪

---

## 待处理修改

### 待处理：app.py 整合适配

- **发现日期**：2026-08-01
- **问题**：
  1. `validate_dataframe` 返回值类型变化 → app.py 第 133-134 行遍历逻辑失效
  2. `update_alert_status` 内部已写日志 → app.py 再写一次造成重复
- **状态**：待修复（见整合阶段记录）
- **影响**：导入页面错误提示不显示；预警处理产生双份日志

---

## 后续修改记录模板

后续每次修改按以下格式追加：

```
---

## 日期：YYYY-MM-DD

## 修改阶段：
（前后端整合 / 功能迭代 / Bug修复 / 测试补充）

## 修改文件：
（文件路径）

## 修改内容：
（具体改动描述）

## 修改原因：
（为什么要改）

## 解决的问题：
（修复了什么 bug / 实现了什么功能）

## 影响范围：
（哪些模块受影响）

## 是否影响数据库：
（是/否，如是请说明具体表/字段）

## 是否影响接口：
（是/否，如果改变函数签名或返回值请说明）

## 测试方法：
（如何验证修改正确）

## 测试结果：
（通过/失败/待验证）
```

---

## 日期：2026-08-01

## 修改阶段：前后端整合阶段一（修复接口兼容性）

## 修改文件：app.py

## 修改内容：
1. 第 133 行：`validate_dataframe` 返回值从 `errors` 解包为 `summary, row_errors`（适配 services/data_service.py 接口变化）
2. 第 134-136 行：错误显示改为 `if summary or row_errors:` 统一判断，summary 显示笼统错误，row_errors 逐行显示"第X行 字段: 原因"
3. 第 205 行：移除预警处理处的 `add_log(username(),'处理预警',...)` 调用（因 `update_alert_status` 内部已自动记录日志）

## 修改原因：
- `validate_dataframe` 在 Phase 2 重构后返回值从 `list[str]` 变为 `(list[str], list[dict])`，app.py 原有遍历逻辑会报错
- `update_alert_status` 在 Phase 4 增加了内部 `add_log` 调用，app.py 再调用一次造成重复日志

## 解决的问题：
- 导入页错误提示恢复正常显示
- 消除预警处理重复日志

## 影响范围：仅 app.py，不影响 database/、services/、ui/、assets/

## 是否影响数据库：否

## 是否影响接口：否（仅修改调用方式，不改变函数签名）

## 测试方法：
- `python -c "import ast; ast.parse(...)"` 语法检查通过
- 人工审查代码逻辑：if/elif 结构正确，validate_dataframe 解包正确，add_log 重复已移除

## 测试结果：通过

---

## 日期：2026-08-01

## 修改阶段：前后端整合阶段二（增强导入页）

## 修改文件：app.py

## 修改内容：
1. 第 23 行：data_service 导入增加 `import_with_validation`
2. 第 138 行：导入确认按钮从 `save_dataframe` 切换为 `import_with_validation`，日志详情从简单行数改为"新增X/更新Y/跳过Z"，`add_log` 增加 `log_type='import'` 分类

## 修改原因：
`import_with_validation` 是 Phase 2 新增的主力导入函数，返回 `ImportResult`（含 inserted/updated/skipped 计数），前端应展示完整导入结果而非仅总行数。

## 解决的问题：
- 前端导入结果展示从模糊的"N条"变为"新增X条，更新Y条，跳过Z条"
- 导入日志增加 `log_type='import'` 分类标记

## 影响范围：仅 app.py 导入确认按钮逻辑，不影响 database/、services/、ui/

## 是否影响数据库：否

## 是否影响接口：否

## 测试方法：
- `python -c "import ast; ast.parse(...)"` 语法检查通过
- `save_dataframe` 在 app.py 中仅剩 import 声明，无其余调用

## 测试结果：通过

---

## 日期：2026-08-01

## 修改阶段：前后端整合阶段三（增强用户管理）

## 修改文件：app.py

## 修改内容：
1. 第 20 行：auth_service 导入增加 `set_user_enabled, update_user_role, change_password, list_users`
2. 第 226-232 行：新增"修改当前用户密码"折叠表单（调用 `change_password`）
3. 第 233-234 行：用户列表从 SQLAlchemy 直查改为调用 `list_users()`
4. 第 235-248 行：新增用户管理控件 — 选择用户后的禁用/启用按钮和角色下拉修改
5. 第 222-225 行：创建用户反馈改为根据 `create_or_update_user` 返回值显示成功/错误

## 修改原因：
Phase 3 新增的用户管理后端函数（set_user_enabled、update_user_role、change_password、list_users）之前未接入前端 UI。

## 解决的问题：
- 管理员可在前端禁用/启用用户、修改用户角色
- 所有用户可自行修改密码
- 用户列表改用 `list_users()` 统一接口

## 影响范围：
- app.py system() 函数：用户管理段从 8 行扩展到 33 行
- 不影响 database/、services/、ui/、assets/
- auth_service import 行变化，但未移除原有 import

## 是否影响数据库：否

## 是否影响接口：否（仅调用已有函数）

## 测试方法：
- `python -c "import ast; ast.parse(...)"` 语法检查通过
- 代码审查：控件结构完整（表单→密码修改→用户表→管理控件）
- 无用户可操作自己（selectbox 过滤 `username != username()`）

## 测试结果：通过

---

## 日期：2026-08-01

## 修改阶段：前后端整合阶段四（增强导出功能）

## 修改文件：app.py

## 修改内容：
1. 第 24 行：data_service 导入增加 `export_table, export_all_tables`
2. 第 140-150 行：数据库查询标签页增加导出格式选择（CSV/Excel）、站点筛选、日期范围、导出当前表按钮、批量导出按钮
3. 原简单 CSV 下载按钮（`st.download_button('导出CSV',q.to_csv(...))`）替换为调用 `export_table`/`export_all_tables`

## 修改原因：
Phase 2 新增的导出函数（export_table、export_all_tables）支持格式选择、站点和时间筛选，前端应接入这些能力。

## 解决的问题：
- 导出格式从仅 CSV 扩展为 CSV + Excel
- 支持按站点 ID 和时间范围筛选导出
- 新增批量导出全部数据表为 ZIP

## 影响范围：app.py data_page() 函数 t2 标签页（从 1 行扩展为 11 行）

## 是否影响数据库：否

## 是否影响接口：否

## 测试方法：
- `python -c "import ast; ast.parse(...)"` 语法检查通过
- 代码审查：with t2 块完整，控件布局 3 列正确

## 测试结果：通过

---

## 日期：2026-08-01

## 修改阶段：数据库结构同步修复

## 修改文件：database/init_db.py

## 修改内容：
1. 新增 `_migrate_schema()` 函数：用 SQLAlchemy Inspector 检查 alerts 和 operation_logs 表，按需执行 `ALTER TABLE ADD COLUMN` 追加缺失字段
2. `initialize_database()` 中 `create_all()` 之后调用 `_migrate_schema()`
3. 新增导入 `from sqlalchemy import inspect, text`

## 修改原因：
项目无 Alembic/migrations/init.sql。`Base.metadata.create_all()` 对已存在的表是 no-op，导致已有部署升级时 `handled_at` 和 `log_type` 字段缺失，引发 "column does not exist" 错误。

## 解决的问题：
- 已有数据库（含 Docker PostgreSQL volume）启动时自动补充缺失字段
- 新部署不受影响（`create_all` 已包含新字段，迁移步骤检测到已存在则跳过）
- 幂等安全（重复执行不报错）

## 影响范围：
- database/init_db.py：新增 `_migrate_schema()` 函数 + 1 行调用
- 不修改 models.py、services、app.py
- PostgreSQL 和 SQLite 均兼容（ALTER TABLE ADD COLUMN 语法一致）

## 是否影响数据库：是（DDL 操作，仅添加列，不修改已有数据）

## 是否影响接口：否

## 测试方法：
1. 创建不含新列的旧 schema → 运行 initialize_database() → 验证列已添加
2. 重复运行 initialize_database() → 无异常（幂等性）

## 测试结果：通过
