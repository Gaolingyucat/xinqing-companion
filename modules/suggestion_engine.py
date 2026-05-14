"""功能模块：封装具体业务能力，供路由层调用。"""

def generate_suggestion(input_type, emotion_cn, risk_level, risk_score):
    if str(input_type).lower() == "text":
        if risk_level == "高风险":
            return (
                f"检测到文本情绪为{emotion_cn}，风险分数{risk_score}。"
                "建议暂停当前任务，及时寻求老师、同伴或专业资源支持。"
            )
        if risk_level == "中风险":
            return (
                f"检测到文本情绪为{emotion_cn}，风险分数{risk_score}。"
                "建议短暂休息、深呼吸，必要时与同伴沟通。"
            )
        return (
            f"检测到文本情绪为{emotion_cn}，风险分数{risk_score}。"
            "当前文本情绪较稳定，可继续观察。"
        )

    if str(input_type).lower() == "audio":
        if risk_level == "高风险":
            return (
                f"检测到语音状态为{emotion_cn}，风险分数{risk_score}。"
                "建议先暂停当前任务，进行短时放松，并主动与同伴或老师沟通当前状态。"
            )
        if risk_level == "中风险":
            return (
                f"检测到语音状态为{emotion_cn}，风险分数{risk_score}。"
                "建议短暂休息、降低连续负荷，并在稍后再次进行语音复测。"
            )
        return (
            f"检测到语音状态为{emotion_cn}，风险分数{risk_score}。"
            "当前语音状态较平稳，建议保持节奏并持续关注状态变化。"
        )

    if risk_level == "高风险":
        return (
            f"{input_type}识别结果为{emotion_cn}，风险分数{risk_score}。"
            "建议立即进行安抚沟通并联系指导老师或心理辅导资源。"
        )
    if risk_level == "中风险":
        return (
            f"{input_type}识别结果为{emotion_cn}，风险分数{risk_score}。"
            "建议短时休息、情绪记录，并在24小时内复测。"
        )
    return (
        f"{input_type}识别结果为{emotion_cn}，风险分数{risk_score}。"
        "整体状态较稳定，建议保持规律作息并持续观察。"
    )


def get_suggestion(emotion_cn, risk_level):
    score_hint = 75 if risk_level == "高风险" else 50 if risk_level == "中风险" else 20
    return generate_suggestion("语音", emotion_cn, risk_level, score_hint)
