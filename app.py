from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from core.config import APP_NAME, APP_VERSION, DEMO_MODE, SEED_DEMO_DATA, BASE_DIR, BACKUP_DIR, PUBLIC_DEPLOYMENT
from database.init_db import initialize_database
from database.engine import session_scope
from database.models import ModelRegistry, UploadedFile
from sqlalchemy import select
from services.auth_service import authenticate, create_or_update_user, set_user_enabled, update_user_role, change_password, list_users
from services.log_service import add_log, query_logs
from services.data_service import (
    DATASET_CONFIG, read_uploaded_file, validate_dataframe, save_dataframe, import_with_validation, query_table,
    export_table, export_all_tables, get_station_options, get_latest_station_levels, get_water_level_series, get_flow_series, get_rainfall_series, get_tide_series, get_dashboard_statistics, get_latest_data_time, simulate_realtime_update, create_json_backup,
)
from services.alert_service import refresh_threshold_alerts, query_alerts, update_alert_status
from services.prediction_service import run_demo_prediction, get_latest_prediction, list_prediction_tasks
from services.scheduling_service import generate_demo_plans, get_latest_plans, select_plan
from services.template_service import TEMPLATES, dataframe_to_excel_bytes
from services.gis_service import load_gis_stations
from services.backup_service import create_json_backup_extended, verify_backup, restore_from_json
from ui.theme import inject_research_theme, login_brand_panel, sidebar_brand, page_header, research_banner, metric_card, section_label, research_footer, style_plotly_figure
from ui.public_site import (
    inject_public_site_theme, public_topbar, render_overview, render_gis,
    render_digital_twin, render_capabilities, render_architecture, render_about, public_footer,
)
from ui.command_center_home import render_command_center_home
from ui.scene3d import render_scene3d
from ui.assistant import render_assistant
from ui.charts3d import time_series_figure, prediction_figure, comparison_figure

LOGO = Image.open(BASE_DIR/'assets'/'hhu_logo.png')
st.set_page_config(page_title=APP_NAME,page_icon=LOGO,layout='wide',initial_sidebar_state='auto')
initialize_database(seed_demo=SEED_DEMO_DATA)
inject_research_theme()
inject_public_site_theme()

ROLE_PERMISSIONS={
 '管理员':{'simulate','import','predict','schedule','alert','backup','users'},
 '科研人员':{'import','predict','schedule'},
 '调度人员':{'predict','schedule','alert'},
 '查看用户':set(),
}
ROLE_PAGES={
 '管理员':['平台首页','水知AI助手','三维河网','数据中心','运行监测','水动力预测','智能调度','方案比较','预警中心','模型管理','系统管理'],
 '科研人员':['平台首页','水知AI助手','三维河网','数据中心','运行监测','水动力预测','智能调度','方案比较','模型管理'],
 '调度人员':['平台首页','水知AI助手','三维河网','运行监测','水动力预测','智能调度','方案比较','预警中心'],
 '查看用户':['平台首页','水知AI助手','三维河网','运行监测','方案比较','预警中心'],
}

def user(): return st.session_state.get('user',{})
def username(): return user().get('username','anonymous')
def role(): return user().get('role','查看用户')
def allowed(p): return p in ROLE_PERMISSIONS.get(role(),set())

def login():
    if user(): return True
    a,b,c,d=st.columns([.35,1.15,.9,.35],gap='large')
    with b: login_brand_panel()
    with c:
        users = list_users()
        st.markdown('### 登录正式平台'); st.caption(APP_VERSION)
        if not users:
            if PUBLIC_DEPLOYMENT:
                st.info('管理入口暂未开放。你仍可使用公开三维场景与水知助手。')
                return False
            st.warning('数据库中没有用户，请先创建管理员账号。')
            with st.form('create_admin'):
                au=st.text_input('管理员账号')
                ap=st.text_input('管理员密码',type='password')
                if st.form_submit_button('创建并登录',type='primary',width='stretch'):
                    ok, msg = create_or_update_user(au, ap, '管理员')
                    if ok:
                        result=authenticate(au, ap)
                        if result:
                            st.session_state['user']=result
                            target = st.session_state.pop('pending_backend_page', None)
                            if target in ROLE_PAGES.get(result.get('role','查看用户'), []): st.session_state['backend_nav'] = target
                            add_log(result['username'],'首次创建并登录平台')
                            st.rerun()
                        else: st.error('创建后登录失败，请联系管理员。')
                    else: st.error(msg)
        else:
            with st.form('login'):
                u=st.text_input('账号'); p=st.text_input('密码',type='password'); ok=st.form_submit_button('进入平台',width='stretch',type='primary')
            if SEED_DEMO_DATA and not PUBLIC_DEPLOYMENT:
                st.info('演示模式默认账号：admin，默认密码：admin123。登录成功后请及时修改密码。')
            if ok:
                result=authenticate(u.strip(),p)
                if result:
                    st.session_state['user']=result
                    target = st.session_state.pop('pending_backend_page', None)
                    if target in ROLE_PAGES.get(result.get('role','查看用户'), []): st.session_state['backend_nav'] = target
                    add_log(result['username'],'登录平台')
                    st.rerun()
                else: st.error('账号或密码错误。')
    return False


def banner():
    research_banner(('演示环境' if DEMO_MODE else '正式数据环境')+'。已整合多人权限、质量校验、备份恢复、实测GIS参考数据、GIS联动预测与约束调度；当前水动力计算核心仍为可替换的演示模型。')


def dashboard():
    page_header('运行工作台', '三维空间、水情、模型任务与预警处置集中呈现。')
    banner()
    refresh_threshold_alerts()
    stats = get_dashboard_statistics()
    cols = st.columns(4)
    for column, item in zip(cols, [('业务监测站', stats['station_count'], '⌖', '业务数据库'), ('当前预警', stats['alert_count'], '△', '待处置事件'), ('预测任务', stats['prediction_count'], 'ƒ', '已记录任务'), ('河道', stats['river_count'], '≈', '业务登记')]):
        with column:
            metric_card(*item)
    latest = get_latest_station_levels()
    st.caption(f'数据更新时间：{get_latest_data_time()}')
    render_scene3d(latest, height=560, key='dashboard_scene')
    actions = st.columns(3)
    for column, label, destination in zip(actions, ['查看运行监测', '咨询水知助手', '进入预警中心'], ['运行监测','水知AI助手','预警中心']):
        with column:
            if destination in ROLE_PAGES.get(role(), []) and st.button(label, key='dash_'+destination, width='stretch'):
                st.session_state['pending_backend_nav'] = destination
                st.rerun()
    if allowed('simulate') and st.button('模拟接收一批演示数据', type='secondary'):
        n = simulate_realtime_update()
        refresh_threshold_alerts()
        add_log(username(), '模拟实时数据接入', details=f'{n}条')
        st.rerun()
    if not latest.empty:
        st.subheader('最新水情')
        st.dataframe(latest, width='stretch', hide_index=True)
    research_footer(APP_VERSION)


def map_page():
    page_header('三维河网', '以真实地表承载空间参考资料和业务水情，选择站点开展定位与研判。')
    render_scene3d(get_latest_station_levels(), height=720, key='backend_scene')
    with st.expander('查看业务监测站最新数据'):
        st.dataframe(get_latest_station_levels(), width='stretch', hide_index=True)
    research_footer(APP_VERSION)

def data_page():
    page_header('数据中心','文件留痕、中文字段映射、质量校验、数据库写入和导出'); banner(); t1,t2,t3=st.tabs(['文件导入','数据库查询','上传记录'])
    with t1:
        dtype=st.selectbox('数据类型',list(DATASET_CONFIG)); st.download_button('下载标准模板',dataframe_to_excel_bytes(TEMPLATES[dtype],dtype),file_name=f'{dtype}模板.xlsx',width='stretch')
        up=st.file_uploader('上传CSV或Excel',type=['csv','xlsx','xls'])
        if up:
            try:
                df=read_uploaded_file(up); st.dataframe(df.head(100),width='stretch'); summary, row_errors=validate_dataframe(dtype,df)
                if summary or row_errors:
                    for e in summary: st.error(e)
                    for e in row_errors: st.error(f"第{e['row']}行 {e['field']}: {e['error']}")
                elif st.button('确认写入共享数据库',type='primary',disabled=not allowed('import')):
                    result=import_with_validation(dtype,df,username(),up); add_log(username(),'导入数据',details=f'{dtype} 新增{result.inserted}/更新{result.updated}/跳过{result.skipped}',log_type='import'); st.success(f'新增{result.inserted}条，更新{result.updated}条，跳过{result.skipped}条')
            except Exception as e: add_log(username(),'导入数据',result='失败',details=str(e)); st.error(str(e))
    with t2:
        dtype2=st.selectbox('查询类型',list(DATASET_CONFIG),key='q'); q=query_table(dtype2); st.dataframe(q,width='stretch',hide_index=True)
        c1,c2,c3=st.columns(3)
        with c1: fmt=st.selectbox('导出格式',['csv','xlsx'],key='efmt')
        with c2: sid=st.text_input('站点筛选(可选)',key='esid')
        with c3: date_range=st.text_input('日期范围(可选,如2026-07-01~2026-08-01)',key='edate')
        if st.button('导出当前表',type='primary'):
            df, dt = (date_range.split('~')[0], date_range.split('~')[1]) if date_range and '~' in date_range else (None, None)
            path=export_table(dtype2,fmt,sid or None,df,dt)
            with open(path,'rb') as f: st.download_button('点击下载文件',f.read(),file_name=path.name)
        if st.button('批量导出全部数据表'):
            path=export_all_tables(fmt); add_log(username(),'导出全量数据',details=path.name,log_type='export')
            with open(path,'rb') as f: st.download_button('点击下载ZIP',f.read(),file_name=path.name)
    with t3:
        with session_scope() as s: rows=s.scalars(select(UploadedFile).order_by(UploadedFile.id.desc()).limit(200)).all()
        st.dataframe(pd.DataFrame([{c.name:getattr(r,c.name) for c in UploadedFile.__table__.columns} for r in rows]),width='stretch',hide_index=True)
    research_footer(APP_VERSION)


def monitoring():
    page_header('运行监测', '三维空间定位与多站点时序分析联动查看；所有数值保留实际单位。')
    options = get_station_options()
    water_stations = options[options.station_type=='水位站']
    ids = water_stations.station_id.tolist()
    names = dict(zip(water_stations.station_id, water_stations.station_name))
    selected = st.multiselect('监测站点', ids, default=ids[:3], format_func=lambda sid: f'{sid} · {names[sid]}')
    hours = st.slider('最近小时数',12,168,72,12)
    render_scene3d(get_latest_station_levels(), height=430, key='monitor_scene', focus_station=selected[0] if selected else None)
    if not selected:
        st.info('请选择至少一个监测站。')
        return
    series = [
        ('水位过程', pd.concat([get_water_level_series(sid,hours) for sid in selected], ignore_index=True), 'water_level','水位（m）'),
        ('流量过程', pd.concat([get_flow_series(sid,hours) for sid in selected], ignore_index=True), 'flow_value','流量（m³/s）'),
        ('降雨过程', get_rainfall_series(hours), 'rainfall','降雨（mm）'),
        ('潮位过程', get_tide_series(hours), 'tide_level','潮位（m）')]
    tabs = st.tabs([item[0] for item in series])
    for tab, (title, frame, value, unit) in zip(tabs, series):
        with tab:
            if frame.empty:
                st.info('所选时间范围没有数据。')
                continue
            st.plotly_chart(time_series_figure(frame,'monitor_time',value,unit,title=title),width='stretch')
            with st.expander('查看原始数值'):
                st.dataframe(frame,width='stretch',hide_index=True)
                st.download_button('下载当前序列',frame.to_csv(index=False).encode('utf-8-sig'),f'{value}_series.csv','text/csv',key='monitor_download_'+value)
    research_footer(APP_VERSION)

def prediction():
    page_header('水动力预测','兼容数据库站点与新吴实测GIS站点；预测结果保存水位与流量序列')
    banner()
    db_options = get_station_options()
    rows = []
    if not db_options.empty:
        for r in db_options.itertuples(index=False):
            if r.station_type == '水位站':
                rows.append({'station_id':str(r.station_id),'station_name':r.station_name,'source':'数据库'})
    for g in load_gis_stations():
        rows.append({'station_id':g['station_id'],'station_name':g['station_name'],'source':'GIS实测'})
    option_df = pd.DataFrame(rows).drop_duplicates(subset=['station_id'], keep='first') if rows else pd.DataFrame(columns=['station_id','station_name','source'])
    if option_df.empty:
        st.warning('暂无可用预测站点。')
        return
    ids = option_df.station_id.tolist()
    sid = st.selectbox('预测站点', ids, format_func=lambda x: f"{x} {option_df.loc[option_df.station_id==x,'station_name'].iloc[0]} [{option_df.loc[option_df.station_id==x,'source'].iloc[0]}]")
    latest = get_latest_station_levels()
    row = latest[latest.station_id.astype(str)==str(sid)] if not latest.empty and 'station_id' in latest.columns else pd.DataFrame()
    current_default = float(row.water_level.iloc[0]) if not row.empty and pd.notna(row.water_level.iloc[0]) else 4.0
    left,right = st.columns([.75,1.25], gap='large')
    with left:
        current = st.number_input('当前水位（m）', value=current_default, step=.01)
        rain = st.number_input('预测期降雨（mm）', value=35.0)
        tide = st.number_input('外河潮位（m）', value=3.1, step=.01)
        gate = st.slider('闸门强度',0.0,.8,.4,.1)
        pump = st.slider('泵站强度',0.0,.8,.4,.1)
        hours = st.slider('预测时长',6,72,24,6)
        if st.button('开始预测', type='primary', disabled=not allowed('predict')):
            st.session_state.pred = run_demo_prediction(sid,current,rain,tide,gate,pump,hours,username())
            add_log(username(),'运行预测',details=st.session_state.pred['task_code'])
    with right:
        pred = st.session_state.get('pred') or get_latest_prediction()
        if pred:
            df = pred['series'] if 'series' in pred else pd.DataFrame({'predict_time':pred['times'],'predicted_level':pred['values'],'predicted_flow':pred.get('flows')})
            c1,c2,c3 = st.columns(3)
            c1.metric('最高水位',f"{pred['max_level']:.2f} m")
            c2.metric('风险等级',pred['risk_level'])
            c3.metric('超4.5m时段',f"{pred.get('over_hours',0)} h")
            st.caption(f"站点：{pred.get('station_name','—')}（{pred.get('station_id','—')}）")
            st.plotly_chart(prediction_figure(df), width='stretch')
            st.caption('拖动旋转查看预测时效、水位与流量的关系；本页使用演示模型。')
    st.dataframe(list_prediction_tasks(),width='stretch',hide_index=True)
    research_footer(APP_VERSION)


def scheduling():
    page_header('智能调度','关联最近预测任务，并结合新吴实测闸泵规模与运行约束生成多目标方案')
    banner()
    pred = get_latest_prediction()
    if not pred:
        st.warning('请先运行预测。')
        return
    st.info(f"关联预测任务：{pred['task_code']}｜站点：{pred.get('station_name',pred.get('station_id','—'))}")
    l,r = st.columns(2)
    with l:
        flood = st.slider('防洪安全',0,100,40)
        drainage = st.slider('排涝效率',0,100,25)
        ecology = st.slider('生态需求',0,100,15)
        energy = st.slider('能耗控制',0,100,10)
        navigation = st.slider('航运保障',0,100,10)
        total = flood+drainage+ecology+energy+navigation
        st.write(f'权重合计：{total}%')
    with r:
        max_level = st.number_input('最高允许水位',value=4.5)
        min_level = st.number_input('最低生态水位',value=2.2)
        max_gate_opening = st.slider('最大闸门开度（%）',20,100,80,5)
        max_pump_hours = st.slider('最大泵站运行时长（h）',1,24,20,1)
        if st.button('生成方案',type='primary',disabled=(total!=100 or not allowed('schedule'))):
            generate_demo_plans(
                pred,
                {'防洪安全':flood,'排涝效率':drainage,'生态需求':ecology,'能耗控制':energy,'航运保障':navigation},
                {'最高允许水位':max_level,'最低生态水位':min_level,'max_gate_opening':max_gate_opening,'max_pump_hours':max_pump_hours},
                pred.get('gate_factor',.4), pred.get('pump_factor',.4),
            )
            add_log(username(),'生成调度方案',details=pred['task_code'])
            st.rerun()
    plans = get_latest_plans()
    st.dataframe(plans,width='stretch',hide_index=True)
    research_footer(APP_VERSION)


def compare():
    page_header('方案比较', '以实际模型指标比较水位、排水和能耗，保留人工推荐与审核。')
    plans = get_latest_plans()
    if plans.empty:
        st.info('尚无候选方案，请先运行预测并生成调度方案。')
        return
    st.plotly_chart(comparison_figure(plans), width='stretch')
    st.caption('水位和能耗越低越优；排水指标越高越优。不同指标不能直接视作同一量纲。')
    code = st.selectbox('推荐方案', plans.plan_code.tolist())
    if st.button('审核并推荐',type='primary',disabled=not allowed('schedule')):
        rid = int(plans.loc[plans.plan_code==code,'id'].iloc[0])
        select_plan(rid,username())
        add_log(username(),'审核推荐方案',details=code)
        st.rerun()
    st.dataframe(plans,width='stretch',hide_index=True)
    research_footer(APP_VERSION)

def alerts():
    page_header('预警中心','阈值预警生成、确认和解除'); refresh_threshold_alerts()
    level_filter = st.selectbox('预警等级',['全部','蓝色','黄色','橙色','红色'])
    df=query_alerts("" if level_filter=="全部" else level_filter)
    level_colors={"蓝色":"🔵","黄色":"🟡","橙色":"🟠","红色":"🔴"}
    if not df.empty and "alert_level" in df.columns:
        df["alert_level"] = df["alert_level"].apply(lambda x: f"{level_colors.get(x, '')}{x}")
    st.dataframe(df,width='stretch',hide_index=True)
    if not df.empty and allowed('alert'):
        aid=st.selectbox('选择预警',df.id.tolist()); action=st.radio('处理方式',['确认','解除'],horizontal=True)
        if st.button('提交处理',type='primary'):
            ok = update_alert_status(int(aid),'已确认' if action=='确认' else '已解除',username())
            if ok: st.success(f'预警 {aid} 已{action}')
            else: st.error('处理失败')
            st.rerun()
    research_footer(APP_VERSION)


def models():
    page_header('模型管理','模型登记、状态和接口');
    with session_scope() as s: rows=s.scalars(select(ModelRegistry).order_by(ModelRegistry.id)).all()
    st.dataframe(pd.DataFrame([{c.name:getattr(r,c.name) for c in ModelRegistry.__table__.columns} for r in rows]),width='stretch',hide_index=True); research_footer(APP_VERSION)


def system():
    page_header('系统管理','用户、日志、备份恢复与正式部署状态')
    a,b = st.columns(2)
    with a:
        section_label('用户管理')
        if allowed('users'):
            with st.form('userform'):
                u=st.text_input('用户名'); p=st.text_input('初始密码',type='password'); rr=st.selectbox('角色',['管理员','科研人员','调度人员','查看用户']); ok=st.form_submit_button('创建或更新用户')
            if ok and u and p:
                success, msg = create_or_update_user(u,p,rr); add_log(username(),'创建或更新用户',details=f'{u}: {msg}',log_type='user')
                st.success(msg) if success else st.error(msg)
            with st.expander('修改当前用户密码'):
                with st.form('pwdform'):
                    old_pwd=st.text_input('旧密码',type='password'); new_pwd=st.text_input('新密码',type='password'); pwd_ok=st.form_submit_button('确认修改')
                if pwd_ok and old_pwd and new_pwd:
                    s2, m2 = change_password(username(), old_pwd, new_pwd)
                    st.success(m2) if s2 else st.error(m2)
        users = list_users()
        st.dataframe(pd.DataFrame([{'用户名':x['username'],'角色':x['role'],'启用':x['enabled'],'最后登录':x['last_login_at']} for x in users]),width='stretch',hide_index=True)
        targets = [x['username'] for x in users if x['username'] != username()]
        if allowed('users') and targets:
            mu = st.selectbox('选择要管理的用户', targets)
            target = next((x for x in users if x['username'] == mu), None)
            c1,c2 = st.columns(2)
            with c1:
                if target:
                    btn = '禁用' if target['enabled'] else '启用'
                    if st.button(btn, key=f'toggle_{mu}'):
                        set_user_enabled(mu, not target['enabled']); add_log(username(),'用户管理',details=f'{btn} {mu}',log_type='user'); st.rerun()
            with c2:
                if target:
                    roles=['管理员','科研人员','调度人员','查看用户']
                    new_role = st.selectbox('角色', roles, index=roles.index(target['role']), key=f'urole_{mu}')
                    if new_role != target['role']:
                        update_user_role(mu,new_role); add_log(username(),'用户管理',details=f'修改 {mu} 角色为 {new_role}',log_type='user'); st.rerun()
    with b:
        section_label('数据备份与恢复')
        if st.button('生成JSON完整备份',type='primary',disabled=not allowed('backup')):
            info = create_json_backup_extended()
            path = Path(info['path'])
            add_log(username(),'生成完整备份',details=f"{path.name} MD5={info['checksum']}",log_type='backup')
            st.success(f"备份完成：{info['table_count']} 个表，MD5 {info['checksum']}")
            st.download_button('下载备份',path.read_bytes(),file_name=path.name,width='stretch')
        restore_file = st.file_uploader('校验/恢复JSON备份',type=['json'],key='restore_json')
        if restore_file:
            candidate = BACKUP_DIR / 'restore_candidate.json'
            candidate.write_bytes(restore_file.getvalue())
            check = verify_backup(str(candidate))
            if check.get('valid'):
                st.success(f"备份校验通过｜MD5 {check['checksum']}｜识别表 {check['known_table_count']}")
                overwrite = st.checkbox('覆盖现有数据（危险操作）',value=False)
                if st.button('执行恢复',disabled=not allowed('backup')):
                    result = restore_from_json(str(candidate),overwrite=overwrite)
                    if result.get('success'):
                        add_log(username(),'恢复备份',details=f"恢复 {result['total_restored']} 条，overwrite={overwrite}",log_type='backup')
                        st.success(f"恢复完成：{result['total_restored']} 条记录")
                    else:
                        st.error(result.get('error','恢复失败'))
            else:
                st.error(check.get('error','备份校验失败'))
        st.warning('PostgreSQL整库级备份仍建议使用 scripts/backup_postgres.ps1 或服务器计划任务。')
    section_label('操作日志')
    st.dataframe(query_logs(),width='stretch',hide_index=True)
    research_footer(APP_VERSION)

def _set_public_page(page_name: str, backend_target: str | None = None) -> None:
    st.session_state['pending_public_page'] = page_name
    if backend_target:
        st.session_state['pending_backend_page'] = backend_target
    st.rerun()


def public_portal() -> None:
    public_topbar()
    public_pages = ['首页','实景三维','数字孪生','水知AI助手','平台概览','关于平台','登录平台']
    pending = st.session_state.pop('pending_public_page',None)
    if pending in public_pages:
        st.session_state['public_page'] = pending
    if st.session_state.get('public_page','首页') not in public_pages:
        st.session_state['public_page'] = '首页'
    page = st.radio('网站导航',public_pages,horizontal=True,label_visibility='collapsed',key='public_page')
    if page == '首页':
        render_command_center_home(_set_public_page)
    elif page == '实景三维':
        render_gis()
    elif page == '数字孪生':
        render_digital_twin()
    elif page == '水知AI助手':
        render_assistant()
    elif page == '平台概览':
        render_overview()
    elif page == '关于平台':
        intro, capabilities, architecture = st.tabs(['平台介绍','业务能力','数据架构'])
        with intro: render_about()
        with capabilities: render_capabilities()
        with architecture: render_architecture()
    elif page == '登录平台':
        login()
    public_footer()

if not user():
    public_portal()
    st.stop()

with st.sidebar:
    sidebar_brand(APP_VERSION)
    st.write(f"用户：**{username()}**  \n角色：**{role()}**")
    pages=ROLE_PAGES.get(role(),['平台首页'])
    pending = st.session_state.pop('pending_backend_nav',None)
    if pending in pages:
        st.session_state['backend_nav'] = pending
    requested = st.session_state.get('backend_nav')
    if requested not in pages:
        st.session_state['backend_nav'] = pages[0]
    page=st.radio('导航',pages,label_visibility='collapsed',key='backend_nav')
    st.divider()
    if st.button('退出登录',width='stretch',type='primary',key='logout_btn'):
        add_log(username(),'退出平台')
        st.session_state.pop('user',None)
        st.session_state.pop('backend_nav',None)
        st.session_state.pop('pending_backend_page',None)
        st.session_state['public_page']='首页'
        st.rerun()

public_topbar()
{'平台首页':dashboard,'水知AI助手':lambda:render_assistant(user()),'三维河网':map_page,'数据中心':data_page,'运行监测':monitoring,'水动力预测':prediction,'智能调度':scheduling,'方案比较':compare,'预警中心':alerts,'模型管理':models,'系统管理':system}[page]()
