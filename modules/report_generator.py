"""功能模块：封装具体业务能力，供路由层调用。"""

from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

from modules.record_manager import read_records


INPUT_LABELS = {
    "image": "图像识别",
    "text": "文本分析",
    "audio": "语音识别",
}


def _build_summary(stats):
    total = stats["total"]
    high = stats["high_risk"]
    mid = stats["mid_risk"]
    low = stats["low_risk"]

    if total == 0:
        return "当前暂无检测数据，本报告仅作为辅助评估模板，建议完成检测后再查看状态趋势。"
    if high >= max(mid, low) and high > 0:
        return "近期高风险记录占比较高，提示情绪波动较明显。建议关注状态变化，适当休息并减少连续高负荷任务。"
    if mid >= max(high, low) and mid > 0:
        return "近期以中风险记录为主，提示存在一定情绪压力。建议合理安排作息，减少连续高强度任务并保持沟通。"
    return "近期记录以低风险为主，整体状态相对稳定。建议继续保持当前节奏，并持续进行状态观察。"


def generate_report_data(csv_path):
    records = read_records(csv_path)
    total = len(records)

    type_counter = Counter()
    risk_counter = Counter()
    emotion_counter = Counter()

    for row in records:
        input_type = (row.get("input_type", "") or "").strip()
        risk_level = (row.get("risk_level", "") or "").strip()
        emotion_cn = (row.get("emotion_cn", "") or "").strip()
        emotion = (row.get("emotion", "") or "").strip()

        if input_type:
            type_counter[input_type] += 1
        if risk_level:
            risk_counter[risk_level] += 1
        if emotion_cn or emotion:
            emotion_counter[emotion_cn or emotion] += 1

    high_risk = risk_counter.get("高风险", 0)
    mid_risk = risk_counter.get("中风险", 0)
    low_risk = risk_counter.get("低风险", 0)
    high_risk_ratio = f"{(high_risk / total * 100):.1f}%" if total else "0.0%"

    latest_time = records[0].get("time", "") if records else ""
    most_common_emotion = emotion_counter.most_common(1)[0][0] if emotion_counter else "暂无"

    recent_records = []
    for row in records[:5]:
        raw_type = (row.get("input_type", "") or "").strip()
        recent_records.append(
            {
                "time": row.get("time", ""),
                "input_type": INPUT_LABELS.get(raw_type, raw_type or "未知类型"),
                "emotion_cn": row.get("emotion_cn", ""),
                "risk_level": row.get("risk_level", ""),
                "risk_score": row.get("risk_score", ""),
            }
        )

    stats = {
        "total": total,
        "image": type_counter.get("image", 0),
        "text": type_counter.get("text", 0),
        "audio": type_counter.get("audio", 0),
        "low_risk": low_risk,
        "mid_risk": mid_risk,
        "high_risk": high_risk,
        "high_risk_ratio": high_risk_ratio,
        "latest_time": latest_time or "暂无",
        "most_common_emotion": most_common_emotion,
    }

    return {
        "has_data": total > 0,
        "stats": stats,
        "summary": _build_summary(stats),
        "recent_records": recent_records,
    }


def save_report_html(report_data, report_dir):
    directory = Path(report_dir)
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.html"
    file_path = directory / filename

    stats = report_data["stats"]
    rows_html = ""
    for row in report_data["recent_records"]:
        rows_html += (
            "<tr>"
            f"<td>{escape(str(row.get('time', '')))}</td>"
            f"<td>{escape(str(row.get('input_type', '')))}</td>"
            f"<td>{escape(str(row.get('emotion_cn', '')))}</td>"
            f"<td>{escape(str(row.get('risk_level', '')))}</td>"
            f"<td>{escape(str(row.get('risk_score', '')))}</td>"
            "</tr>"
        )

    html_content = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>情绪状态风险评估报告</title>
  <style>
    body {{ font-family: Arial, 'Microsoft YaHei', sans-serif; margin: 28px; color: #1f2937; }}
    h1 {{ color: #1d4ed8; margin-bottom: 12px; }}
    h2 {{ color: #1e40af; margin-top: 24px; }}
    .card {{ border: 1px solid #dbeafe; border-radius: 8px; padding: 14px; background: #f8fbff; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 8px; font-size: 13px; text-align: left; }}
    th {{ background: #f1f5f9; }}
  </style>
</head>
<body>
  <h1>情绪状态风险评估报告</h1>
  <div class="card">
    <p>总检测次数：{stats['total']}</p>
    <p>图像检测次数：{stats['image']}</p>
    <p>文本检测次数：{stats['text']}</p>
    <p>语音检测次数：{stats['audio']}</p>
    <p>低风险次数：{stats['low_risk']}</p>
    <p>中风险次数：{stats['mid_risk']}</p>
    <p>高风险次数：{stats['high_risk']}</p>
    <p>高风险占比：{stats['high_risk_ratio']}</p>
    <p>最近一次检测时间：{stats['latest_time']}</p>
    <p>出现最多的情绪类别：{escape(str(stats['most_common_emotion']))}</p>
  </div>
  <h2>综合评估</h2>
  <div class="card">{escape(report_data['summary'])}</div>
  <h2>最近5条检测记录</h2>
  <table>
    <thead>
      <tr><th>时间</th><th>输入类型</th><th>中文情绪</th><th>风险等级</th><th>风险分数</th></tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</body>
</html>
"""

    file_path.write_text(html_content, encoding="utf-8")
    return filename, str(file_path)
