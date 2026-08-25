# Remove Dynamic Home Background Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除首页所有图片/Canvas 动态背景并改为纯 CSS 静态黑钢渐变，同时保留五幕业务文案。

**Architecture:** 删除首页舞台层与滚动运行时，五幕恢复普通文档流。源渲染资产保留在仓库，构建脚本明确排除它们，浏览器测试以“零动态资产请求”为发布契约。

**Tech Stack:** HTML、CSS、原生 JavaScript、Python unittest、Playwright、Bash

---

### Task 1: Establish Static-Home Contracts

**Files:**
- Modify: `tests/home_ui_contract_test.py`
- Modify: `tests/build_ui_contract_test.py`
- Modify: `tests/e2e/site.spec.js`
- Modify: `tests/e2e/fallbacks.spec.js`

- [ ] 将首页契约改为断言不存在 `company-stage`、`picture`、`canvas`、`data-manifest` 与 `company-scrolly.js`，五个可读 `article` 仍存在。
- [ ] 将构建契约改为要求 `_site` 排除 `assets/scrolly/v2` 和 `js/company-scrolly.js`。
- [ ] 将浏览器契约改为桌面/手机均不请求 `/assets/scrolly/v2/`，五幕可见、无横向溢出；无 JS、Reduced Motion 与 Save-Data 仍可读。
- [ ] 运行上述测试并确认因旧动态实现仍存在而失败。

### Task 2: Remove Dynamic Markup and Runtime

**Files:**
- Modify: `index.html`
- Modify: `css/home.css`
- Modify: `scripts/build-site.sh`
- Modify: `.github/workflows/deploy.yml`
- Modify: `.github/workflows/pages.yml`
- Delete: `tests/company_scrolly_runtime_test.js`

- [ ] 删除 `company-stage` 与首页滚动运行时引用，保留五幕语义 HTML。
- [ ] 把 `company-scrolly` 和 `company-steps` 改为静态渐变、普通文档流与响应式留白。
- [ ] 构建时删除 `assets/scrolly/v2` 和 `js/company-scrolly.js`，工作流停止运行已删除的运行时测试。
- [ ] 删除仅验证旧动画运行时的测试文件。
- [ ] 运行 Task 1 测试并确认通过。

### Task 3: Verify, Document, Commit and Deploy

**Files:**
- Modify: `README.md`
- Modify: `docs/DEPLOY-HANDOVER.md`

- [ ] 更新首页说明为静态五幕与纯 CSS 背景，注明 Blender/渲染仅保留为历史源文件且不部署。
- [ ] 运行完整 Python、Node、Playwright、构建和 `git diff --check` 验证。
- [ ] 提交 `style: remove dynamic homepage background` 并推送当前分支。
- [ ] 等待 GitHub Pages 与 ECS 工作流成功，验证 `https://dingyivac.com` 不请求任何 scrolly 资产。
