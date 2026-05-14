/* 通用前端脚本：处理站点基础交互行为。 */

document.addEventListener("DOMContentLoaded", () => {
  const yearNode = document.getElementById("current-year");
  if (yearNode) {
    yearNode.textContent = String(new Date().getFullYear());
  }
});
