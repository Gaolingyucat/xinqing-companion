"""功能模块：封装具体业务能力，供路由层调用。"""

CRISIS_TERMS = [
    "不想活",
    "不想活了",
    "想死",
    "伤害自己",
    "结束一切",
    "活不下去",
]


INTENT_KEYWORDS = {
    "asking_advice": ["怎么办", "我该怎么办", "怎么缓解", "怎么处理", "该怎么做", "怎么调整"],
    "stress": ["压力大", "压力好大", "撑不住", "扛不住", "好崩溃", "快崩溃", "顶不住"],
    "anger": ["很烦", "烦死", "生气", "火大", "愤怒", "气死"],
    "tired": ["好累", "心累", "太累", "疲惫", "没精神", "不想动"],
    "venting": ["想说说", "好难受", "委屈", "心里堵", "压抑", "不知道和谁说"],
}


def _normalize_text(text):
    return " ".join(str(text or "").strip().replace("\n", " ").split())


def _contains_any(text, keywords):
    content = str(text or "")
    return any(word in content for word in keywords)


def _detect_intent(user_text, emotion_key):
    content = str(user_text or "")

    if _contains_any(content, INTENT_KEYWORDS["asking_advice"]):
        return "asking_advice"
    if _contains_any(content, INTENT_KEYWORDS["stress"]):
        return "stress"
    if _contains_any(content, INTENT_KEYWORDS["anger"]) or emotion_key == "angry":
        return "anger"
    if _contains_any(content, INTENT_KEYWORDS["tired"]) or emotion_key == "tired":
        return "tired"
    if _contains_any(content, INTENT_KEYWORDS["venting"]) or emotion_key in {"negative", "anxious"}:
        return "venting"
    return "neutral"


def _extract_focus_text(user_text):
    normalized = _normalize_text(user_text)
    if len(normalized) <= 26:
        return normalized
    return f"{normalized[:26]}..."


def _get_last_ai_reply(conversation_history):
    if not isinstance(conversation_history, list):
        return ""
    for item in reversed(conversation_history[-10:]):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).lower()
        if role in {"ai", "assistant"}:
            return _normalize_text(item.get("content", ""))
    return ""


def _pick_line(options, seed_value, avoid_text=""):
    if not options:
        return ""
    index = seed_value % len(options)
    line = options[index]
    if avoid_text and line in avoid_text and len(options) > 1:
        line = options[(index + 1) % len(options)]
    return line


def _build_empathy_line(intent, risk_level, seed_value, last_ai_reply):
    if risk_level == "高风险":
        options = [
            "我能感觉到你现在正承受很重的情绪压力。",
            "听到你这样说，我知道你现在一定很不好受。",
            "你现在的状态让我很担心，也很想先陪你稳住当下。",
        ]
        return _pick_line(options, seed_value, last_ai_reply)

    options_map = {
        "asking_advice": [
            "你愿意主动问“怎么办”，说明你已经在努力找出口了。",
            "你现在在认真想办法，这本身就是很重要的一步。",
            "能看出来你很想把局面稳下来，我们可以一起拆开它。",
        ],
        "stress": [
            "我听见你在说“压力扛得很吃力”，这种感觉真的很累人。",
            "你现在像一直顶着很重的负担，难受是很真实的。",
            "长期被压力推着走会很消耗，你现在的反应很正常。",
        ],
        "anger": [
            "你现在的烦和火气很明显，我能理解这种被卡住的感觉。",
            "这股情绪来得很猛，先别急着否定自己。",
            "听起来你现在真的很上火，先把自己放在第一位。",
        ],
        "tired": [
            "你已经撑了很久，累到这种程度很让人心疼。",
            "这种心累和没力气的状态，很多人都会经历。",
            "你现在像是电量见底了，先照顾自己最重要。",
        ],
        "venting": [
            "把这些说出来很不容易，你已经做得很好。",
            "你愿意把感受摊开来说，是很有力量的。",
            "我在认真听你说，现在先不用急着把一切都想明白。",
        ],
        "neutral": [
            "我在这儿，会认真听你把当下说完整。",
            "我们可以慢慢聊，不需要一次把所有事都解决。",
            "先把感受说出来就很好，我陪你一起整理。",
        ],
    }
    options = options_map.get(intent, options_map["neutral"])
    return _pick_line(options, seed_value, last_ai_reply)


def _build_action_line(intent, risk_level):
    if risk_level == "高风险":
        if intent == "asking_advice":
            return "先暂停2分钟，把眼前压力写成1-3条，选最容易处理的一件先做5分钟，同时尽快联系一位可信任的人陪你一起稳住状态。"
        if intent == "stress":
            return "先停下手头事情，做三次慢呼吸，再只处理一个5分钟小步骤，并尽快联系可信任的人给你支持。"
        return "先暂停当前任务，联系一位你信任的人陪你待一会儿；如果状态持续升级，尽快联系老师、朋友或专业支持。"

    if intent == "asking_advice":
        return "先暂停2分钟，把压力源写成1-3条，选最容易处理的一件事，只做5分钟就好。"
    if intent == "stress":
        return "先做三次慢呼吸，再把当前任务拆成最小一步，只给自己一个5分钟计时。"
    if intent == "anger":
        return "先离开让你更上火的场景30秒，喝口水，再把最想说的话写下来后再决定下一步。"
    if intent == "tired":
        return "先让眼睛离开屏幕2分钟，放松肩颈，然后只做一个最轻的小任务重启节奏。"
    if intent == "venting":
        return "先把“最难受的一件事”写成一句话，再给它打个0到10分，帮助我们找到重点。"
    return "可以先用一句话记录此刻心情，再告诉我今天最想先改善的一件小事。"


def _build_open_question(intent, seed_value, last_ai_reply):
    options_map = {
        "asking_advice": [
            "你想先从哪一件最小的事开始，我可以陪你定第一步。",
            "如果只选一件你现在能动手的小事，你会选哪件？",
            "要不要先说说你最想优先解决的是哪一块？",
        ],
        "stress": [
            "这股压力现在最主要来自工作、学习，还是人际关系？",
            "你觉得现在最压着你的那一件事是什么？",
            "如果把压力拆开，第一块最重的是哪一块？",
        ],
        "anger": [
            "这次让你最上火的触发点是什么？",
            "你更想先处理情绪，还是先处理那件事本身？",
            "要不要先说说刚刚最让你受不了的一幕？",
        ],
        "tired": [
            "你现在更像是身体累，还是心里累？",
            "今天最消耗你的环节是什么？",
            "你愿意先告诉我，哪一段时间最容易崩掉吗？",
        ],
        "venting": [
            "你愿意从今天最难受的那一刻开始说起吗？",
            "如果现在给情绪起个名字，它会是什么？",
            "你此刻最希望被理解的一句话是什么？",
        ],
        "neutral": [
            "你想先聊今天发生的哪件事？",
            "现在最想被听见的是哪部分感受？",
            "我们先从你最在意的一点开始，好吗？",
        ],
    }
    options = options_map.get(intent, options_map["neutral"])
    return _pick_line(options, seed_value + 7, last_ai_reply)


def _build_reflect_line(user_text, seed_value, last_ai_reply):
    focus_text = _extract_focus_text(user_text)
    options = [
        f"听起来你现在最卡住的是“{focus_text}”。",
        f"我听到你最在意的是“{focus_text}”。",
        f"你刚刚提到的“{focus_text}”，确实会让人很有压力。",
    ]
    return _pick_line(options, seed_value + 3, last_ai_reply)


def _emotion_label(intent, emotion_cn):
    if intent == "stress":
        return "压力"
    if intent == "tired":
        return "疲惫"
    if intent == "anger":
        return "愤怒"
    return emotion_cn or "中性"


def generate_companion_reply(user_text, emotion_result, risk_result, conversation_history=None):
    content = _normalize_text(user_text)
    emotion_result = emotion_result or {}
    risk_result = risk_result or {}

    emotion_key = str(emotion_result.get("emotion", "neutral") or "neutral").lower()
    emotion_cn = str(emotion_result.get("emotion_cn", "中性") or "中性")
    risk_level = str(risk_result.get("risk_level", "中风险") or "中风险")

    is_crisis = _contains_any(content, CRISIS_TERMS)
    intent = _detect_intent(content, emotion_key)
    last_ai_reply = _get_last_ai_reply(conversation_history)
    seed_value = sum(ord(ch) for ch in content) + len(str(last_ai_reply))

    if is_crisis:
        reply = (
            "我很担心你现在的状态。"
            "请先把自己放到安全的位置，马上联系身边可信任的人；"
            "如果有伤害自己的冲动，请立即联系当地紧急求助电话或专业危机干预热线。"
        )
        return {
            "intent": "stress",
            "emotion_label": "高压危机表达",
            "reply": reply,
            "advice": "请先确保安全，并马上联系可信任的人和当地紧急帮助资源。",
            "is_crisis": True,
        }

    empathy_line = _build_empathy_line(intent, risk_level, seed_value, last_ai_reply)
    reflect_line = _build_reflect_line(content, seed_value, last_ai_reply)
    action_line = _build_action_line(intent, risk_level)
    question_line = _build_open_question(intent, seed_value, last_ai_reply)

    reply = f"{empathy_line}{reflect_line}{action_line}{question_line}"
    if last_ai_reply and _normalize_text(reply) == _normalize_text(last_ai_reply):
        question_line = _build_open_question(intent, seed_value + 11, "")
        reply = f"{empathy_line}{reflect_line}{action_line}{question_line}"

    advice = action_line
    if risk_level == "高风险":
        advice = "建议先暂停当前任务，并尽快联系可信任的人或专业支持。"
    elif risk_level == "中风险":
        advice = "建议短暂休息并拆解压力，先完成一个5分钟小步骤。"

    return {
        "intent": intent,
        "emotion_label": _emotion_label(intent, emotion_cn),
        "reply": reply,
        "advice": advice,
        "is_crisis": False,
    }
