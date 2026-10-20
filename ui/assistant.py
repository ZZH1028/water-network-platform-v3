"""Water-domain retrieval assistant and role-aware knowledge-library interface."""
from __future__ import annotations

import html
import ipaddress
import re
from datetime import datetime
from urllib.parse import urlsplit

import streamlit as st

from services.assistant_service import answer_question, get_assistant_status
from services.knowledge_service import (
    delete_document,
    import_document,
    initialize_knowledge_base,
    knowledge_statistics,
    list_documents,
    search_knowledge,
)


MESSAGES_KEY = "water_assistant_messages"
EXTERNAL_KEY = "water_assistant_allow_external"
PENDING_KEY = "water_assistant_pending_question"
OWNER_KEY = "water_assistant_session_owner"
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_QUESTION_LENGTH = 4000
SOURCE_LABELS = {
    "uploaded": "导入资料",
    "reference": "专业导读",
    "overview": "专业导读",
    "reference_overview": "专业导读",
    "manual": "平台操作手册",
    "operation": "平台操作手册",
    "operation_manual": "平台操作手册",
    "platform_manual": "平台操作手册",
    "guide": "专业导读",
}


def _can_manage(user: dict | None) -> bool:
    return bool(user and user.get("role") in {"管理员", "科研人员"})


def _safe_source_url(value: str) -> str | None:
    """Only make explicitly public HTTPS citations clickable."""
    if not isinstance(value, str) or any(c in value for c in "\r\n\t\\"):
        return None
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            return None
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            if not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", host):
                return None
        if parsed.port not in (None, 443):
            return None
        return value.strip()
    except ValueError:
        return None


def _source_label(value: str) -> str:
    return SOURCE_LABELS.get(str(value), "知识库资料")


def _conversation_markdown(messages: list[dict]) -> str:
    lines = ["# 水专业助手 · 会话记录", "", f"导出时间：{datetime.now():%Y-%m-%d %H:%M}", ""]
    for message in messages:
        lines.extend(["## " + ("我的提问" if message.get("role") == "user" else "水专业助手"), "", str(message.get("content", "")), ""])
        if message.get("role") == "assistant":
            lines.extend(["回答模式：" + ("兼容模型 + 知识检索" if message.get("mode") == "llm" else "本地资料检索"), ""])
            for source in message.get("sources", []):
                citation = str(source.get("citation", ""))
                title = str(source.get("title", "资料"))
                position = source.get("section") or source.get("page") or (int(source.get("chunk_index", 0)) + 1)
                lines.append(f"- {citation} {title} · {_source_label(source.get('source_type', ''))} · 位置：{position}")
                url = _safe_source_url(source.get("source_url") or source.get("url") or "")
                if url:
                    lines.append("  来源：" + url)
            if message.get("sources"):
                lines.append("")
            if message.get("warning"):
                lines.extend(["说明：" + str(message["warning"]), ""])
    return "\n".join(lines)


def _inject_assistant_style() -> None:
    st.markdown(
        """<style>
        .water-ai-hero {padding:27px 30px;border:1px solid rgba(80,181,190,.25);border-radius:20px;background:radial-gradient(ellipse at 90% 0%,rgba(28,155,151,.15),transparent 55%),linear-gradient(120deg,#102331,#102c37);margin:0 0 20px}
        .water-ai-eyebrow {font-size:11px;letter-spacing:2.4px;color:#64d6c5;font-weight:700;margin-bottom:10px}
        .water-ai-title {font-size:30px;color:#f0f7f6;font-weight:750;letter-spacing:1px;margin-bottom:9px}
        .water-ai-description {color:#a9bfca;font-size:14px;line-height:1.8;max-width:920px}
        .water-ai-chip {display:inline-block;padding:5px 10px;border:1px solid rgba(210,188,137,.25);color:#d8c697;border-radius:6px;font-size:11px;margin:14px 8px 0 0}
        .water-ai-mode {padding:13px 17px;border-left:3px solid #52c8b6;background:rgba(58,123,132,.10);border-radius:0 9px 9px 0;color:#b3cad0;font-size:13px;line-height:1.75;margin:4px 0 16px}
        .water-ai-mode strong {color:#d8efea}
        [data-testid="stChatMessage"] {border:1px solid rgba(100,153,167,.18);border-radius:14px;background:rgba(14,31,43,.75);padding:20px 22px;margin-bottom:16px}
        [data-testid="stChatMessage"] p,[data-testid="stChatMessage"] li {line-height:1.85}
        [data-testid="stChatInput"] {border:1px solid rgba(81,188,178,.4);border-radius:13px}
        @media(max-width:700px) {.water-ai-hero {padding:22px 18px}.water-ai-title {font-size:25px}[data-testid="stChatMessage"] {padding:15px 12px}}
        </style>""",
        unsafe_allow_html=True,
    )


def _render_sources(sources: list[dict], *, key_prefix: str) -> None:
    if not sources:
        return
    with st.expander(f"查看引用依据 · {len(sources)} 条", expanded=False):
        for index, source in enumerate(sources):
            citation = str(source.get("citation") or f"[{index + 1}]")
            st.text(f"{citation} {source.get('title', '知识库资料')}")
            section = str(source.get("section") or "")
            page = source.get("page")
            position = f"第 {page} 页" if page else (section or f"片段 {int(source.get('chunk_index', 0)) + 1}")
            st.caption(f"{_source_label(source.get('source_type', ''))} · {position}")
            # Show documents as inert text, including any instructions in an upload.
            text = str(source.get("text", ""))
            st.text(text[:1800] + ("\n…" if len(text) > 1800 else ""))
            url = _safe_source_url(source.get("source_url") or source.get("url") or "")
            if url:
                st.link_button("打开公开来源", url, key=f"{key_prefix}_source_{index}")
            if index < len(sources) - 1:
                st.divider()


def _render_chat(status: dict, user: dict | None = None) -> None:
    configured = bool(status.get("configured"))
    if configured:
        st.checkbox(
            "本会话允许将我的问题、相关资料片段与最近对话发送到已配置的 AI 服务",
            key=EXTERNAL_KEY,
            help="默认关闭。开启后才会调用后台配置的兼容模型；不会发送整座资料库。账号切换或退出后会清空本地会话与授权。",
        )
        mode_text = "兼容模型问答已启用，答案会结合命中资料并列出引用。" if st.session_state[EXTERNAL_KEY] else "模型接口已配置；本会话仍使用本地资料检索。"
    else:
        st.session_state[EXTERNAL_KEY] = False
        mode_text = "当前为本地资料检索：展示可核对的原文摘录与操作步骤。接入兼容 AI 服务后，可启用基于资料的综合问答。"
    st.markdown(f'<div class="water-ai-mode"><strong>{"兼容模型 + 知识检索" if configured and st.session_state.get(EXTERNAL_KEY) else "本地资料检索模式"}</strong><br>{html.escape(mode_text)}</div>', unsafe_allow_html=True)

    messages = st.session_state.setdefault(MESSAGES_KEY, [])
    left, right = st.columns([4, 1])
    with left:
        st.caption("聚焦平原感潮河网、水动力与闸泵调度，也可以询问平台具体操作。" + ("当前可检索内置资料及登录用户共享资料。" if user else "访客仅检索公开的内置导读与操作手册。"))
    with right:
        if st.button("清空会话", key="water_ai_clear", width="stretch", disabled=not messages):
            st.session_state[MESSAGES_KEY] = []
            st.session_state.pop(PENDING_KEY, None)
            st.rerun()
    if messages:
        st.download_button("导出本次会话", _conversation_markdown(messages), file_name="水专业助手_会话记录.md", mime="text/markdown", key="water_ai_export")
    else:
        suggestions = [
            "平原感潮河网为什么会出现潮汐顶托？",
            "如何开展感潮河网模型率定与验证？",
            "闸泵联合调度需要准备哪些资料？",
            "如何在平台导入水位数据并完成质量校验？",
        ]
        columns = st.columns(2)
        for index, question in enumerate(suggestions):
            with columns[index % 2]:
                if st.button(question, key=f"water_ai_suggestion_{index}", width="stretch"):
                    st.session_state[PENDING_KEY] = question
                    st.rerun()
    for index, message in enumerate(messages):
        with st.chat_message(message.get("role", "assistant"), avatar="🌊" if message.get("role") == "assistant" else None):
            st.markdown(message.get("content", ""))
            if message.get("role") == "assistant":
                st.caption("兼容模型 + 知识检索" if message.get("mode") == "llm" else "本地资料检索 · 非大模型生成")
                if message.get("warning"):
                    st.info(message["warning"])
                _render_sources(message.get("sources", []), key_prefix=f"water_ai_message_{index}")

    question = st.chat_input("例如：如何考虑潮位边界，制定闸泵联合调度方案？", key="water_ai_input")
    question = question or st.session_state.pop(PENDING_KEY, None)
    if not question:
        return
    question = str(question).strip()
    if not question:
        return
    if len(question) > MAX_QUESTION_LENGTH:
        st.error(f"问题过长，请精简至 {MAX_QUESTION_LENGTH} 字以内，或拆成几个问题。")
        return
    history = [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="🌊"):
        try:
            with st.spinner("正在检索专业资料与操作手册…"):
                result = answer_question(question, history=history, allow_external=bool(configured and st.session_state.get(EXTERNAL_KEY)), include_uploaded=bool(user))
            messages.append({"role": "assistant", "content": str(result.get("answer", "未找到可用资料，请补充资料或细化问题。")), "sources": result.get("sources", []), "mode": result.get("mode", "retrieval"), "warning": result.get("warning", ""), "model": result.get("model", "")})
        except ValueError as exc:
            messages.append({"role": "assistant", "content": str(exc), "sources": [], "mode": "retrieval"})
        except Exception:
            messages.append({"role": "assistant", "content": "本次检索未完成。请稍后重试；若持续失败，请联系管理员检查知识库与模型连接。", "sources": [], "mode": "retrieval"})
    st.session_state[MESSAGES_KEY] = messages[-40:]
    st.rerun()


def _render_library(user: dict) -> None:
    st.markdown("#### 专业资料库")
    st.caption("资料在本地提取文字、分块并建立检索索引；新增资料导入后即可检索。此过程不会训练或修改大模型权重。")
    st.caption("导入资料供登录用户检索；公开访客只能检索内置导读与操作手册。请确认资料可以在登录用户范围共享。")
    with st.expander("导入专业资料", expanded=True):
        with st.form("water_knowledge_import", clear_on_submit=True):
            upload = st.file_uploader("选择 PDF、Word、文本或结构化资料", type=["pdf", "docx", "txt", "md", "csv", "json"], key="water_knowledge_upload", max_upload_size=20, help="单文件不超过 20 MB。扫描 PDF 需要先完成 OCR；请只导入有权使用的资料。")
            title = st.text_input("资料名称（可选）", max_chars=200, key="water_knowledge_title")
            source_url = st.text_input("公开来源链接（可选，HTTPS）", max_chars=2000, placeholder="https://…", key="water_knowledge_url")
            submit = st.form_submit_button("提取文字并建立索引", type="primary", width="stretch")
        if submit:
            if upload is None:
                st.error("请先选择一份专业资料。")
            elif upload.size > MAX_DOCUMENT_BYTES:
                st.error("文件超过 20 MB，请按章节拆分后再导入。")
            elif source_url.strip() and not _safe_source_url(source_url):
                st.error("来源链接应为公开 HTTPS 地址；也可以暂不填写。")
            else:
                try:
                    with st.spinner("正在提取文字并建立索引…"):
                        document = import_document(upload.name, upload.getvalue(), title=title.strip() or None, source_url=source_url.strip(), source_type="uploaded", uploaded_by=str(user.get("username", "用户")))
                    st.success(f"资料已可检索：{document.get('title', upload.name)}。相同文件会复用已有索引。")
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("资料导入未完成，请检查文件是否可读取并稍后重试。")

    documents = list_documents(include_uploaded=True)
    st.markdown("#### 已索引资料")
    if documents:
        rows = [{"资料名称": doc.get("title", ""), "类别": "内置导读 / 手册" if doc.get("is_seed") else "用户导入", "片段数": doc.get("chunk_count", 0), "大小（KB）": round(doc.get("byte_size", 0) / 1024, 1), "导入者": doc.get("uploaded_by", ""), "导入时间": str(doc.get("created_at", ""))[:19]} for doc in documents]
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("资料库暂无内容，可先导入一份可检索的专业资料。")
    with st.expander("检索验证", expanded=False):
        with st.form("water_knowledge_search"):
            query = st.text_input("输入关键词或专业问题", key="water_knowledge_search_query", max_chars=MAX_QUESTION_LENGTH)
            searched = st.form_submit_button("检索匹配片段")
        if searched:
            if not query.strip():
                st.info("请输入问题或关键词。")
            else:
                try:
                    sources = search_knowledge(query.strip(), limit=6, include_uploaded=True)
                    if sources:
                        _render_sources(sources, key_prefix="water_library_search")
                    else:
                        st.info("未找到相关片段。试试更具体的术语，或补充对应资料。")
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("检索暂时不可用，请稍后重试。")

    removable = [d for d in documents if not d.get("is_seed")]
    if removable and user.get('role') == '管理员':
        with st.expander("移除导入资料", expanded=False):
            choices = {int(d["id"]): d for d in removable}
            selected = st.selectbox("选择要移除的资料", list(choices), format_func=lambda i: str(choices[i].get("title", "资料")), key="water_knowledge_delete_document")
            confirmed = st.checkbox("我确认移除此资料及其检索索引", key=f"water_knowledge_delete_confirm_{selected}")
            if st.button("移除选中资料", key="water_knowledge_delete", disabled=not confirmed):
                try:
                    if delete_document(int(selected)):
                        st.session_state["water_knowledge_notice"] = "选中资料已移除，后续问答将不再检索此资料。既有会话保留原引用摘录。"
                        st.rerun()
                    else:
                        st.info("此资料已不存在，请刷新资料列表。")
                except Exception:
                    st.error("移除资料未完成，请稍后重试。")
    if removable and user.get('role') != '管理员':
        st.caption('科研人员可以导入和验证资料；移除已有资料请由管理员操作。')
    st.caption("内置内容包含专业导读与平台操作手册，导读中的公开参考链接不代表已导入链接站点的全部资料。")


def render_assistant(user: dict | None = None) -> None:
    """Render public questions and optionally privileged document management."""
    owner = "user:" + str(user.get("username") or user.get("id") or user.get("role")) if user else "anonymous"
    if st.session_state.get(OWNER_KEY) != owner:
        st.session_state[MESSAGES_KEY] = []
        st.session_state[EXTERNAL_KEY] = False
        st.session_state.pop(PENDING_KEY, None)
        st.session_state[OWNER_KEY] = owner
    _inject_assistant_style()
    st.markdown('<div class="water-ai-hero"><div class="water-ai-eyebrow">WATER INTELLIGENCE · EVIDENCE FIRST</div><div class="water-ai-title">水专业智能助手</div><div class="water-ai-description">让专业知识与工程数据连接起来。围绕平原感潮河网开展资料检索、专业答疑与平台操作引导，每一条引用都可以回到资料片段核对。</div><span class="water-ai-chip">平原感潮河网</span><span class="water-ai-chip">资料检索与引用</span><span class="water-ai-chip">平台操作指引</span></div>', unsafe_allow_html=True)
    try:
        initialize_knowledge_base()
        stats = knowledge_statistics(include_uploaded=bool(user))
        status = get_assistant_status()
    except Exception:
        st.error("知识库暂时不可用，请联系管理员检查本地存储权限与服务状态。")
        return
    columns = st.columns(3)
    columns[0].metric("已索引资料", stats.get("document_count", 0))
    columns[1].metric("可检索片段", stats.get("chunk_count", 0))
    columns[2].metric("模型接口", "已配置" if status.get("configured") else "待配置")
    notice = st.session_state.pop("water_knowledge_notice", None)
    if notice:
        st.success(notice)
    if _can_manage(user):
        chat_tab, library_tab, settings_tab = st.tabs(["专业问答", "资料管理", "接入说明"])
        with chat_tab:
            _render_chat(status, user)
        with library_tab:
            _render_library(user or {})
        with settings_tab:
            st.markdown("#### 配置兼容模型")
            st.write("管理员可在服务环境中配置以下变量。密钥通过环境设置安全录入，页面不会展示或保存密钥值。")
            st.code("WATER_AI_BASE_URL=https://你的兼容服务/v1\nWATER_AI_MODEL=模型名称\nWATER_AI_API_KEY=通过环境设置安全录入", language="text")
            st.caption("请使用公开 HTTPS 兼容接口。配置完成后，本会话仍默认使用本地检索；明确勾选允许发送问题、片段与最近对话后，才会向服务发起请求。")
            if status.get("configured"):
                st.success("兼容接口所需变量已配置。是否实际可用，会在用户授权的问答请求中验证。")
                st.caption("已配置模型：" + str(status.get("model") or "默认模型"))
            else:
                st.info("当前无需密钥即可使用本地专业资料检索与平台操作手册。")
            st.markdown("#### 扩充专业知识范围")
            st.write("建议按流域与主题整理资料：潮汐边界、水文监测、水动力模型、闸泵联合调度、防洪排涝、水生态与数据质量。优先导入授权规范、正式报告与模型说明，并填写公开来源。知识库的覆盖范围由实际索引内容决定。")
    else:
        _render_chat(status, user)
        st.caption("管理员与科研人员登录后可以导入专业资料、管理知识来源，并验证检索结果。")
