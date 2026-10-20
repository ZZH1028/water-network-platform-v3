"""Three-dimensional analytical views with explicit, meaningful axes."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

COLORS = ['#35d6bd', '#68b9f8', '#efc679', '#a997f0', '#f18f9b', '#8bcf91']


def _layout(fig: go.Figure, title: str, x: str, y: str, z: str, height=440) -> go.Figure:
    axis = dict(backgroundcolor='#102332', gridcolor='rgba(131,166,187,.16)',
                color='#99b2c4', showbackground=True, zerolinecolor='#395363')
    fig.update_layout(title=dict(text=title, font=dict(size=16)), height=height,
                      paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#dcebf3'),
                      margin=dict(l=0, r=0, t=45, b=0), legend=dict(orientation='h', y=1.03),
                      scene=dict(xaxis=dict(title=x, **axis), yaxis=dict(title=y, **axis),
                                 zaxis=dict(title=z, **axis), camera=dict(eye=dict(x=1.6, y=-1.7, z=1.1))))
    return fig


def time_series_figure(frame: pd.DataFrame, time_column: str, value_column: str,
                       value_label: str, *, group_column='station_id', title='', height=440) -> go.Figure:
    fig = go.Figure()
    if frame.empty:
        return _layout(fig, title, '相对起点（h）', '站点', value_label, height)
    data = frame.copy()
    data['_time'] = pd.to_datetime(data[time_column], errors='coerce')
    data[value_column] = pd.to_numeric(data[value_column], errors='coerce')
    data = data.dropna(subset=['_time', value_column]).sort_values('_time')
    if data.empty:
        return _layout(fig, title, '相对起点（h）', '站点', value_label, height)
    start = data['_time'].min()
    groups = list(data.groupby(group_column, sort=False)) if group_column in data else [('观测序列', data)]
    labels = []
    for index, (name, group) in enumerate(groups):
        labels.append(str(name))
        fig.add_trace(go.Scatter3d(x=(group['_time']-start).dt.total_seconds()/3600,
                                  y=[index]*len(group), z=group[value_column],
                                  name=str(name), mode='lines+markers',
                                  line=dict(color=COLORS[index % len(COLORS)], width=5),
                                  marker=dict(size=2.5), customdata=group['_time'].dt.strftime('%Y-%m-%d %H:%M'),
                                  hovertemplate='%{customdata}<br>'+str(name)+'<br>'+value_label+'：%{z:.3f}<extra></extra>'))
    _layout(fig, title, f'自 {start:%m-%d %H:%M} 起（h）', '站点 / 序列', value_label, height)
    fig.update_layout(scene_yaxis=dict(tickvals=list(range(len(labels))), ticktext=labels))
    return fig


def prediction_figure(frame: pd.DataFrame) -> go.Figure:
    if 'predicted_flow' not in frame or frame['predicted_flow'].isna().all():
        return time_series_figure(frame, 'predict_time', 'predicted_level', '预测水位（m）',
                                  title='预测过程 · 三维分析')
    data = frame.copy().sort_values('predict_time')
    times = pd.to_datetime(data['predict_time'])
    hours = (times-times.min()).dt.total_seconds()/3600
    fig = go.Figure(go.Scatter3d(x=hours, y=data['predicted_flow'], z=data['predicted_level'],
                                mode='lines+markers', name='预测轨迹',
                                line=dict(color='#35d6bd', width=6),
                                marker=dict(size=4, color=data['predicted_level'], colorscale='Teal'),
                                customdata=times.dt.strftime('%m-%d %H:%M'),
                                hovertemplate='%{customdata}<br>流量 %{y:.2f} m³/s<br>水位 %{z:.3f} m<extra></extra>'))
    return _layout(fig, '水位 × 流量 × 预测时效', '预测时效（h）', '预测流量（m³/s）', '预测水位（m）', 480)


def comparison_figure(plans: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for index, row in enumerate(plans.itertuples(index=False)):
        fig.add_trace(go.Scatter3d(x=[row.max_level], y=[row.energy_index], z=[row.drainage_volume],
                                  mode='markers+text', text=[f'方案 {row.plan_code}'],
                                  name=f'方案 {row.plan_code}', textposition='top center',
                                  marker=dict(size=13, color=COLORS[index % len(COLORS)], opacity=.9),
                                  customdata=[[row.score]],
                                  hovertemplate='最高水位 %{x:.2f} m<br>能耗指数 %{y:.1f}<br>排水指标 %{z:.1f}<br>综合评分 %{customdata[0]:.1f}<extra></extra>'))
    return _layout(fig, '候选方案 · 三目标决策空间', '最高水位（m）↓', '能耗指数 ↓', '模型排水指标 ↑', 500)


def section_profile_figure(profile: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for index, (column, label) in enumerate([('min_elev', '最低高程'), ('mean_elev', '平均高程'), ('max_elev', '最高高程')]):
        fig.add_trace(go.Scatter3d(x=list(range(1, len(profile)+1)), y=[index]*len(profile), z=profile[column],
                                  name=label, mode='lines+markers', line=dict(color=COLORS[index], width=5),
                                  marker=dict(size=3), customdata=profile['section_id'].astype(str),
                                  hovertemplate='断面 %{customdata}<br>吴淞高程 %{z:.2f} m<extra></extra>'))
    _layout(fig, '河道断面高程纵览', '断面序列', '统计项', '吴淞高程（m）')
    fig.update_layout(scene_yaxis=dict(tickvals=[0,1,2], ticktext=['最低','平均','最高']))
    return fig
