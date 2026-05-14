/* 记录页脚本：按日期分组展示记录，并支持重点筛选与关键词搜索。 */

(function () {
  const dataNode = document.getElementById("journalRecordsData");
  const tabsWrap = document.getElementById("journalTabs");
  const groupedList = document.getElementById("journalGroupedList");
  const noResultText = document.getElementById("journalNoResultText");
  const searchInput = document.getElementById("journalSearchInput");

  if (!dataNode || !tabsWrap || !groupedList || !noResultText || !searchInput) {
    return;
  }

  let rows = [];
  try {
    rows = JSON.parse(dataNode.textContent || "[]");
  } catch (error) {
    rows = [];
  }

  const tabs = Array.from(tabsWrap.querySelectorAll(".journal-tab"));
  let activeFilter = "all";
  let activeKeyword = "";

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const escapeHtml = (text) =>
    String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const parseDate = (dateText) => {
    const text = String(dateText || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) {
      return null;
    }
    const dt = new Date(`${text}T00:00:00`);
    if (Number.isNaN(dt.getTime())) {
      return null;
    }
    return dt;
  };

  const isFocus = (row) => {
    const emotion = String(row.emotion || "");
    const risk = String(row.risk_level || "");
    return Boolean(row.is_focus) || risk === "高风险" || risk === "中高风险" || ["危机状态", "高压状态", "重点关注"].includes(emotion);
  };

  const riskBadge = (riskLevel) => {
    const text = String(riskLevel || "未知");
    if (text === "高风险") {
      return '<span class="risk-pill risk-high">高风险</span>';
    }
    if (text === "中风险" || text === "中高风险") {
      return `<span class="risk-pill risk-mid">${escapeHtml(text)}</span>`;
    }
    if (text === "低风险") {
      return '<span class="risk-pill risk-low">低风险</span>';
    }
    return `<span class="risk-pill risk-unknown">${escapeHtml(text)}</span>`;
  };

  const getGroupMeta = (groupRows) => {
    const highRisk = groupRows.some((row) => row.risk_level === "高风险" || ["危机状态", "重点关注"].includes(row.emotion));
    const highPressure = groupRows.some((row) => ["高压状态", "重点关注"].includes(row.emotion));
    const midCount = groupRows.filter((row) => row.risk_level === "中风险").length;

    if (highRisk) {
      return { status: "重点关注", weather: "暴雨预警" };
    }
    if (highPressure || midCount >= 2) {
      return { status: "有压力", weather: "小雨" };
    }
    if (midCount > 0) {
      return { status: "有压力", weather: "多云" };
    }
    return { status: "平稳", weather: "晴" };
  };

  const resolveGroupInfo = (dateKey) => {
    const dateObj = parseDate(dateKey);
    if (!dateObj) {
      return { label: "更早", key: "older", expanded: false, rank: 999999 };
    }

    const diffDays = Math.floor((today - dateObj) / (24 * 60 * 60 * 1000));
    if (diffDays === 0) {
      return { label: "今天", key: "today", expanded: true, rank: 0 };
    }
    if (diffDays === 1) {
      return { label: "昨天", key: "yesterday", expanded: false, rank: 1 };
    }
    if (diffDays > 30) {
      return { label: "更早", key: "older", expanded: false, rank: 999999 - diffDays };
    }
    return { label: dateKey, key: dateKey, expanded: false, rank: diffDays };
  };

  const matchesFilter = (row) => {
    if (activeFilter === "all") {
      return true;
    }
    if (activeFilter === "focus") {
      return isFocus(row);
    }
    return String(row.filter_group || "") === activeFilter;
  };

  const matchesSearch = (row) => {
    if (!activeKeyword) {
      return true;
    }
    const haystack = [
      row.emotion,
      row.risk_level,
      row.suggestion,
      row.suggestion_full,
      row.input_type,
      row.input_type_key,
      row.time,
    ]
      .map((item) => String(item || "").toLowerCase())
      .join(" ");
    return haystack.includes(activeKeyword);
  };

  const renderRecordCard = (row) => {
    const confidenceHtml = row.confidence
      ? `<p><strong>置信度：</strong>${escapeHtml(row.confidence)}</p>`
      : "";
    const sourceHtml = row.source
      ? `<p><strong>回复来源：</strong>${escapeHtml(row.source)}</p>`
      : "";

    return `
      <article class="journal-record-item">
        <div class="journal-item-head">
          <p class="journal-time">${escapeHtml(row.time_short || "--:--")}</p>
          ${riskBadge(row.risk_level)}
        </div>
        <p class="journal-main">${escapeHtml(row.icon || "📔")} ${escapeHtml(row.input_type || "其他")} · ${escapeHtml(row.emotion || "未知")}</p>
        <p class="journal-sub">${escapeHtml(row.suggestion || "继续按自己的节奏慢慢来。")}</p>
        <details class="journal-details">
          <summary>查看详情</summary>
          <div class="journal-details-body">
            <p><strong>完整建议：</strong>${escapeHtml(row.suggestion_full || "继续按自己的节奏慢慢来。")}</p>
            <p><strong>输入类型：</strong>${escapeHtml(row.input_type || "其他")}</p>
            ${confidenceHtml}
            ${sourceHtml}
            <p><strong>时间：</strong>${escapeHtml(row.time || "")}</p>
          </div>
        </details>
      </article>
    `;
  };

  const renderGroup = (groupItem) => {
    const meta = getGroupMeta(groupItem.rows);
    const detailsAttr = groupItem.info.expanded ? "open" : "";
    const cardsHtml = groupItem.rows.map(renderRecordCard).join("");

    return `
      <details class="journal-group" ${detailsAttr}>
        <summary class="journal-group-head">
          <span class="journal-group-title">${escapeHtml(groupItem.info.label)}</span>
          <span class="journal-group-meta">${groupItem.rows.length} 条 · ${escapeHtml(meta.status)} · ${escapeHtml(meta.weather)}</span>
        </summary>
        <div class="journal-group-body">
          ${cardsHtml}
        </div>
      </details>
    `;
  };

  const render = () => {
    tabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.filter === activeFilter));

    const filtered = rows.filter((row) => matchesFilter(row) && matchesSearch(row));
    if (!filtered.length) {
      groupedList.innerHTML = "";
      noResultText.hidden = false;
      return;
    }

    noResultText.hidden = true;

    const groupsMap = new Map();
    filtered.forEach((row) => {
      const info = resolveGroupInfo(row.date_key || "");
      const key = info.key;
      if (!groupsMap.has(key)) {
        groupsMap.set(key, { info, rows: [] });
      }
      groupsMap.get(key).rows.push(row);
    });

    const groups = Array.from(groupsMap.values()).sort((a, b) => a.info.rank - b.info.rank);
    groupedList.innerHTML = groups.map(renderGroup).join("");
    Array.from(groupedList.querySelectorAll(".journal-group")).forEach((group, index) => {
      group.style.setProperty("--group-delay", `${index * 0.05}s`);
      group.classList.add("is-animated");
    });
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      activeFilter = tab.dataset.filter || "all";
      render();
    });
  });

  searchInput.addEventListener("input", () => {
    activeKeyword = String(searchInput.value || "").trim().toLowerCase();
    render();
  });

  render();
})();
