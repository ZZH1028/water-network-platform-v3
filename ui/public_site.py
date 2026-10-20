from __future__ import annotations

import base64
import html
from functools import lru_cache

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.config import APP_NAME, APP_VERSION, BASE_DIR, DEMO_MODE
from services.data_service import get_dashboard_statistics, get_latest_data_time, get_latest_station_levels
from services.gis_service import get_gis_summary, load_river_sections
from ui.scene3d import render_scene3d
from ui.charts3d import time_series_figure, section_profile_figure
from ui.theme import page_header

def inject_public_site_theme() -> None:
    st.markdown("""
    <style>
    .public-topbar{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:14px 0 22px;margin-bottom:4px;border-bottom:1px solid #233847}
    .public-brand{display:flex;align-items:center;gap:13px}.public-brand img{width:44px;height:44px;object-fit:contain;background:#fff;border-radius:50%;padding:3px}
    .public-brand-title{font-size:19px;font-weight:750;letter-spacing:.5px;color:#edf5fa}.public-brand-sub{font-size:10px;color:#8babbc;letter-spacing:2px;margin-top:4px}
    .public-version{border:1px solid #355650;border-radius:20px;padding:7px 12px;color:#8bdbc4;font-size:11px;white-space:nowrap}
    .public-footer{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;padding-top:20px;margin-top:32px;border-top:1px solid #233847;color:#7d99ac;font-size:11px}
    [data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"]{gap:7px;padding:7px;background:#0c1b2b;border:1px solid #263b4e;border-radius:10px}
    [data-testid="stMain"] label[data-testid="stRadioOption"]{padding:8px 14px;border-radius:7px;border:1px solid transparent;margin:0}
    [data-testid="stMain"] label[data-testid="stRadioOption"][data-selected="true"]{background:#163c40;border-color:#38776b}
    [data-testid="stMain"] label[data-testid="stRadioOption"][data-selected="true"] p{color:#84e4cf!important}
    [data-testid="stMain"] label[data-testid="stRadioOption"]>div>div:first-child{display:none}
    [data-testid="stMain"] label[data-testid="stRadioOption"][data-focus-visible="true"]{outline:2px solid #d8bb80;outline-offset:2px}
    @media(max-width:680px){.public-version{display:none}.public-brand-title{font-size:15px}.public-brand-sub{font-size:8px}}
    </style>
    """, unsafe_allow_html=True)

def public_topbar() -> None:
    logo = base64.b64encode((BASE_DIR/'assets/hhu_logo.png').read_bytes()).decode('ascii')
    st.markdown(f'<div class="public-topbar"><div class="public-brand"><img src="data:image/png;base64,{logo}" alt="平台标识"><div><div class="public-brand-title">{html.escape(APP_NAME)}</div><div class="public-brand-sub">TIDAL RIVER NETWORK · SPATIAL INTELLIGENCE</div></div></div><div class="public-version">实景三维 · 水知助手</div></div>', unsafe_allow_html=True)

def render_overview() -> None:
    page_header('河网数据概览', '地理参考资料与业务水情分开呈现，让每一项指标都有明确来源。')
    summary, stats = get_gis_summary(), get_dashboard_statistics()
    columns = st.columns(4)
    for column, (label, value) in zip(columns, [('参考监测站',summary['station_count']),('参考闸泵',summary['facility_count']),('河道断面',summary['section_count']),('业务监测站',stats['station_count'])]):
        column.metric(label,value)
    st.caption(f"业务数据更新：{get_latest_data_time()} · {'当前为演示水情' if DEMO_MODE else '当前数据库水情'}")
    render_scene3d(get_latest_station_levels(), height=540, key='overview_scene')
    st.subheader('监测站最新水情')
    latest = get_latest_station_levels()
    st.dataframe(latest, width='stretch', hide_index=True)
    st.download_button('下载当前监测快照', latest.to_csv(index=False).encode('utf-8-sig'), 'station_snapshot.csv', 'text/csv')

def render_gis(build_map=None) -> None:
    page_header('实景三维 · 河网一张图', '以卫星影像和地形承载站点、河道与闸泵，面向平原感潮河网开展空间研判。')
    render_scene3d(get_latest_station_levels(), height=720, key='public_scene')
    with st.expander('数据来源与实景精度'):
        st.markdown('卫星影像采用 Esri World Imagery；地形采用公开的 Esri 全球高程服务。图中站点、闸泵与河网来自项目已有参考资料，水情来自业务数据库。')
        st.markdown('卫星影像叠加地形可以浏览真实地表；建筑级倾斜摄影需接入相应的实景三维数据。全球地形精度不能替代河床测量、堤顶高程或工程测绘。')

@lru_cache(maxsize=1)
def _river_df() -> pd.DataFrame:
    return pd.DataFrame(load_river_sections())

def _twin_3d_figure(df: pd.DataFrame, title: str, max_points=6500) -> go.Figure:
    view = df.iloc[::max(1, (len(df)+max_points-1)//max_points)].copy()
    fig = go.Figure(go.Scatter3d(
        x=view.plane_x, y=view.plane_y, z=view.wusong_elev, mode='markers',
        marker=dict(size=2.5, color=view.wusong_elev, colorscale='Teal', opacity=.85,
                    colorbar=dict(title='吴淞高程 m')),
        customdata=view[['reach_name','section_id']].values,
        hovertemplate='河道 %{customdata[0]} · 断面 %{customdata[1]}<br>X %{x:.2f} · Y %{y:.2f}<br>吴淞高程 %{z:.2f} m<extra></extra>'))
    axis = dict(backgroundcolor='#102332', gridcolor='rgba(130,168,188,.15)', color='#93b2c3', showbackground=True)
    fig.update_layout(title=title, height=620, paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#dcebf3'),
        margin=dict(l=0,r=0,t=45,b=0),
        scene=dict(xaxis=dict(title='本地平面 X（m）',**axis), yaxis=dict(title='本地平面 Y（m）',**axis),
                   zaxis=dict(title='吴淞高程（m）',**axis), aspectmode='manual', aspectratio=dict(x=1.4,y=1,z=.45)))
    return fig

def render_digital_twin() -> None:
    page_header('数字孪生 · 空间与河床', '浏览真实地表，进一步查看原始测量断面的三维形态与高程。')
    surface, sections = st.tabs(['实景地表', '实测河床断面'])
    with surface:
        render_scene3d(get_latest_station_levels(), height=650, key='twin_scene')
    with sections:
        df = _river_df()
        if df.empty:
            st.info('尚未导入河道断面。')
            return
        st.caption('测量采用本地平面坐标和吴淞高程；尚无可靠坐标转换参数，因此单独展示，不强行套合卫星底图。显示适当放大竖向尺度，刻度仍保留实际高程。')
        left, right = st.columns([1,2])
        with left:
            mode = st.selectbox('三维范围',['全河网概览','按河道查看','按断面查看'])
        with right:
            rivers = sorted(df.reach_name.dropna().unique())
            selected = st.selectbox('河道', rivers, disabled=mode=='全河网概览')
        view = df if mode=='全河网概览' else df[df.reach_name==selected]
        if mode=='按断面查看':
            section = st.selectbox('断面',sorted(view.section_id.astype(str).unique()))
            view = view[view.section_id.astype(str)==section]
        a,b,c = st.columns(3)
        a.metric('当前测点',f'{len(view):,}')
        b.metric('最低高程',f'{view.wusong_elev.min():.2f} m')
        c.metric('最高高程',f'{view.wusong_elev.max():.2f} m')
        st.plotly_chart(_twin_3d_figure(view,'河床实测点云'), width='stretch', config={'displaylogo':False,'scrollZoom':True})
        if mode!='全河网概览':
            profile = view.groupby('section_id',as_index=False).agg(mean_elev=('wusong_elev','mean'),min_elev=('wusong_elev','min'),max_elev=('wusong_elev','max'))
            st.plotly_chart(section_profile_figure(profile),width='stretch')
        with st.expander('查看测量数据'):
            st.dataframe(view, width='stretch', hide_index=True)
            st.download_button('下载当前断面资料',view.to_csv(index=False).encode('utf-8-sig'),'river_sections.csv','text/csv')

def render_capabilities() -> None:
    page_header('从空间感知到专业研判', '围绕感潮河网的监测、预报、调度与知识积累，形成连续的工作流程。')
    columns = st.columns(3)
    cards = [
        ('01 · 实景三维','卫星影像与真实地形承载监测站、闸泵和河网；支持接入建筑级实景三维资料。'),
        ('02 · 水知助手','导入专业资料，按问题检索原文并引用来源；也可查询平台操作步骤。支持后续连接兼容的大模型。'),
        ('03 · 预测与调度','现有演示模型生成水位、流量与风险结果，形成多目标候选方案，保留人工审核。')]
    for col,(title,text) in zip(columns,cards):
        with col:
            with st.container(border=True):
                st.subheader(title)
                st.write(text)
    st.subheader('建议工作流程')
    st.markdown('**导入与校验 → 三维定位 → 水情研判 → 模型预测 → 方案比选 → 人工审核**')
    st.info('正式工程应用需要接入并验证专业模型、实时数据及设施运行约束。当前预测与优化仍使用仓库已有演示模型。')

def render_architecture() -> None:
    page_header('数据与能力架构', '统一空间场景、业务数据和专业资料，支持本地开发与多人协作。')
    for title,text in [
        ('实景空间','三维地球、卫星影像、全球地形、河网与站点；可选接入实景 3D Tiles。'),
        ('业务工作台','监测、预测、调度、预警、数据质量、导入导出与权限审计。'),
        ('知识与助手','专业资料解析、分块索引、来源引用、本地检索及可选模型问答。'),
        ('存储与服务','业务支持 SQLite / PostgreSQL；知识资料独立索引；支持 Docker 部署。')]:
        with st.container(border=True):
            st.subheader(title)
            st.write(text)

def render_about() -> None:
    page_header('关于平台', '面向平原感潮河网的三维空间研判与水专业知识工作台。')
    st.write('平台保留既有水情、预测、调度和管理能力，以三维实景空间与可溯源的专业资料检索连接这些工作环节。')
    st.subheader('资料覆盖与模型边界')
    st.write('初始知识库是带公开来源的专题导读与本平台操作手册，不代表已经收录全球水专业文献。专业资料需持续按来源、版本、适用地区和高程基准维护。')
    st.write('未配置大模型时，助手提供实际命中的资料摘录与操作指引；接入模型后，可对匹配资料进行归纳问答。工程计算、运行指令和调度审核仍由专业人员负责。')

def public_footer() -> None:
    st.markdown(f'<div class="public-footer"><span>{html.escape(APP_NAME)} · {html.escape(APP_VERSION)}</span><span>实景空间 / 专业知识 / 协同研判</span></div>',unsafe_allow_html=True)
