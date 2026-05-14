"""功能模块：封装具体业务能力，供路由层调用。"""

import json
import os
from typing import Any

from flask import current_app, has_app_context


FALLBACK_RESPONSE = {
    "reply": "",
    "llm_emotion": "",
    "llm_intent": "",
    "llm_reason": "",
    "source": "mimo",
    "warning": "",
}


def _get_setting(name: str, default: Any = ""):
    if has_app_context():
        return current_app.config.get(name, default)
    return os.getenv(name, default)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _format_recent_history(recent_history):
    if not isinstance(recent_history, list):
        return ""
    lines = []
    for item in recent_history[-6:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = _normalize_text(item.get("content", ""))
        if not content:
            continue
        role_cn = "用户" if role == "user" else "AI"
        lines.append(f"{role_cn}: {content}")
    return "\n".join(lines)


def _extract_text_from_response(content_obj):
    if isinstance(content_obj, str):
        return content_obj
    if isinstance(content_obj, list):
        chunks = []
        for item in content_obj:
            if isinstance(item, dict):
                text_part = item.get("text") or item.get("content")
                if text_part:
                    chunks.append(str(text_part))
            elif isinstance(item, str):
                chunks.append(item)
        return "\n".join(chunks)
    return str(content_obj or "")


def _extract_json_string(raw_text):
    text = str(raw_text or "").strip()
    if not text:
        return ""

    text = text.replace("```json", "```").replace("```JSON", "```").strip()

    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return text


def _try_load_json(json_text):
    return json.loads(json_text)


def _safe_parse_json(raw_text):
    json_text = _extract_json_string(raw_text)
    if not json_text:
        return None, ""

    # 尝试直接按 JSON 解析。
    try:
        data = _try_load_json(json_text)
        if isinstance(data, dict):
            return data, ""
    except Exception:
        pass

    # 兼容模型偶发的中文标点/引号输出。
    normalized = (
        json_text.replace("：", ":")
        .replace("，", ",")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    try:
        data = _try_load_json(normalized)
        if isinstance(data, dict):
            return data, ""
    except Exception:
        pass

    return None, ""


def _build_prompt(user_text, emotion_result, risk_result, recent_history_text):
    local_emotion = str((emotion_result or {}).get("emotion_cn", "中性") or "中性")
    local_risk = str((risk_result or {}).get("risk_level", "中风险") or "中风险")
    local_score = str((risk_result or {}).get("risk_score", "") or "")

    system_prompt = (
        "你是“心晴陪伴”App 里的 AI 情绪陪伴助手。\n"
        "你只返回一个 JSON 对象，不要输出 Markdown、代码块、解释或多余文字。\n\n"
        "你说话要像一个温和、靠谱、关系比较近的朋友。不要像客服，不要像心理咨询报告，不要像官方通知。\n"
        "回复要自然、短一点，有人味，贴着用户刚才说的话回应。\n\n"
        "回复风格：\n"
        "- 70到130字；\n"
        "- 多用短句；\n"
        "- 少用套话；\n"
        "- 不要总是用“我理解你”“我能感受到”开头；\n"
        "- 不要说教，不要灌鸡汤；\n"
        "- 不要说“作为AI”；\n"
        "- 不要医疗化，不要出现“治疗、诊断、心理疾病、患者”等词；\n"
        "- 不要承诺解决问题；\n"
        "- 给建议时只给一个很小的下一步；\n"
        "- 最后可以问一个轻一点的问题，但不要每次都问。\n\n"
        "如果用户是普通压力：自然安抚 + 一个小步骤。\n"
        "如果用户是高压表达：先稳住情绪 + 提醒先确认安全 + 建议联系可信任的人 + 再给一个很小的下一步。\n"
        "如果本地风险等级是高风险但不是明确危机词：语气要更谨慎，不要轻描淡写。\n"
        "明确危机词由本地安全机制处理，你只处理非危机的普通压力和高压表达。\n\n"
        "JSON 格式必须严格如下：\n"
        "{\n"
        '  "reply": "给用户看的自然陪伴式回复",\n'
        '  "llm_emotion": "从以下选一个：积极、平静、焦虑、难过、愤怒、疲惫、高压状态、中性",\n'
        '  "llm_intent": "从以下选一个：倾诉、求建议、表达压力、表达疲惫、表达愤怒、重点关注、普通聊天",\n'
        '  "llm_reason": "一句话说明判断依据，40字以内"\n'
        "}\n\n"
        "只能返回 JSON，不要返回 JSON 以外的任何内容。"
    )

    user_prompt = (
        f"用户输入：{user_text}\n"
        f"本地识别情绪：{local_emotion}\n"
        f"本地风险等级：{local_risk}\n"
        f"本地风险分数：{local_score}\n"
        f"最近对话：\n{recent_history_text or '（无）'}\n"
        "请严格返回 JSON。"
    )
    return system_prompt, user_prompt


def _sanitize_reply(reply_text):
    text = str(reply_text or "").strip()
    if len(text) > 170:
        return text[:170]
    return text


def _build_photo_prompt(photo_result, risk_result, recent_history_text):
    emotion_cn = str((photo_result or {}).get("emotion_cn", "平静") or "平静")
    emotion = str((photo_result or {}).get("emotion", "neutral") or "neutral")
    confidence = float((photo_result or {}).get("confidence", 0) or 0)
    risk_level = str((risk_result or {}).get("risk_level", "低风险") or "低风险")
    suggestion = str((risk_result or {}).get("suggestion", "") or "")
    confidence_text = f"{confidence * 100:.1f}%"

    system_prompt = (
        "你是“心晴陪伴”App 中温柔、克制、有人味的 AI 陪伴助手。\n"
        "用户刚上传了一张自拍或照片，系统给出了一个图像情绪参考结果。\n"
        "你只能返回一个 JSON 对象，不要输出 Markdown、代码块或解释文字。\n\n"
        "要求：\n"
        "1. 不要把图像结果说得绝对；\n"
        "2. 要提醒表情不一定完全代表真实感受，结果仅作为心情记录参考；\n"
        "3. 语气温柔自然，像朋友在陪着聊；\n"
        "4. 不要说“系统检测到”“模型判断为”；\n"
        "5. 禁止医疗化表达，不要出现治疗/诊断/心理疾病；\n"
        "6. 风险偏高时语气更谨慎，提醒先确认安全并联系可信任的人；\n"
        "7. 回复 80-150 字，尽量用短句，有轻柔追问引导继续表达。\n\n"
        "JSON 格式：\n"
        "{\n"
        '  "reply": "自然陪伴回复",\n'
        '  "llm_emotion": "积极/平静/焦虑/难过/愤怒/疲惫/高压状态/中性",\n'
        '  "llm_intent": "倾诉/求建议/表达压力/表达疲惫/表达愤怒/重点关注/普通聊天",\n'
        '  "llm_reason": "一句话说明依据，40字以内"\n'
        "}\n"
    )

    user_prompt = (
        f"图像情绪（中文）：{emotion_cn}\n"
        f"图像情绪（英文）：{emotion}\n"
        f"参考置信度：{confidence_text}\n"
        f"本地风险等级：{risk_level}\n"
        f"本地建议：{suggestion or '继续记录即可'}\n"
        f"最近会话：\n{recent_history_text or '（无）'}\n"
        "请生成一段温柔自然的陪伴回复，并严格返回 JSON。"
    )
    return system_prompt, user_prompt


def _build_voice_prompt(voice_result, risk_result, recent_history_text):
    emotion_cn = str((voice_result or {}).get("emotion_cn", "平稳") or "平稳")
    emotion = str((voice_result or {}).get("emotion", "calm") or "calm")
    confidence = float((voice_result or {}).get("confidence", 0) or 0)
    features = (voice_result or {}).get("features", {}) or {}
    duration = float(features.get("duration", 0) or 0)
    risk_level = str((risk_result or {}).get("risk_level", "低风险") or "低风险")
    suggestion = str((risk_result or {}).get("suggestion", "") or "")
    confidence_text = f"{confidence * 100:.1f}%"
    duration_text = f"{duration:.1f}秒" if duration > 0 else "未知"

    system_prompt = (
        "你是“心晴陪伴”App 中温柔、克制、有人味的 AI 陪伴助手。\n"
        "用户刚发送了一段语音，系统基于语音特征得到一个参考状态。\n"
        "你只能返回一个 JSON 对象，不要输出 Markdown、代码块或解释文字。\n\n"
        "要求：\n"
        "1. 不要把语音情绪结果说得绝对；\n"
        "2. 要提醒声音状态只是参考，真正感受以用户自身体验为准；\n"
        "3. 语气温柔自然，像朋友在陪着聊；\n"
        "4. 不要使用“系统检测到”“模型判断为”；\n"
        "5. 如果没有转写文本，不要假装知道用户具体说了什么；\n"
        "6. 禁止医疗化表达，不要出现治疗/诊断/心理疾病；\n"
        "7. 风险偏高时语气更谨慎，提醒先暂停、确认安全并联系可信任的人；\n"
        "8. 回复 80-150 字，尽量用短句，最后可轻柔追问一句。\n\n"
        "JSON 格式：\n"
        "{\n"
        '  "reply": "自然陪伴回复",\n'
        '  "llm_emotion": "积极/平静/焦虑/难过/愤怒/疲惫/高压状态/中性",\n'
        '  "llm_intent": "倾诉/求建议/表达压力/表达疲惫/表达愤怒/重点关注/普通聊天",\n'
        '  "llm_reason": "一句话说明依据，40字以内"\n'
        "}\n"
    )

    user_prompt = (
        f"语音情绪（中文）：{emotion_cn}\n"
        f"语音情绪（英文）：{emotion}\n"
        f"参考置信度：{confidence_text}\n"
        f"语音时长：{duration_text}\n"
        f"本地风险等级：{risk_level}\n"
        f"本地建议：{suggestion or '继续记录即可'}\n"
        f"语音转写：无（当前未提供 ASR 文本）\n"
        f"最近会话：\n{recent_history_text or '（无）'}\n"
        "请生成一段温柔自然的陪伴回复，并严格返回 JSON。"
    )
    return system_prompt, user_prompt


def _guess_intent_from_text(user_text):
    content = str(user_text or "")
    if any(key in content for key in ["撑不住", "顶不住", "扛不住", "受不了了", "快崩溃", "喘不过气", "我不行了"]):
        return "重点关注"
    if any(key in content for key in ["怎么办", "咋办", "怎么做"]):
        return "求建议"
    if any(key in content for key in ["压力", "崩溃", "撑不住"]):
        return "表达压力"
    if any(key in content for key in ["累", "疲惫", "不想动"]):
        return "表达疲惫"
    return "倾诉"


def _create_completion_with_retry(client, model, system_prompt, user_prompt, timeout_seconds):
    kwargs = {
        "model": model,
        "temperature": 0.5,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        return client.with_options(timeout=float(timeout_seconds)).chat.completions.create(
            response_format={"type": "json_object"},
            **kwargs,
        )
    except Exception as error:
        error_text = str(error).lower()
        should_retry_without_format = (
            "response_format" in error_text
            or "unsupported" in error_text
            or "not support" in error_text
            or "invalid parameter" in error_text
            or "invalid" in error_text
        )
        if should_retry_without_format:
            return client.with_options(timeout=float(timeout_seconds)).chat.completions.create(**kwargs)
        raise


def generate_ai_companion_reply(
    user_text, emotion_result, risk_result, recent_history=None, system_judgement="系统判断：普通情绪压力，可以进行自然陪伴式回复。"
):
    result = dict(FALLBACK_RESPONSE)

    api_key = str(_get_setting("MIMO_API_KEY", "") or "").strip()
    base_url = str(_get_setting("MIMO_BASE_URL", "") or "").strip()
    model = str(_get_setting("MIMO_MODEL", "") or "").strip()
    timeout_seconds = int(_get_setting("MIMO_TIMEOUT_SECONDS", 15) or 15)

    if not api_key or not base_url or not model:
        result["warning"] = "MiMo 配置不完整，已切换为本地模板回复。"
        return result

    try:
        from openai import OpenAI
    except Exception:
        result["warning"] = "未安装 openai SDK，已切换为本地模板回复。"
        return result

    system_prompt, user_prompt = _build_prompt(
        user_text=user_text,
        emotion_result=emotion_result,
        risk_result=risk_result,
        recent_history_text=_format_recent_history(recent_history),
    )
    user_prompt = f"{user_prompt}\n{system_judgement}\n"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = _create_completion_with_retry(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
        )
        raw_content = _extract_text_from_response(completion.choices[0].message.content)
    except Exception as error:
        result["warning"] = f"MiMo 调用失败：{error}，已切换为本地模板回复。"
        return result

    raw_reply = _sanitize_reply(raw_content)
    parsed, _ = _safe_parse_json(raw_content)

    if isinstance(parsed, dict):
        reply = _sanitize_reply(parsed.get("reply", "")) or raw_reply
        result["reply"] = reply
        result["llm_emotion"] = _normalize_text(
            parsed.get("llm_emotion", "") or (emotion_result or {}).get("emotion_cn", "")
        )
        result["llm_intent"] = _normalize_text(parsed.get("llm_intent", "") or _guess_intent_from_text(user_text))
        result["llm_reason"] = _normalize_text(
            parsed.get("llm_reason", "") or "根据用户表达和本地情绪识别结果综合判断。"
        )
        result["warning"] = ""
        if not result["reply"]:
            result["warning"] = "MiMo 返回内容为空，已切换为本地模板回复。"
        return result

    # 非 JSON 但有自然语言内容时，直接作为 MiMo 回复，不向前端暴露解析类提示。
    result["reply"] = raw_reply
    result["llm_emotion"] = _normalize_text((emotion_result or {}).get("emotion_cn", ""))
    result["llm_intent"] = _guess_intent_from_text(user_text)
    result["llm_reason"] = "根据用户表达和本地情绪识别结果综合判断。"
    result["warning"] = ""

    if not result["reply"]:
        result["warning"] = "MiMo 返回内容为空，已切换为本地模板回复。"

    return result


def generate_photo_companion_reply(photo_result, risk_result, user_context=None):
    result = dict(FALLBACK_RESPONSE)

    api_key = str(_get_setting("MIMO_API_KEY", "") or "").strip()
    base_url = str(_get_setting("MIMO_BASE_URL", "") or "").strip()
    model = str(_get_setting("MIMO_MODEL", "") or "").strip()
    timeout_seconds = int(_get_setting("MIMO_TIMEOUT_SECONDS", 15) or 15)

    if not api_key or not base_url or not model:
        result["warning"] = "MiMo 配置不完整，已切换为本地模板回复。"
        return result

    try:
        from openai import OpenAI
    except Exception:
        result["warning"] = "未安装 openai SDK，已切换为本地模板回复。"
        return result

    system_prompt, user_prompt = _build_photo_prompt(
        photo_result=photo_result,
        risk_result=risk_result,
        recent_history_text=_format_recent_history(user_context),
    )

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = _create_completion_with_retry(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
        )
        raw_content = _extract_text_from_response(completion.choices[0].message.content)
    except Exception as error:
        result["warning"] = f"MiMo 调用失败：{error}，已切换为本地模板回复。"
        return result

    raw_reply = _sanitize_reply(raw_content)
    parsed, _ = _safe_parse_json(raw_content)

    if isinstance(parsed, dict):
        result["reply"] = _sanitize_reply(parsed.get("reply", "")) or raw_reply
        result["llm_emotion"] = _normalize_text(parsed.get("llm_emotion", "") or (photo_result or {}).get("emotion_cn", ""))
        result["llm_intent"] = _normalize_text(parsed.get("llm_intent", "") or "普通聊天")
        result["llm_reason"] = _normalize_text(
            parsed.get("llm_reason", "") or "结合图像参考结果与风险等级生成。"
        )
        result["warning"] = ""
        if not result["reply"]:
            result["warning"] = "MiMo 返回内容为空，已切换为本地模板回复。"
        return result

    result["reply"] = raw_reply
    result["llm_emotion"] = _normalize_text((photo_result or {}).get("emotion_cn", "中性"))
    result["llm_intent"] = "普通聊天"
    result["llm_reason"] = "结合图像参考结果与风险等级生成。"
    result["warning"] = ""
    if not result["reply"]:
        result["warning"] = "MiMo 返回内容为空，已切换为本地模板回复。"
    return result


def generate_voice_companion_reply(voice_result, risk_result, user_context=None):
    result = dict(FALLBACK_RESPONSE)

    api_key = str(_get_setting("MIMO_API_KEY", "") or "").strip()
    base_url = str(_get_setting("MIMO_BASE_URL", "") or "").strip()
    model = str(_get_setting("MIMO_MODEL", "") or "").strip()
    timeout_seconds = int(_get_setting("MIMO_TIMEOUT_SECONDS", 15) or 15)

    if not api_key or not base_url or not model:
        result["warning"] = "MiMo 配置不完整，已切换为本地模板回复。"
        return result

    try:
        from openai import OpenAI
    except Exception:
        result["warning"] = "未安装 openai SDK，已切换为本地模板回复。"
        return result

    system_prompt, user_prompt = _build_voice_prompt(
        voice_result=voice_result,
        risk_result=risk_result,
        recent_history_text=_format_recent_history(user_context),
    )

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = _create_completion_with_retry(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
        )
        raw_content = _extract_text_from_response(completion.choices[0].message.content)
    except Exception as error:
        result["warning"] = f"MiMo 调用失败：{error}，已切换为本地模板回复。"
        return result

    raw_reply = _sanitize_reply(raw_content)
    parsed, _ = _safe_parse_json(raw_content)

    if isinstance(parsed, dict):
        result["reply"] = _sanitize_reply(parsed.get("reply", "")) or raw_reply
        result["llm_emotion"] = _normalize_text(parsed.get("llm_emotion", "") or (voice_result or {}).get("emotion_cn", ""))
        result["llm_intent"] = _normalize_text(parsed.get("llm_intent", "") or "普通聊天")
        result["llm_reason"] = _normalize_text(
            parsed.get("llm_reason", "") or "结合语音参考结果与风险等级生成。"
        )
        result["warning"] = ""
        if not result["reply"]:
            result["warning"] = "MiMo 返回内容为空，已切换为本地模板回复。"
        return result

    result["reply"] = raw_reply
    result["llm_emotion"] = _normalize_text((voice_result or {}).get("emotion_cn", "中性"))
    result["llm_intent"] = "普通聊天"
    result["llm_reason"] = "结合语音参考结果与风险等级生成。"
    result["warning"] = ""
    if not result["reply"]:
        result["warning"] = "MiMo 返回内容为空，已切换为本地模板回复。"
    return result
