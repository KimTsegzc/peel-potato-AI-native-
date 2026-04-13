from __future__ import annotations

import difflib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .... import LLMProvider
from ....features.conversation_context import REPO_ROOT
from ....features.shared_uploads import resolve_attachment_path
from ....integrations.email_sender import EmailSender, EmailSenderError
from ...contracts import AgentRequest, AgentResponse
from ..base import BaseSkill
from .pending_confirmation import (
    clear_pending_email_confirmation,
    load_pending_email_confirmation,
    save_pending_email_confirmation,
)


_EMAIL_ADAPTER_MODEL = "qwen-turbo"
_EMAIL_ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_MAIL_HISTORY_QUERY_RE = re.compile(r"已发送|发过.*邮件|邮件记录|邮件历史|我刚发了哪些邮件", re.IGNORECASE)
_CONFIRM_SEND_YES_RE = re.compile(r"^(是|好|好的|确认|确认发送|发吧|发送|可以|行|嗯|yes|y)$", re.IGNORECASE)
_CONFIRM_SEND_NO_RE = re.compile(r"^(否|不|不要|取消|不用了|不发了|no|n)$", re.IGNORECASE)
_BODY_COMMAND_LIKE_RE = re.compile(
    r"^(发|发送|帮我|请|给|整理|汇总|总结|列举|梳理|分析).*(邮件|发给|报告|整理|汇总|列举|邮箱)?",
    re.IGNORECASE,
)
_RICH_BODY_REQUEST_RE = re.compile(
    r"更新|最新|局势|战局|分析|影响|报告|整理|汇总|总结|梳理|三点|要点|附来源|来源|简报|研判",
    re.IGNORECASE,
)
_CONTACT_FILE = Path(__file__).resolve().parent / "data" / "contacts.json"
_SHARED_SPACE_DIR = REPO_ROOT / "Memory" / "shared_space"
_PHYSICAL_EXAM_KEYWORD = "体检单"
_PHYSICAL_EXAM_FIXED_SUBJECT = "广州分行直营中心经营体检数据"
_PHYSICAL_EXAM_FIXED_BODY = (
    "广州直营中心客户经理业绩体检简报\n"
    "现将广州直营中心李东明、江振杰、崔翔越三位直营客户经理2025 年 6 月 —2026 年 2 月业绩体检情况简要汇报如下：\n"
    "三位整体业绩均达标、增长动力充足，核心指标表现亮眼：\n"
    "江振杰：综合排名 Top3%，9 项指标全达标，产销业绩 11284.5 万（超中心均值 359%），客户基础与执行能力全面优秀，可作为标杆分享经验。\n"
    "李东明：综合排名 Top2%，9 项指标 8 项达标，团队贡献分 120（超中心均值 307%），仅客户维护略低于均值，需小幅优化。\n"
    "崔翔越：综合排名 Top5%，业绩增长突出，AUM 当月新增 1827.388 万（超中心均值 237.3%），客户基础与团队贡献待提升，需制定专项改进计划。\n"
    "整体来看，团队业绩稳健、优势明显，后续可聚焦短板优化，持续提升客户经营与综合服务能力。"
)
_GENERIC_AUDIENCE_RE = re.compile(
    r"与会人员|参会人员|所有人|全部人|全部联系人|全部联系人|所有联系人|通讯录所有人|通讯录全部人|大家|各位|各位领导同事|领导同事",
    re.IGNORECASE,
)
_CONTACT_SPLIT_RE = re.compile(r"[\s,，。.:：;；()（）\[\]【】<>《》'\"/\\|]+")
_MULTI_RECEIVER_SPLIT_RE = re.compile(r"\s*(?:,|，|;|；|、|\n|和|及|以及|还有)\s*")


def _resolve_skill_model(request: AgentRequest) -> str:
    selected = str(request.model or "").strip()
    return selected or _EMAIL_ADAPTER_MODEL


def _strip_user_prefix(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.lower().startswith("user:"):
        return stripped[5:].strip()
    return stripped


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_attachment_hints(source: dict[str, Any] | None) -> dict[str, Any]:
    payload = source if isinstance(source, dict) else {}

    attachments_raw = payload.get("attachments")
    attachments: list[dict[str, Any]] = []
    if isinstance(attachments_raw, list):
        for item in attachments_raw:
            if isinstance(item, dict):
                attachments.append(dict(item))

    memory_refs_raw = payload.get("memory_refs") or payload.get("memory_attachments")
    memory_refs: list[str] = []
    if isinstance(memory_refs_raw, list):
        for item in memory_refs_raw:
            text = str(item or "").strip()
            if text:
                memory_refs.append(text)

    return {
        "attachments": attachments,
        "memory_refs": memory_refs,
    }


def _extract_attachment_paths(attachments: list[dict[str, Any]] | None) -> list[str]:
    resolved_paths: list[str] = []
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        candidate = str(item.get("path") or item.get("file_path") or item.get("filepath") or "").strip()
        if candidate:
            resolved_paths.append(candidate)
    return _dedupe_text_list(resolved_paths)


def _extract_request_attachment_paths(request: AgentRequest) -> list[str]:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    attachments = metadata.get("attachments") if isinstance(metadata.get("attachments"), list) else []
    resolved_paths: list[str] = []
    for item in attachments:
        if not isinstance(item, dict):
            continue
        direct_path = str(item.get("path") or item.get("file_path") or item.get("filepath") or "").strip()
        if direct_path:
            resolved_paths.append(direct_path)
            continue
        resolved_attachment_path = resolve_attachment_path(item)
        if resolved_attachment_path is not None:
            resolved_paths.append(str(resolved_attachment_path))
    return _dedupe_path_list(resolved_paths)


def _extract_request_attachment_display_names(request: AgentRequest) -> dict[str, str]:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    attachments = metadata.get("attachments") if isinstance(metadata.get("attachments"), list) else []
    display_names: dict[str, str] = {}
    for item in attachments:
        if not isinstance(item, dict):
            continue
        resolved_attachment_path = None
        direct_path = str(item.get("path") or item.get("file_path") or item.get("filepath") or "").strip()
        if direct_path:
            resolved_attachment_path = Path(direct_path).resolve()
        else:
            resolved_attachment_path = resolve_attachment_path(item)
        if resolved_attachment_path is None:
            continue
        display_name = str(item.get("original_name") or item.get("name") or resolved_attachment_path.name).strip()
        if display_name:
            display_names[str(resolved_attachment_path)] = display_name
    return display_names


def _parse_email_request(request: AgentRequest) -> tuple[str, str, str | None, dict[str, Any]]:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    email_meta = metadata.get("email") if isinstance(metadata.get("email"), dict) else metadata

    subject = str((email_meta.get("subject") or "")).strip() if isinstance(email_meta, dict) else ""
    body = str((email_meta.get("body") or email_meta.get("content") or "")).strip() if isinstance(email_meta, dict) else ""
    receiver = str((email_meta.get("receiver") or email_meta.get("to") or "")).strip() if isinstance(email_meta, dict) else ""
    field_sources = {
        "subject": "metadata" if subject else None,
        "body": "metadata" if body else None,
        "receiver": "metadata" if receiver else None,
    }
    attachment_hints = _extract_attachment_hints(email_meta if isinstance(email_meta, dict) else None)

    if subject or body or receiver or attachment_hints["attachments"] or attachment_hints["memory_refs"]:
        return subject, body, receiver or None, {"field_sources": field_sources, **attachment_hints}

    raw_input = _strip_user_prefix(request.user_input)

    payload = _extract_json_payload(raw_input)
    if payload:
        subject = str(payload.get("subject") or "").strip()
        body = str(payload.get("body") or payload.get("content") or "").strip()
        receiver = str(payload.get("receiver") or payload.get("to") or "").strip()
        field_sources = {
            "subject": "json" if subject else None,
            "body": "json" if body else None,
            "receiver": "json" if receiver else None,
        }
        attachment_hints = _extract_attachment_hints(payload)
        return subject, body, receiver or None, {"field_sources": field_sources, **attachment_hints}

    return "", "", None, {"field_sources": field_sources, **attachment_hints}


def _extract_receiver_from_text(text: str) -> str | None:
    match = _EMAIL_ADDRESS_RE.search(text or "")
    if not match:
        return None
    return match.group(0).strip() or None


def _extract_receivers_from_text(text: str) -> list[str]:
    receivers: list[str] = []
    for match in _EMAIL_ADDRESS_RE.findall(text or ""):
        normalized = str(match or "").strip()
        if normalized and normalized not in receivers:
            receivers.append(normalized)
    return receivers


def _split_receiver_tokens(text: str | None) -> list[str]:
    stripped = str(text or "").strip()
    if not stripped:
        return []
    parts = [item.strip() for item in _MULTI_RECEIVER_SPLIT_RE.split(stripped) if item.strip()]
    return parts or [stripped]


def _dedupe_text_list(items: list[str]) -> list[str]:
    unique_items: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_items.append(normalized)
    return unique_items


def _dedupe_path_list(paths: list[str]) -> list[str]:
    unique_items: list[str] = []
    seen: set[str] = set()
    for item in paths:
        candidate = str(item or "").strip()
        normalized = str(Path(candidate).resolve()) if candidate else ""
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_items.append(normalized)
    return unique_items


def _normalize_contact_key(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[\s\-_.·]", "", value)
    return value


def _load_contacts() -> list[dict[str, Any]]:
    if not _CONTACT_FILE.exists():
        return []
    try:
        payload = json.loads(_CONTACT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []

    contacts: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        email = str(item.get("email") or "").strip()
        if not name or not email:
            continue
        aliases_raw = item.get("aliases")
        aliases: list[str] = []
        if isinstance(aliases_raw, list):
            for alias in aliases_raw:
                alias_text = str(alias or "").strip()
                if alias_text:
                    aliases.append(alias_text)
        contacts.append(
            {
                "name": name,
                "email": email,
                "aliases": aliases,
            }
        )
    return contacts


def _build_contact_maps(contacts: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
    by_key: dict[str, dict[str, Any]] = {}
    keywords: list[tuple[str, dict[str, Any]]] = []
    for contact in contacts:
        names = [str(contact.get("name") or "").strip(), *[str(a).strip() for a in contact.get("aliases") or []]]
        for name in names:
            if not name:
                continue
            key = _normalize_contact_key(name)
            if key:
                by_key[key] = contact
                keywords.append((name, contact))
    # 长词优先，避免 "谢" 覆盖 "谢鑫"。
    keywords.sort(key=lambda item: len(item[0]), reverse=True)
    return by_key, keywords


def _resolve_receivers_from_contacts(receiver: str | None, raw_input: str) -> tuple[list[str], dict[str, Any]]:
    contacts = _load_contacts()
    receiver_tokens = _split_receiver_tokens(receiver)
    resolved_receivers = _dedupe_text_list(_extract_receivers_from_text(receiver or "") + _extract_receivers_from_text(raw_input if not receiver_tokens else ""))

    if not contacts:
        explicit_emails = _dedupe_text_list(_extract_receivers_from_text(receiver or "") + _extract_receivers_from_text(raw_input))
        if explicit_emails:
            return explicit_emails, {"contact_resolved": False, "contact_match": "already_email"}
        return resolved_receivers, {"contact_resolved": False, "contact_match": "none"}

    by_key, keywords = _build_contact_maps(contacts)
    matched_names: list[str] = []
    match_types: list[str] = []
    unresolved_tokens: list[str] = []

    def _append_contact_email(email_value: str | None, *, contact_name: str | None = None, match_type: str | None = None) -> None:
        email_text = str(email_value or "").strip()
        if not email_text or email_text in resolved_receivers:
            return
        resolved_receivers.append(email_text)
        if contact_name and contact_name not in matched_names:
            matched_names.append(contact_name)
        if match_type and match_type not in match_types:
            match_types.append(match_type)

    for email_value in _extract_receivers_from_text(receiver or "") + _extract_receivers_from_text(raw_input):
        _append_contact_email(email_value, match_type="already_email")

    for token in receiver_tokens:
        if _EMAIL_ADDRESS_RE.fullmatch(token):
            _append_contact_email(token, match_type="already_email")
            continue
        hit = by_key.get(_normalize_contact_key(token))
        if hit:
            _append_contact_email(hit.get("email"), contact_name=str(hit.get("name") or "").strip(), match_type="receiver_exact")
            continue
        close = difflib.get_close_matches(_normalize_contact_key(token), list(by_key.keys()), n=1, cutoff=0.82)
        if close:
            hit = by_key.get(close[0])
            if hit:
                _append_contact_email(hit.get("email"), contact_name=str(hit.get("name") or "").strip(), match_type="fuzzy")
                continue
        unresolved_tokens.append(token)

    text = raw_input or ""
    for keyword, hit in keywords:
        if keyword and keyword in text:
            _append_contact_email(hit.get("email"), contact_name=str(hit.get("name") or "").strip(), match_type="text_contains")

    return resolved_receivers, {
        "contact_resolved": bool(matched_names),
        "contact_match": ",".join(match_types) if match_types else "none",
        "contact_names": matched_names,
        "unresolved_receivers": unresolved_tokens,
    }


def _resolve_all_contact_emails() -> list[str]:
    contacts = _load_contacts()
    emails = [str(contact.get("email") or "").strip() for contact in contacts if str(contact.get("email") or "").strip()]
    return _dedupe_text_list(emails)


def _is_generic_audience_request(receiver: str | None, raw_input: str) -> bool:
    combined = "\n".join(part for part in [str(receiver or "").strip(), str(raw_input or "").strip()] if part)
    return bool(_GENERIC_AUDIENCE_RE.search(combined))


def _find_shared_space_files_by_keyword(keyword: str) -> list[Path]:
    normalized_keyword = str(keyword or "").strip()
    if not normalized_keyword or not _SHARED_SPACE_DIR.exists():
        return []
    return sorted(
        [path for path in _SHARED_SPACE_DIR.rglob("*") if path.is_file() and normalized_keyword in path.name],
        key=lambda item: str(item.relative_to(_SHARED_SPACE_DIR)).lower(),
    )


def _user_explicitly_named_receivers(raw_input: str) -> bool:
    if _extract_receivers_from_text(raw_input):
        return True
    contacts = _load_contacts()
    _, keywords = _build_contact_maps(contacts)
    return any(keyword and keyword in (raw_input or "") for keyword, _ in keywords)


def _resolve_special_attachments(raw_input: str, attachment_paths: list[str]) -> tuple[list[str], str | None]:
    resolved_paths = list(attachment_paths)
    if _PHYSICAL_EXAM_KEYWORD not in (raw_input or ""):
        return _dedupe_path_list(resolved_paths), None

    matches = _find_shared_space_files_by_keyword(_PHYSICAL_EXAM_KEYWORD)
    if not matches:
        return _dedupe_path_list(resolved_paths), f"shared_space 里没有找到名称包含“{_PHYSICAL_EXAM_KEYWORD}”的文件。"
    if len(matches) > 1:
        names = "，".join(path.name for path in matches)
        return _dedupe_path_list(resolved_paths), f"shared_space 里找到了多个“{_PHYSICAL_EXAM_KEYWORD}”附件：{names}。请保留一个后再重试。"

    resolved_paths.append(str(matches[0]))
    return _dedupe_path_list(resolved_paths), None


def _is_physical_exam_email(raw_input: str, attachment_paths: list[str]) -> bool:
    if _PHYSICAL_EXAM_KEYWORD in (raw_input or ""):
        return True
    return any(_PHYSICAL_EXAM_KEYWORD in Path(path).name for path in attachment_paths)


def _display_attachment_name(path_text: str, request_display_names: dict[str, str] | None = None) -> str:
    normalized_path = str(Path(str(path_text or "").strip()).resolve()) if str(path_text or "").strip() else ""
    if request_display_names and normalized_path in request_display_names:
        return request_display_names[normalized_path]

    raw_name = Path(normalized_path or path_text).name
    if _PHYSICAL_EXAM_KEYWORD not in raw_name:
        return raw_name

    return re.sub(r"^[A-Za-z0-9-]+_", "", raw_name, count=1)


def _adapt_email_request_with_llm(request: AgentRequest, model_name: str) -> dict[str, str] | None:
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    raw_input = _strip_user_prefix(request.user_input)
    system_prompt = (
        "你是邮件参数提取器。"
        "请从用户输入和metadata中提取邮件参数，并只返回JSON对象。"
        "JSON schema: {\"receiver\": string, \"subject\": string, \"body\": string, \"attachments\": array, \"memory_refs\": array}。"
        "receiver 可以是邮箱，也可以是用户提到的联系人姓名，后端会再做联系人映射。"
        "如果缺少subject，请根据用户意图生成一个简短明确的主题。"
        "如果缺少body，请根据用户需求补全成可直接发送的邮件正文。"
        "如果用户已经明确给出很短的正文，如“你好”“收到请回复”，允许保留短正文。"
        "attachments 和 memory_refs 当前只做保留位，没有内容时返回空数组。"
        "禁止输出除JSON外的任何文字。"
    )
    user_payload = {
        "user_input": raw_input,
        "metadata": metadata,
    }
    try:
        response = LLMProvider.with_response_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            model=model_name,
        )
    except Exception:
        return None

    payload = _extract_json_payload(str(response.get("content", "") or ""))
    if not payload:
        return None

    receiver = str(payload.get("receiver") or payload.get("to") or "").strip()
    subject = str(payload.get("subject") or "").strip()
    body = str(payload.get("body") or payload.get("content") or "").strip()
    if not receiver:
        receiver = _extract_receiver_from_text(raw_input) or ""
    return {
        "receiver": receiver,
        "subject": subject,
        "body": body,
    }


def _build_usage_tip() -> str:
    return (
        "我可以直接帮你发邮件，再补一句就能发出：\n"
        "比如：发给 xiexin1.gd@ccb.com 和 longjiang.gd@ccb.com，主题“伊朗局势报告”，正文写昨天三点变化。\n"
        "或者：给 xx@ccb.com、yy@ccb.com 发会议提醒，说明明早9点五楼会议室。"
    )


def _build_missing_receiver_tip() -> str:
    return (
        "我已经进入邮件发送技能了，但还缺明确收件人。\n"
        "你可以直接给一个或多个邮箱地址，或说联系人姓名，例如：发给谢鑫和龙江，整理昨天伊朗局势三点更新并附来源。"
    )


def _normalize_compare_text(text: str) -> str:
    value = (text or "").strip().lower()
    return re.sub(r"[\s\n\r\t，。；;：:、,.!?！？（）()【】\[\]<>《》\-—_]", "", value)


def _sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"[。！？!?\n]+", text or "") if part.strip()]
    return len(parts)


def _looks_like_subject_echo(body: str, subject: str) -> bool:
    normalized_body = _normalize_compare_text(body)
    normalized_subject = _normalize_compare_text(subject)
    if not normalized_body or not normalized_subject:
        return False
    if normalized_body == normalized_subject:
        return True
    if normalized_body.startswith(normalized_subject) or normalized_subject.startswith(normalized_body):
        return True
    similarity = difflib.SequenceMatcher(None, normalized_body, normalized_subject).ratio()
    return similarity >= 0.88


def _needs_rich_body(raw_input: str) -> bool:
    return bool(_RICH_BODY_REQUEST_RE.search(raw_input or ""))


def _is_low_quality_body(
    body: str,
    raw_input: str,
    *,
    subject: str = "",
    explicit_body: bool = False,
    require_rich_body: bool = False,
) -> bool:
    text = (body or "").strip()
    user_text = (raw_input or "").strip()
    if not text:
        return True
    if len(text) < 24 and not explicit_body:
        return True
    if _looks_like_subject_echo(text, subject):
        return True
    if user_text and text == user_text:
        return True
    if _BODY_COMMAND_LIKE_RE.search(text):
        return True
    if ("发给" in text or "邮箱" in text) and not explicit_body:
        return True
    if require_rich_body and _sentence_count(text) < 3:
        return True
    return False


def _refine_email_body_with_llm(
    *,
    subject: str,
    body: str,
    raw_input: str,
    model_name: str,
    require_rich_body: bool = False,
) -> str | None:
    structure_requirement = (
        "要求：至少3句话；包含背景、要点和结尾。"
        if not require_rich_body
        else "要求：必须写成可直接发送的完整邮件正文，至少10句话（500字），并包含开场说明、3个独立要点和收尾判断；各要点尽量单独成句。"
    )
    source_requirement = "请尽量联网用今天搜到最新的可靠信息，并在正文中自然写出来源线索。"
    system_prompt = (
        "你是邮件正文润色助手。"
        "请将用户意图改写成可直接发送的正式中文邮件正文。"
        f"{structure_requirement}"
        f"{source_requirement}"
        "禁止只写一句话摘要，禁止把标题原样重复成正文。"
        "只输出正文，不要标题，不要额外说明。"
    )
    payload = {
        "user_input": raw_input,
        "subject": subject,
        "body": body,
    }
    try:
        response = LLMProvider.with_response_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            model=model_name,
            enable_search=True,
        )
    except Exception:
        return None

    refined = str(response.get("content", "") or "").strip()
    if not refined or _is_low_quality_body(refined, raw_input, subject=subject, require_rich_body=require_rich_body):
        return None
    return refined


def _is_mail_history_query(text: str) -> bool:
    return bool(_MAIL_HISTORY_QUERY_RE.search(text or ""))


def _explain_email_failure_with_llm(
    *,
    error_text: str,
    receiver: str | None,
    subject: str,
    request: AgentRequest,
    model_name: str,
) -> str | None:
    raw_input = _strip_user_prefix(request.user_input)
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    system_prompt = (
        "你是邮件发送失败解释助手。"
        "请根据SMTP错误，给用户一个简洁中文解释。"
        "输出2到4行："
        "第1行写主要原因；"
        "第2到4行给出可执行修复建议。"
        "如果收件人不是完整邮箱（缺少@或域名），必须明确指出并给出示例。"
        "不要输出JSON，不要编造成功发送结果。"
    )
    payload = {
        "error": error_text,
        "receiver": receiver,
        "subject": subject,
        "user_input": raw_input,
        "metadata": metadata,
    }
    try:
        response = LLMProvider.with_response_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            model=model_name,
        )
    except Exception:
        return None

    explanation = str(response.get("content", "") or "").strip()
    return explanation or None


def _normalize_confirmation_reply(text: str) -> str:
    value = _strip_user_prefix(text)
    return re.sub(r"[\s，。；;：:!?！？]", "", value).strip().lower()


def _build_receiver_confirmation_prompt(
    receivers: list[str],
    *,
    repeated: bool = False,
    receiver_display: str | None = None,
    attachment_names: list[str] | None = None,
) -> str:
    opening = "我编好内容了，帮我确认一下收件人，我怕打扰到大家~" if not repeated else "我还在等你确认收件人，怕打扰到大家~"
    lines = [opening, f"收件人：{str(receiver_display or '，'.join(receivers) or '未识别').strip()}"]
    if attachment_names:
        lines.append(f"附件：{'，'.join(attachment_names)}")
    lines.append("回复“是”发送，回复“否”取消。")
    return "\n".join(lines)


def _send_email_and_build_response(
    *,
    request: AgentRequest,
    skill_name: str,
    skill_model: str,
    subject: str,
    body: str,
    receivers: list[str],
    attachments: list[str],
    base_metrics: dict[str, Any],
) -> AgentResponse:
    try:
        result = EmailSender.send_text(
            subject=subject,
            body=body,
            receiver=receivers,
            attachments=attachments,
        )
    except EmailSenderError as exc:
        failure_reason = str(exc)
        llm_failure_explanation = _explain_email_failure_with_llm(
            error_text=failure_reason,
            receiver=", ".join(receivers),
            subject=subject,
            request=request,
            model_name=skill_model,
        )
        content = f"邮件发送失败：{failure_reason}"
        if llm_failure_explanation:
            content = f"邮件发送失败。\n{llm_failure_explanation}\n\n原始错误：{failure_reason}"
        return AgentResponse(
            content=content,
            metrics={
                "skill": skill_name,
                "send_email": {
                    "ok": False,
                    "reason": failure_reason,
                    "receiver": ", ".join(receivers),
                    "receivers": receivers,
                    "attachments": attachments,
                    "subject": subject,
                    **base_metrics,
                    "llm_failure_explainer_used": bool(llm_failure_explanation),
                    "llm_failure_explainer_model": skill_model,
                },
            },
        )

    final_receiver = str(result.get("receiver") or ", ".join(receivers))
    final_subject = str(result.get("subject") or subject)
    transport = str(result.get("transport") or "")
    final_attachments = [str(item or "").strip() for item in result.get("attachments") or attachments if str(item or "").strip()]
    sent_at = datetime.now().strftime("%y年%m月%d日，%H:%M:%S")
    attachment_names = [Path(item).name for item in final_attachments]
    content_lines = [
        "邮件已发送。",
        f"收件人：{final_receiver or '未返回'}",
        f"主题：{final_subject}",
    ]
    if attachment_names:
        content_lines.append(f"附件：{'，'.join(attachment_names)}")
    content_lines.append(f"发送时间: {sent_at}")
    return AgentResponse(
        content="\n".join(content_lines),
        metrics={
            "skill": skill_name,
            "send_email": {
                "ok": True,
                "receiver": final_receiver,
                "receivers": result.get("receivers") or receivers,
                "attachments": final_attachments,
                "subject": final_subject,
                "transport": transport,
                "smtp_host": result.get("smtp_host"),
                "smtp_port": result.get("smtp_port"),
                **base_metrics,
            },
        },
    )


class SendEmailSkill(BaseSkill):
    name = "send_email"
    display_name = "邮件发送"
    description = "发送邮件技能：根据前端指令发送SMTP文本邮件，可指定收件人、主题和正文。"
    routing_hints = (
        "明确要求发送邮件、代发邮件、通知邮件",
        "用户明确给出收件人、主题、正文等字段",
    )
    avoid_hints = (
        "普通闲聊与开放问答",
        "内部职能分工查询",
    )
    routing_examples = (
        "帮我发邮件给xx@xx.com，主题是会议提醒，正文是明早9点开会",
        "发送邮件 {\"receiver\":\"xx@xx.com\",\"subject\":\"测试\",\"body\":\"你好\"}",
    )
    manual_relpath = "SKILL.md"

    def run_stream(self, request: AgentRequest) -> Iterator[dict]:
        response = self.run_once(request)
        yield {"type": "pulse", "stage": "accepted", "elapsed_seconds": 0.0}
        yield {"type": "delta", "content": response.content}
        yield {"type": "done", "content": response.content, "metrics": response.metrics}

    def run_once(self, request: AgentRequest) -> AgentResponse:
        raw_input = _strip_user_prefix(request.user_input)
        skill_model = _resolve_skill_model(request)
        pending_confirmation = load_pending_email_confirmation(request.session_id)
        if pending_confirmation:
            confirmation_reply = _normalize_confirmation_reply(raw_input)
            receivers = [str(item or "").strip() for item in pending_confirmation.get("receivers") or [] if str(item or "").strip()]
            attachments = [str(item or "").strip() for item in pending_confirmation.get("attachments") or [] if str(item or "").strip()]
            pending_attachment_names = pending_confirmation.get("attachment_names") if isinstance(pending_confirmation.get("attachment_names"), list) else []
            attachment_names = [str(item or "").strip() for item in pending_attachment_names if str(item or "").strip()] or [Path(item).name for item in attachments]
            pending_base_metrics = pending_confirmation.get("base_metrics") if isinstance(pending_confirmation.get("base_metrics"), dict) else {}
            receiver_display = str(pending_confirmation.get("receiver_display") or pending_base_metrics.get("receiver_display") or "").strip()
            if _CONFIRM_SEND_YES_RE.fullmatch(confirmation_reply):
                clear_pending_email_confirmation(request.session_id)
                return _send_email_and_build_response(
                    request=request,
                    skill_name=self.name,
                    skill_model=skill_model,
                    subject=str(pending_confirmation.get("subject") or "").strip(),
                    body=str(pending_confirmation.get("body") or "").strip(),
                    receivers=receivers,
                    attachments=attachments,
                    base_metrics={
                        **pending_base_metrics,
                        "confirmation_required": True,
                        "confirmation_reply": "yes",
                    },
                )
            if _CONFIRM_SEND_NO_RE.fullmatch(confirmation_reply):
                clear_pending_email_confirmation(request.session_id)
                return AgentResponse(
                    content="好，这封邮件先不发了，已取消。",
                    metrics={
                        "skill": self.name,
                        "send_email": {
                            "ok": False,
                            "reason": "user_cancelled",
                            "receiver": "，".join(receivers),
                            "receivers": receivers,
                            "attachments": attachments,
                            "subject": str(pending_confirmation.get("subject") or "").strip(),
                            **pending_base_metrics,
                            "confirmation_required": True,
                            "confirmation_reply": "no",
                        },
                    },
                )
            return AgentResponse(
                content=_build_receiver_confirmation_prompt(
                    receivers,
                    repeated=True,
                    receiver_display=receiver_display or None,
                    attachment_names=attachment_names,
                ),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "confirmation_pending",
                        "receiver": "，".join(receivers),
                        "receivers": receivers,
                        "attachments": attachments,
                        "subject": str(pending_confirmation.get("subject") or "").strip(),
                        **pending_base_metrics,
                        "confirmation_required": True,
                        "confirmation_reply": "other",
                    },
                },
            )

        subject, body, receiver, compose_hints = _parse_email_request(request)
        field_sources = compose_hints.get("field_sources") if isinstance(compose_hints, dict) else {}
        explicit_body = bool(isinstance(field_sources, dict) and field_sources.get("body") in {"metadata", "json"})
        attachments = compose_hints.get("attachments") if isinstance(compose_hints, dict) else []
        memory_refs = compose_hints.get("memory_refs") if isinstance(compose_hints, dict) else []
        request_attachment_display_names = _extract_request_attachment_display_names(request)
        attachment_paths = _dedupe_path_list(_extract_attachment_paths(attachments) + _extract_request_attachment_paths(request))
        require_rich_body = _needs_rich_body(raw_input)
        body_generated_by_llm = False
        explicitly_named_receivers = _user_explicitly_named_receivers(raw_input)

        attachment_paths, attachment_error = _resolve_special_attachments(raw_input, attachment_paths)
        if attachment_error:
            return AgentResponse(
                content=f"我先拦截了这次发送：{attachment_error}",
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "attachment_resolution_failed",
                        "attachment_count": len(attachment_paths),
                        "memory_ref_count": len(memory_refs),
                    },
                },
            )
        attachment_names = [_display_attachment_name(item, request_attachment_display_names) for item in attachment_paths]
        is_physical_exam_email = _is_physical_exam_email(raw_input, attachment_paths)
        if is_physical_exam_email:
            subject = _PHYSICAL_EXAM_FIXED_SUBJECT
            body = _PHYSICAL_EXAM_FIXED_BODY
            body_generated_by_llm = False
            explicit_body = True

        if _is_mail_history_query(raw_input):
            return AgentResponse(
                content=(
                    "我目前只能代你发送邮件，还不能直接读取邮箱‘已发送’列表。\n"
                    "你可以这样说：‘发给谁、主题是什么、要点是什么’，我就能立刻代发。"
                ),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "history_query_not_supported",
                    },
                },
            )

        if not receiver:
            receiver = ", ".join(_extract_receivers_from_text(raw_input)) or None

        receivers, contact_metrics = _resolve_receivers_from_contacts(receiver=receiver, raw_input=raw_input)

        llm_adapter_used = False
        llm_body_refiner_used = False
        if not receivers or not subject or not body:
            adapted = _adapt_email_request_with_llm(request, model_name=skill_model)
            if adapted:
                llm_adapter_used = True
                if not receivers:
                    receiver = str(adapted.get("receiver") or "").strip() or None
                if not subject:
                    subject = str(adapted.get("subject") or "").strip()
                if not body:
                    body = str(adapted.get("body") or "").strip()
                    body_generated_by_llm = bool(body)

        # LLM 可能回填人名而非邮箱，这里再次做联系人查转兜底。
        receivers, post_adapter_contact_metrics = _resolve_receivers_from_contacts(receiver=receiver, raw_input=raw_input)
        if post_adapter_contact_metrics.get("contact_resolved") or receivers:
            contact_metrics = post_adapter_contact_metrics

        generic_audience_request = _is_generic_audience_request(receiver=receiver, raw_input=raw_input)
        if generic_audience_request and not explicitly_named_receivers:
            all_contact_receivers = _resolve_all_contact_emails()
            if all_contact_receivers:
                receivers = all_contact_receivers
                contact_metrics = {
                    **contact_metrics,
                    "contact_resolved": True,
                    "contact_match": "all_contacts",
                    "contact_names": [str(contact.get("name") or "").strip() for contact in _load_contacts() if str(contact.get("name") or "").strip()],
                    "unresolved_receivers": [],
                    "all_contacts_selected": True,
                }

        if not receivers:
            return AgentResponse(
                content=_build_missing_receiver_tip(),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "missing_receiver",
                        "receiver": receiver,
                        "receivers": receivers,
                        "llm_adapter_used": llm_adapter_used,
                        "llm_adapter_model": skill_model,
                        "llm_body_refiner_used": llm_body_refiner_used,
                        "attachment_count": len(attachment_paths),
                        "attachments": attachment_paths,
                        "memory_ref_count": len(memory_refs),
                        "implementation_hint": "大模型互联网搜索",
                        **contact_metrics,
                    },
                },
            )

        body_quality_blocked = False
        should_refine_generated_body = bool(subject and body and body_generated_by_llm and not explicit_body)
        if subject and body and (
            should_refine_generated_body
            or _is_low_quality_body(
                body,
                raw_input,
                subject=subject,
                explicit_body=explicit_body,
                require_rich_body=require_rich_body,
            )
        ):
            refined_body = _refine_email_body_with_llm(
                subject=subject,
                body=body,
                raw_input=raw_input,
                model_name=skill_model,
                require_rich_body=require_rich_body,
            )
            if refined_body:
                body = refined_body
                llm_body_refiner_used = True
            else:
                body_quality_blocked = _is_low_quality_body(
                    body,
                    raw_input,
                    subject=subject,
                    explicit_body=explicit_body,
                    require_rich_body=require_rich_body,
                ) or should_refine_generated_body

        if body_quality_blocked:
            return AgentResponse(
                content=(
                    "我先拦截了这次发送：当前正文看起来还是指令原文，直接发出会是空内容邮件。\n"
                    "请再补一句你希望邮件里出现的要点，或让我继续展开后再发送。"
                ),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "low_quality_body_blocked",
                        "receiver": "，".join(receivers),
                        "receivers": receivers,
                        "attachments": attachment_paths,
                        "subject": subject,
                        "llm_adapter_used": llm_adapter_used,
                        "llm_adapter_model": skill_model,
                        "llm_body_refiner_used": llm_body_refiner_used,
                        "implementation_hint": "大模型互联网搜索",
                        **contact_metrics,
                    },
                },
            )

        if not subject or not body:
            return AgentResponse(
                content=_build_usage_tip(),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "missing_subject_or_body",
                        "receiver": "，".join(receivers),
                        "receivers": receivers,
                        "llm_adapter_used": llm_adapter_used,
                        "llm_adapter_model": skill_model,
                        "llm_body_refiner_used": llm_body_refiner_used,
                        "attachment_count": len(attachment_paths),
                        "attachments": attachment_paths,
                        "memory_ref_count": len(memory_refs),
                        "implementation_hint": "大模型互联网搜索",
                        **contact_metrics,
                    },
                },
            )

        base_metrics = {
            "llm_adapter_used": llm_adapter_used,
            "llm_adapter_model": skill_model,
            "llm_body_refiner_used": llm_body_refiner_used,
            "attachment_count": len(attachment_paths),
            "attachments": attachment_paths,
            "memory_ref_count": len(memory_refs),
            "implementation_hint": "大模型互联网搜索",
            "receiver_display": "已收录的各位领导同事" if not explicitly_named_receivers else "，".join(receivers),
            "attachment_names": attachment_names,
            **contact_metrics,
        }
        pending_saved = save_pending_email_confirmation(
            request.session_id,
            {
                "receivers": receivers,
                "subject": subject,
                "body": body,
                "attachments": attachment_paths,
                "attachment_names": attachment_names,
                "receiver_display": str(base_metrics.get("receiver_display") or "").strip(),
                "base_metrics": base_metrics,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
        )
        if not pending_saved:
            return AgentResponse(
                content=(
                    "我编好内容了，但当前会话没法保存二次确认状态，先没有继续发送。\n"
                    "请在同一会话里重试一次。"
                ),
                metrics={
                    "skill": self.name,
                    "send_email": {
                        "ok": False,
                        "reason": "confirmation_state_unavailable",
                        "receiver": "，".join(receivers),
                        "receivers": receivers,
                        "attachments": attachment_paths,
                        "subject": subject,
                        **base_metrics,
                        "confirmation_required": True,
                    },
                },
            )

        return AgentResponse(
            content=_build_receiver_confirmation_prompt(
                receivers,
                receiver_display=str(base_metrics.get("receiver_display") or "").strip() or None,
                attachment_names=attachment_names,
            ),
            metrics={
                "skill": self.name,
                "send_email": {
                    "ok": False,
                    "reason": "confirmation_pending",
                    "receiver": "，".join(receivers),
                    "receivers": receivers,
                    "attachments": attachment_paths,
                    "subject": subject,
                    **base_metrics,
                    "confirmation_required": True,
                },
            },
        )
