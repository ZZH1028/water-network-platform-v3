# 公网部署

完整平台需要 Python、数据库、WebSocket 和本地资料检索，不能直接运行在只提供静态托管的 GitHub Pages 上。推荐使用 GitHub 管理代码、Streamlit Community Cloud 运行平台；平台入口文件为 `streamlit_app.py`。

## 一键打开部署页面

[使用 GitHub 账号部署平台](https://share.streamlit.io/deploy?repository=ZZH1028%2Fwater-network-platform-v3&branch=main&mainModule=streamlit_app.py)

1. 使用有该仓库访问权限的 GitHub 账号登录 Streamlit Community Cloud，完成授权。
2. 确认 Repository 为 `ZZH1028/water-network-platform-v3`，Branch 为 `main`，Main file path 为 `streamlit_app.py`。
3. 在 Advanced settings 选择 Python **3.12**。如需管理后台，在 Secrets 中填写下列配置，再点击 Deploy：

```toml
[platform]
PUBLIC_ADMIN_USERNAME = "admin"
PUBLIC_ADMIN_PASSWORD = "在此填写你自己的至少12位含字母与数字的密码"
```

不要使用示例文字作为密码。未设置密码时，首页、三维场景、平台介绍和公开资料问答仍可用，管理入口关闭。首次设置后会创建管理员；后台自行修改密码后，普通重启不会覆盖新密码。迁移旧演示库时，原管理员的 `admin123` 可由此配置替换；公网入口拒绝默认演示密码。

4. 部署成功后，以服务实际显示的 `https://…streamlit.app` 地址为准。部署按钮是配置入口，不是已上线的网站地址。可以在 App settings 中设置一个尚未被占用的子域名。

仓库已提供依赖清单；首次启动自动下载固定版本 Cesium 引擎并校验 SHA-512，不需要手工上传静态引擎目录。引擎安装不关闭 TLS；下载异常时需排查托管服务网络后重新启动。

## 数据与模型

- 默认是带演示水情的展示环境，预测、调度不是经率定的水动力模型。
- 托管环境本地 SQLite、上传原件、知识库在重启/重新部署后可能丢失。不要把演示站作为唯一资料存储；长期运行应配置外部 PostgreSQL 并另行准备原件与知识库持久存储。
- 默认问答是有来源的本地资料检索。需要模型综合回答时，在 Secrets 添加 `WATER_AI_BASE_URL`、`WATER_AI_MODEL`、`WATER_AI_API_KEY`，不得把真实密钥提交到 GitHub。
- 卫星影像与地形是浏览器请求的外部服务；是否可用取决于访问地区与服务连通性。当前没有建筑级倾斜摄影数据。

## 本地核验同一入口

```bash
python -m streamlit run streamlit_app.py
```

本地验证不等于已完成公网部署。部署服务的登录授权和 Deploy 操作须由持有账号的人完成；生成实际网址后再验证页面、WebSocket、三维资源和登录行为。
