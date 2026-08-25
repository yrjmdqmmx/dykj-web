# Corporate Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将首页改为紧凑的深色工业风普通企业官网布局，并移除浏览器标签页的文字 favicon。

**Architecture:** 用单个静态 Hero 替换五幕内容，复用现有业务照片与后续内容区块。图标源文件保留但从构建产物排除，所有页面显式声明空 favicon。

**Tech Stack:** HTML、CSS、Bash、Python unittest、Playwright

---

### Task 1: Write Corporate Hero and Favicon Contracts

**Files:**
- Modify: `tests/home_ui_contract_test.py`
- Modify: `tests/build_ui_contract_test.py`
- Modify: `tests/e2e/site.spec.js`
- Modify: `tests/domain_cutover_contract_test.py`

- [ ] 断言首页存在单一 `.corporate-hero`，引用 `assets/img/hero-helium.jpg`，不存在 `.company-scrolly`、`.company-act`、Canvas、picture 或动态运行时。
- [ ] 断言七页都使用空 favicon 且构建不含三个旧图标文件。
- [ ] 断言桌面/手机 Hero 可读、图片可见、无横向溢出、无 scrolly 资源请求和控制台错误。
- [ ] 运行契约并确认旧页面实现导致失败。

### Task 2: Implement the Compact Corporate Homepage

**Files:**
- Modify: `index.html`
- Modify: `css/home.css`
- Modify: `about.html`
- Modify: `business.html`
- Modify: `brands.html`
- Modify: `cases.html`
- Modify: `contact.html`
- Modify: `404.html`
- Modify: `scripts/build-site.sh`

- [ ] 用约 620px 的企业 Hero 替换五幕 HTML，保留公司标题、简介、两个 CTA 并添加真实管路设备照片。
- [ ] 删除五幕专用 CSS，增加桌面左右分栏和移动堆叠样式。
- [ ] 七页改为空 favicon，构建排除旧图标源文件。
- [ ] 运行 Task 1 测试并确认通过。

### Task 3: Document, Verify and Deploy

**Files:**
- Modify: `README.md`
- Modify: `docs/DEPLOY-HANDOVER.md`

- [ ] 更新首页和 favicon 运维说明。
- [ ] 运行完整 Python、Node、Playwright、构建与 `git diff --check`。
- [ ] 提交 `style: simplify homepage to corporate layout` 并推送当前分支。
- [ ] 等待 GitHub Pages/ECS 两条工作流成功，并在 `https://dingyivac.com` 做浏览器可视验收。
