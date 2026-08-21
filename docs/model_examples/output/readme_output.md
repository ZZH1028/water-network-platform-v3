# 模型输出字段说明文档
## 一、水位预测输出文件（demo_pred_output.json / real_pred_output.json）
### 输出固定字段（前端/报表直接读取，结构永久不变）
1. task_code：预测任务唯一编号，PR前缀，用于全链路溯源
2. station_id / station_name / lat / lng：匹配GIS雷达站点WGS84经纬度，支持地图展示
3. times：逐小时预测时间序列数组
4. values：对应时刻预测水位（m，吴淞高程）
5. max_level：预测周期内最高水位
6. risk_level：洪水风险等级（红色/橙色/黄色/蓝色/正常）
7. over_hours：水位超过4.5m警戒水位总时长

### 文件区分
demo_pred_output.json：本次交付演示模拟输出；
real_pred_output.json：后续迭代接入新吴实测水动力模型输出，字段完全一致，仅数值替换。

## 二、调度方案输出文件（demo_schedule_result.json / real_schedule_result.json）
数组格式，一次性返回A/B/C三套差异化调度方案，覆盖防洪、能耗双目标
单套方案固定字段：
1. batch_code：调度批次编号SC开头
2. prediction_task_code：绑定对应预测任务编号，实现预测-调度链路关联
3. station_id、station_name、station_lat、station_lng：绑定监测河道GIS点位
4. plan_code/plan_name：方案标识（A安全优先/B综合平衡/C节能优先）
5. max_level：执行调度后预估最高水位（防洪核心指标）
6. drainage_volume：总排水量
7. energy_index：能耗指数，数值越低越省电
8. gate_actions：投入运行闸门数量
9. pump_hours：泵站总运行时长
10. gate_recommendation：闸门实操调度建议（给调度人员）
11. pump_recommendation：泵站运行实操建议
12. score：方案综合评分，分数越高综合效果越好
13. selected：是否人工选定最优方案
14. review_status：审核状态（待审核/已审核）
15. reviewed_by：审核操作人

## 三、输出格式规范
1. 统一标准UTF-8 JSON格式，前端页面、数据分析脚本可直接解析
2. 可转为pandas DataFrame表格用于报表导出，满足接口输出要求
3. 完全适配PDF任务要求：携带GIS坐标、任务编号、运行状态、多调度方案、闸泵建议、评价指标
## 四、交付区分说明
demo_前缀文件：本次验收交付使用，演示模拟数据；
real_前缀文件：后续迭代更新实测数据后替换使用，接口、字段无需改动。