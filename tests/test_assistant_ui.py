"""Behavior checks for assistant permissions, citations and external consent."""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from ui import assistant as ui


def _public_page():
    from ui.assistant import render_assistant
    render_assistant(None)


def _admin_page():
    from ui.assistant import render_assistant
    render_assistant({"username": "reviewer", "role": "管理员"})


def _viewer_page():
    from ui.assistant import render_assistant
    render_assistant({"username": "reader", "role": "查看用户"})


def _switchable_page():
    import streamlit as st
    from ui.assistant import render_assistant
    render_assistant(st.session_state.get("test_current_user"))


@pytest.fixture
def backend(monkeypatch):
    calls = []
    documents = [
        {"id": 1, "title": "专业导读", "is_seed": True, "chunk_count": 2, "byte_size": 80},
        {"id": 2, "title": "流域研究报告", "is_seed": False, "chunk_count": 3, "byte_size": 120},
    ]
    monkeypatch.setattr(ui, "initialize_knowledge_base", lambda: None)
    monkeypatch.setattr(ui, "knowledge_statistics", lambda *, include_uploaded=True: {"document_count": 2 if include_uploaded else 1, "chunk_count": 5 if include_uploaded else 2})
    monkeypatch.setattr(ui, "get_assistant_status", lambda: {"configured": True, "model": "test-compatible-model"})
    monkeypatch.setattr(ui, "list_documents", lambda *, include_uploaded=True: documents if include_uploaded else documents[:1])
    monkeypatch.setattr(ui, "delete_document", lambda document_id: calls.append({"deleted": document_id}) or True)

    def answer(question, history=None, *, allow_external=False, include_uploaded=False):
        calls.append({"question": question, "history": history, "allow_external": allow_external, "include_uploaded": include_uploaded})
        return {
            "answer": "请先准备下游潮位边界资料，并核对时间基准。[1]",
            "mode": "llm" if allow_external else "retrieval",
            "sources": [{"title": "潮汐边界导读", "citation": "[1]", "source_type": "reference_overview", "text": "率定和验证应使用相互独立的数据时段。", "chunk_index": 0, "url": "https://www.noaa.gov/"}],
        }

    monkeypatch.setattr(ui, "answer_question", answer)
    return calls


@pytest.mark.parametrize("url", ["javascript:alert(1)", "http://example.com/report", "https://localhost/a", "https://127.0.0.1/a", "https://10.1.2.3/a", "https://user:secret@example.com/a", "https://example.com:8443/a", "https://example.com\n/a", "https://intranet/a", "https://bad%host.example/a"])
def test_citation_rejects_nonpublic_or_unsafe_urls(url):
    assert ui._safe_source_url(url) is None


def test_citation_accepts_public_https_and_source_metadata():
    assert ui._safe_source_url("https://www.noaa.gov/education") == "https://www.noaa.gov/education"
    exported = ui._conversation_markdown([{"role": "assistant", "content": "请检查边界条件。[1]", "mode": "retrieval", "sources": [{"title": "边界条件导读", "source_type": "reference_overview", "citation": "[1]", "chunk_index": 0, "url": "https://www.noaa.gov/"}]}])
    assert "本地资料检索" in exported
    assert "边界条件导读" in exported
    assert "https://www.noaa.gov/" in exported


@pytest.mark.parametrize(("role", "expected"), [("管理员", True), ("科研人员", True), ("调度人员", False), ("查看用户", False), ("", False)])
def test_document_management_role_gate(role, expected):
    assert ui._can_manage({"role": role}) is expected
    assert not ui._can_manage(None)


def test_researcher_can_import_but_cannot_delete_shared_documents(backend):
    app = AppTest.from_function(_switchable_page, default_timeout=20)
    app.session_state['test_current_user'] = {'username':'researcher', 'role':'科研人员'}
    app.run()
    assert not app.exception
    assert any(tab.label == '资料管理' for tab in app.tabs)
    assert not any(button.key == 'water_knowledge_delete' for button in app.button)


def test_public_chat_uses_local_retrieval_without_consent_and_keeps_citations(backend):
    app = AppTest.from_function(_public_page, default_timeout=20).run()
    assert not app.exception
    assert not app.tabs
    assert app.checkbox[0].value is False
    app.chat_input[0].set_value("如何考虑下游潮位边界？").run()
    assert not app.exception
    assert len(backend) == 1
    assert backend[0]["allow_external"] is False
    assert backend[0]["include_uploaded"] is False
    assert app.metric[0].value == "1"
    messages = app.session_state[ui.MESSAGES_KEY]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[-1]["sources"][0]["citation"] == "[1]"
    assert any("边界资料" in item.value for item in app.markdown)
    app.button(key="water_ai_clear").click().run()
    assert not app.exception
    assert app.session_state[ui.MESSAGES_KEY] == []


def test_explicit_session_consent_is_required_to_call_model(backend):
    app = AppTest.from_function(_public_page, default_timeout=20).run()
    app.checkbox(key=ui.EXTERNAL_KEY).set_value(True).run()
    app.chat_input[0].set_value("如何开展河网模型率定？").run()
    assert not app.exception
    assert backend[-1]["allow_external"] is True
    assert app.session_state[ui.MESSAGES_KEY][-1]["mode"] == "llm"


def test_admin_management_requires_checked_delete_confirmation(backend):
    app = AppTest.from_function(_admin_page, default_timeout=20).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["专业问答", "资料管理", "接入说明"]
    assert app.button(key="water_knowledge_delete").disabled
    assert app.selectbox(key="water_knowledge_delete_document").value == 2
    app.checkbox(key="water_knowledge_delete_confirm_2").set_value(True).run()
    assert not app.button(key="water_knowledge_delete").disabled
    app.button(key="water_knowledge_delete").click().run()
    assert not app.exception
    assert {"deleted": 2} in backend
    assert {"deleted": 1} not in backend


def test_missing_model_configuration_does_not_expose_external_consent(backend, monkeypatch):
    monkeypatch.setattr(ui, "get_assistant_status", lambda: {"configured": False})
    app = AppTest.from_function(_public_page, default_timeout=20).run()
    assert not app.exception
    assert not app.checkbox
    app.chat_input[0].set_value("如何导入水位数据？").run()
    assert not app.exception
    assert backend[-1]["allow_external"] is False


def test_logged_in_reader_can_search_uploaded_material_without_management(backend):
    app = AppTest.from_function(_viewer_page, default_timeout=20).run()
    assert not app.exception
    assert not app.tabs
    assert app.metric[0].value == "2"
    app.chat_input[0].set_value("请检索登录用户共享的报告").run()
    assert not app.exception
    assert backend[-1]["include_uploaded"] is True


def test_account_switch_and_logout_clear_previous_answers_and_consent(backend):
    app = AppTest.from_function(_switchable_page, default_timeout=20).run()
    app.session_state["test_current_user"] = {"username": "first", "role": "查看用户"}
    app.run()
    app.checkbox(key=ui.EXTERNAL_KEY).set_value(True).run()
    app.chat_input[0].set_value("第一个用户的专业报告问题").run()
    assert app.session_state[ui.MESSAGES_KEY]
    app.session_state["test_current_user"] = {"username": "second", "role": "查看用户"}
    app.run()
    assert not app.exception
    assert app.session_state[ui.MESSAGES_KEY] == []
    assert app.checkbox(key=ui.EXTERNAL_KEY).value is False
    app.chat_input[0].set_value("第二个用户的报告问题").run()
    app.session_state["test_current_user"] = None
    app.run()
    assert not app.exception
    assert app.session_state[ui.MESSAGES_KEY] == []
    assert app.checkbox(key=ui.EXTERNAL_KEY).value is False
    assert app.metric[0].value == "1"


def test_actual_public_assistant_cannot_retrieve_uploaded_document(tmp_path, monkeypatch):
    from services.knowledge_service import initialize_knowledge_base, import_document, knowledge_statistics

    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(tmp_path / "knowledge.db"))
    initialize_knowledge_base()
    public_count = knowledge_statistics(include_uploaded=False)["document_count"]
    private = import_document("private-report.txt", "ZXQSENSITIVE482 专用闸泵报告，测站流量为92714。".encode(), title="登录范围专用报告", storage_dir=tmp_path / "files")
    app = AppTest.from_function(_public_page, default_timeout=20).run()
    assert not app.exception
    assert app.metric[0].value == str(public_count)
    app.chat_input[0].set_value("ZXQSENSITIVE482").run()
    assert not app.exception
    answer = app.session_state[ui.MESSAGES_KEY][-1]
    assert all(source["document_id"] != private["id"] for source in answer.get("sources", []))
    assert "92714" not in answer["content"]
    assert "登录范围专用报告" not in answer["content"]

    reader = AppTest.from_function(_viewer_page, default_timeout=20).run()
    reader.chat_input[0].set_value("ZXQSENSITIVE482").run()
    assert not reader.exception
    response = reader.session_state[ui.MESSAGES_KEY][-1]
    assert any(source["document_id"] == private["id"] for source in response["sources"])
