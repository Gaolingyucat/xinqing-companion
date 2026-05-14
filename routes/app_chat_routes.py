"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request

from modules.companion_reply import generate_companion_reply
from modules.llm_advisor import generate_ai_companion_reply
from modules.record_manager import add_record
from modules.risk_engine import evaluate_text_risk
from modules.text_emotion import analyze_text


app_chat_bp = Blueprint("app_chat", __name__)


CRISIS_TERMS = ["不想活", "想死", "自杀", "伤害自己", "结束一切", "活不下去", "结束生命", "不想继续活", "想消失", "不如死了"]
HIGH_PRESSURE_TERMS = [
    "撑不住",
    "顶不住",
    "扛不住",
    "受不了了",
    "快崩溃了",
    "崩溃了",
    "坚持不下去",
    "熬不下去",
    "太痛苦了",
    "好绝望",
    "没希望了",
    "快疯了",
    "喘不过气",
    "压得我喘不过气",
    "不知道怎么办",
    "真的好累",
    "身心俱疲",
    "我不行了",
]
UNSAFE_LLM_TERMS = [
    "治疗",
    "确诊",
    "心理疾病",
    "保证你会",
    "一定会彻底好",
    "不需要任何专业帮助",
    "我可以替代",
    "替代心理咨询",
    "取代心理咨询",
]


def _contains_crisis_terms(text):
    content = str(text or "")
    return any(term in content for term in CRISIS_TERMS)


def _contains_unsafe_llm_content(text):
    content = str(text or "")
    return any(term in content for term in UNSAFE_LLM_TERMS)


def _contains_high_pressure_terms(text):
    content = str(text or "")
    return any(term in content for term in HIGH_PRESSURE_TERMS)


def _build_crisis_reply():
    return (
        "我很担心你现在的状态。请先把自己放到安全的位置，马上联系身边可信任的人，比如朋友、家人、老师或辅导员。"
        "如果你已经有伤害自己的冲动，请立刻拨打当地紧急电话，或前往最近的急诊/求助点。你不需要一个人扛着这件事。"
    )


@app_chat_bp.route("/app/chat", methods=["GET"])
def app_chat_page():
    return render_template("app_chat.html", nav_active="chat")


@app_chat_bp.route("/app/chat/send", methods=["POST"])
def app_chat_send():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "") or "").strip()
    conversation_history = payload.get("conversation_history")

    if not message:
        return jsonify({"ok": False, "error": "请输入想倾诉的内容。"}), 400

    text_result = analyze_text(message)
    risk_result = evaluate_text_risk(
        text_emotion=text_result["emotion"],
        score=text_result["text_score"],
    )

    # 先生成本地模板结果，作为 LLM 不可用时的稳定兜底。
    local_result = generate_companion_reply(
        user_text=message,
        emotion_result=text_result,
        risk_result=risk_result,
        conversation_history=conversation_history,
    )

    risk_score = int(risk_result["risk_score"])
    risk_level = risk_result["risk_level"]
    local_emotion_cn = text_result["emotion_cn"]

    final_reply = local_result["reply"]
    llm_emotion = ""
    llm_intent = local_result["intent"]
    llm_reason = ""
    source = "本地模板"
    warning = ""
    final_advice = "建议继续记录和表达感受，保持稳定节奏。"
    system_judgement = "系统判断：普通情绪压力，可以进行自然陪伴式回复。"

    # 危机词优先级最高：命中后直接走安全提醒，不调用常规回复流程。
    has_crisis = _contains_crisis_terms(message)
    has_high_pressure = _contains_high_pressure_terms(message)
    if has_crisis:
        risk_score = 100
        risk_level = "高风险"
        local_emotion_cn = "危机状态"
        final_reply = _build_crisis_reply()
        llm_emotion = "高压危机表达"
        llm_intent = "危机求助"
        llm_reason = "检测到高风险表达，系统优先触发本地安全提醒。"
        source = "本地安全机制"
        warning = ""
        final_advice = (
            "请先确保自己处在安全位置，尽快联系身边可信任的人；"
            "如果已有伤害自己的冲动，请立即拨打当地紧急电话或前往最近的急诊/求助点。"
        )
    else:
        if has_high_pressure:
            risk_score = max(risk_score, 75)
            risk_level = "高风险"
            local_emotion_cn = "高压状态"
            llm_emotion = "高压状态"
            llm_intent = "重点关注"
            llm_reason = "用户表达出强烈压力和难以承受的状态，需要重点关注。"
            final_advice = (
                "建议先暂停当前任务，确认自己此刻是否安全，并尽快联系一位可信任的人说说现在的状态。"
                "如果这种感觉继续加重，请及时寻求现实中的帮助。"
            )
            system_judgement = (
                "系统判断：用户出现高压表达，属于重点关注状态。"
                "回复时要更谨慎，先稳定情绪，不要轻描淡写，并建议联系可信任的人。"
            )

        enable_llm = bool(current_app.config.get("ENABLE_LLM_ADVISOR", False))
        if enable_llm:
            # 开启 LLM 时优先请求 MiMo；若失败或内容不合规则自动回退本地模板。
            llm_result = generate_ai_companion_reply(
                user_text=message,
                emotion_result=text_result,
                risk_result=risk_result,
                recent_history=conversation_history,
                system_judgement=system_judgement,
            )
            llm_reply = str(llm_result.get("reply", "") or "").strip()
            llm_warning = str(llm_result.get("warning", "") or "").strip()

            if llm_reply and not _contains_unsafe_llm_content(llm_reply):
                final_reply = llm_reply
                llm_emotion = str(llm_result.get("llm_emotion", "") or "")
                llm_intent = str(llm_result.get("llm_intent", "") or llm_intent)
                llm_reason = str(llm_result.get("llm_reason", "") or llm_reason)
                source = "MiMo AI"
                warning = llm_warning
            else:
                source = "本地模板"
                warning = "已切换为本地模板回复"
                if llm_warning:
                    warning = f"已切换为本地模板回复：{llm_warning}"
        else:
            source = "本地模板"

    if not has_crisis and not has_high_pressure:
        if risk_level == "高风险":
            final_advice = "建议先暂停当前任务，并尽快联系可信任的人、老师、朋友或专业支持。"
        elif risk_level == "中风险":
            final_advice = "建议短暂休息并拆解压力，先完成一个5分钟小步骤。"

    if has_high_pressure:
        llm_emotion = "高压状态"
        llm_intent = "重点关注"
        if not llm_reason:
            llm_reason = "用户表达出强烈压力和难以承受的状态，需要重点关注。"

    add_record(
        csv_path=Path(current_app.root_path) / "data" / "records.csv",
        input_type="app_chat",
        emotion=text_result["emotion"],
        emotion_cn=local_emotion_cn,
        confidence=text_result["text_score"] / 100,
        risk_score=risk_score,
        risk_level=risk_level,
        suggestion=final_advice,
        file_path="app_chat_input",
    )

    return jsonify(
        {
            "ok": True,
            "reply": final_reply,
            "local_emotion_cn": local_emotion_cn,
            "emotion_cn": local_emotion_cn,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "llm_emotion": llm_emotion,
            "llm_intent": llm_intent,
            "llm_reason": llm_reason,
            "advice": final_advice,
            "source": source,
            "warning": warning,
        }
    )
