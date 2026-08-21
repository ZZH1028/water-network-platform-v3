# 正式部署清单

1. 修改 `.env` 中 PostgreSQL 密码和 SECRET_KEY；
2. 将 `DEMO_MODE`、`SEED_DEMO_DATA` 改为 false；
3. 覆盖 `assets/hhu_logo.png` 为获授权的官方校徽；
4. 部署到固定服务器，设置静态IP；
5. 使用 Nginx 和 HTTPS；
6. 设置每日 PostgreSQL 备份计划；
7. 修改全部默认密码；
8. 接入正式水动力模型和调度优化模型；
9. 完成至少两台设备并发测试和数据恢复演练；
10. 禁止平台直接下发真实闸泵控制指令，除非经过专门安全审查。
