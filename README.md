# 水网工程水力调控智能平台 V5.0

面向平原感潮河网的实景三维、专业资料检索与业务研判工作台。

[![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=ZZH1028%2Fwater-network-platform-v3&branch=main&mainModule=streamlit_app.py)

**公网访问部署**：点击上方按钮，以 GitHub 账号授权 Streamlit Community Cloud，选择 `streamlit_app.py`、Python 3.12 后部署。后台管理员在服务的 Secrets 中配置；默认不开放管理账号。实际公网地址由托管服务部署完成后生成，GitHub Pages 不运行本平台的 Python 后台。详见[公网部署说明](docs/PUBLIC_DEPLOYMENT.md)。

## 本次升级

- **三维空间统一入口**：首页、实景三维、数字孪生、运行监测和后台工作台使用 Cesium 三维地球；取消二维地图。公开卫星影像与地形服务分别显示加载状态，支持按站点定位、环绕漫游、工程图层和名称控制。
- **真实资料分层展示**：站点、参考闸泵和河道中心线采用项目地理资料；业务水情与闸泵工况单独标识。河床点云保留原始本地平面坐标和吴淞高程，不冒充已经完成空间配准的建筑模型。
- **水知 AI 助手**：支持专业问题与平台操作帮助；检索片段标明标题、章节或 PDF 页码，支持会话导出。未配置模型时明确使用本地资料检索；后续可连接 OpenAI 兼容接口。
- **专业知识库**：管理员、科研人员可导入 TXT / Markdown / CSV / JSON / PDF / DOCX，支持原件保存、分块索引、中文/英文全文检索、去重及删除。访客只检索内置资料，上传资料供登录用户检索。
- **界面统一**：海军蓝、青绿与浅金配色，围绕三维场景组织水情、预警、工作入口和来源说明；监测、预测、断面纵览与方案比较使用三维分析视图，并保留原始数值表格和导出。

## 本地运行

建议 Python 3.12。Linux / macOS：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt --index-url https://pypi.org/simple
.venv/bin/python scripts/setup_scene_assets.py
.venv/bin/python -m streamlit run app.py
```

Windows 可运行 `01_install_local_env.bat`，再运行 `02_run_local_sqlite.bat`。浏览器访问本地 Streamlit 服务的 8501 端口。

Cesium 引擎资源安装在 `static/cesium/`，来自固定版本的 npm 官方包，并核验 SHA-512；不依赖浏览器访问公共 JavaScript CDN。生成资源被 Git 忽略，克隆后须执行安装步骤，Docker 构建也会执行它。项目已启用 Streamlit 静态资源服务。

默认使用 SQLite 开发数据库和演示水情，首次运行自动初始化。仓库演示管理员为 `admin / admin123`。正式部署前应修改默认密码，并区分演示模型与正式工程模型。

可选本地配置：复制 `.env.development.example` 为 `.env` 后按需填写；既有进程环境变量优先，不会被文件覆盖。不要把真实密钥提交到仓库。`.env.example` 和 `.env.public.example` 是原有 PostgreSQL 部署示例，不能直接当作 SQLite 开发配置。

## 公开实景资源与建筑级实景

默认资源：

| 内容 | 服务 |
| --- | --- |
| 卫星 / 航摄影像 | Esri World Imagery，`server.arcgisonline.com` |
| 全球地形 | Esri WorldElevation3D，`elevation3d.arcgis.com` |
| 建筑级倾斜摄影 | 可选 `WATER_3D_TILESET_URL`，公开 HTTPS 3D Tiles 地址 |

浏览器需要 WebGL 与地图服务网络连接。外部服务失败时仍显示本地工程图层，并明确标注影像未加载、地形椭球回退；这种状态不代表实景加载成功。公开服务的覆盖、更新频率和精度由提供方决定。影像不是实时现场，全球地形不能替代工程测量。

建筑级实景需要合法可访问、已配准且允许跨域访问的 3D Tiles 数据；当前仓库没有这套倾斜摄影数据。该地址会发送到浏览器，不能填写后台模型密钥或其他私密服务凭据。

## AI 与知识资料

初始提供 6 份项目自编专业导读和操作手册，涉及潮汐顶托、边界条件、监测质量、洪潮组合、闸泵调度与平台流程。权威机构链接是阅读入口，不表示其全部原文已被导入。初始资料不代表全球水利文献全集。

导入是提取文字、分块并建立检索索引，不是训练或微调模型。扫描 PDF 需先 OCR；单文件上限 20 MB，默认最多 1000 份资料。资料覆盖范围取决于实际导入内容，建议记录发布机构、版本、适用区域、高程基准和来源。

也可从服务器批量导入已整理、有权共享的资料目录：

```bash
.venv/bin/python scripts/import_knowledge.py /path/to/professional_documents --recursive
```

重复文件按内容摘要识别；失败文件会单独报告，不会中断其他文件的导入。不同来源、版本或流域的资料应明确填写标题与出处，避免混用。

需要模型综合问答时，在安全的环境配置中设置：

```dotenv
WATER_AI_BASE_URL=https://你的兼容模型服务/v1
WATER_AI_MODEL=模型名称
WATER_AI_API_KEY=通过环境设置安全录入
```

接口须为公开 HTTPS Chat Completions 服务。配置后，用户仍需在会话中明确允许向模型发送本次问题、匹配片段及最近对话。未配置、无证据、连接失败或返回引用无效时，保留本地检索结果和明确状态。当前未连接真实模型，不能将接口协议测试视作模型连通验证。

知识库存于 `storage/knowledge/`，可通过 `KNOWLEDGE_DB_PATH` 改变索引数据库位置。业务 JSON 备份不包含知识库；迁移时应在停止资料写入后，另行备份整个知识库目录及原件。Docker 的现有 `./storage:/app/storage` 挂载会保留默认知识库。

## 测试

现有业务测试会在导入时设置数据库，因此按文件使用独立进程：

```bash
for test_file in tests/test_*.py tests/smoke_test.py; do
  .venv/bin/python -m pytest -q "$test_file" || exit 1
done
```

新增测试覆盖资料解析、检索与引用、访客权限、模型调用与故障降级、三维坐标与数据合并、分析图数值。测试数据库和运行输出被 Git 忽略；不要删除既有用户数据。

## 正式应用边界

预测与调度继续使用本仓库原有演示计算核心；本次没有将其替换为经率定验证的专业水动力模型。正式应用仍需专业模型、实时数据、工程坐标转换参数与审批规程。PostgreSQL 多用户部署及 Cloudflare 隧道沿用仓库现有脚本，属于独立部署选项。
