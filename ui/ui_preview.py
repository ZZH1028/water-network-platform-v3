import streamlit as st
from ui.theme import inject_research_theme, sidebar_brand, page_header, research_banner, metric_card, research_footer

st.set_page_config(page_title="V1.1 UI预览", layout="wide")
inject_research_theme()
with st.sidebar:
    sidebar_brand("V1.1 整合增强版")
    st.radio("导航", ["平台首页", "河网GIS地图", "水动力预测", "智能调度"], label_visibility="collapsed")
    st.divider()
    st.button("退出登录", type="primary", key="logout_btn", use_container_width=True)
page_header("界面视觉预览", "用于独立查看 V1.1 合并后的校徽、按钮、侧边栏与响应式样式")
research_banner("本页面只展示视觉组件，不连接业务数据库。")
cols=st.columns(4)
for c, item in zip(cols, [("监测站",194,"⌖","GIS实测"),("闸泵设施",32,"▥","GIS实测"),("河道",110,"≈","断面数据"),("断面点",19317,"•","river.txt")]):
    with c: metric_card(*item)
st.info("将浏览器缩窄到手机宽度可检查移动端响应式布局。")
research_footer("V1.1 整合增强版")
