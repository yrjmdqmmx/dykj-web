# Dingyi Cinematic Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将官网升级为电影工业感、同一视觉系统贯穿五幕的首页，并统一全站视觉语言。

**Architecture:** Blender 只负责预渲染帧与静态兜底图，浏览器继续使用原生 HTML/CSS/JS。桌面与移动端使用独立帧序列和预算；无 JS、弱网、Save-Data、`prefers-reduced-motion` 或加载失败时必须显示可读的静态内容。

**Tech Stack:** Blender、WebP、HTML、CSS、原生 JavaScript、Bash artifact tests

---

## Locked Decisions

- 风格锁定为克制、精密的电影工业感；不做拼贴式章节。
- 首页是同一套真空系统、材质、灯光、镜头语言贯穿的五幕：品牌开场、系统拆解、能力展开、客户证据、联系收束。
- Blender 源文件固定为 `source/blender/dingyi-vacuum-system.blend`，网页只消费预渲染 WebP。
- 桌面序列：96 帧、1920×1080、总计不超过 8 MB；移动序列：40 帧、720×960、总计不超过 2 MB。
- 范围是首页重构加全站设计变量、页头页脚、按钮、卡片与内页头图统一；不重写已确认的业务事实。
- 地图不做预防性重构；只有复现真实问题后，才在 `contact.html`、`js/map.js` 或相关 CSS 中做最小修复。
- 每个阶段独立验证、独立提交，禁止把全部视觉改动压成一个提交。

### Task 1: Lock the Asset Contract

**Files:**
- Create: `tests/cinematic-assets.test.sh`
- Create: `source/blender/dingyi-vacuum-system.blend`
- Create: `assets/cinematic/desktop/`
- Create: `assets/cinematic/mobile/`

- [ ] 先写失败测试，校验桌面 96 帧/1920×1080/≤8 MB、移动 40 帧/720×960/≤2 MB，并拒绝缺帧和错号。
- [ ] 运行 `bash tests/cinematic-assets.test.sh`，确认因资产尚未生成而失败。
- [ ] 用同一 Blender 场景、材质与灯光完成五幕镜头，分别渲染桌面和移动帧序列。
- [ ] 再运行测试并人工抽查首、中、末帧；失败时优先降低 WebP quality，不降低锁定分辨率或帧数。
- [ ] 提交 `feat: add cinematic render assets`。

### Task 2: Rebuild the Homepage as Five Acts

**Files:**
- Modify: `index.html`
- Modify: `css/style.css`
- Create: `js/cinematic-homepage.js`
- Modify: `tests/build-site.test.sh`

- [ ] 先扩展 artifact 测试，要求新脚本、桌面帧、移动帧和静态兜底图进入 `_site`，运行并确认失败。
- [ ] 将首页组织为五幕，按视口选择对应帧集；保留语义标题、键盘可达 CTA 与静态正文。
- [ ] 保留并验证 reduced-motion、Save-Data、无 Canvas、加载失败四条降级路径。
- [ ] 运行 `bash tests/build-site.test.sh && bash tests/cinematic-assets.test.sh`，再做桌面与移动浏览器检查。
- [ ] 提交 `feat: rebuild homepage as cinematic system story`。

### Task 3: Unify the Whole Site

**Files:**
- Modify: `css/style.css`
- Modify: `about.html`
- Modify: `business.html`
- Modify: `brands.html`
- Modify: `cases.html`
- Modify: `contact.html`
- Modify: `404.html`

- [ ] 先记录全站页头、页脚、按钮、卡片、间距、焦点态的页面矩阵与视觉基线。
- [ ] 复用首页设计变量与组件语言统一内页，不改变已确认的公司信息和业务文案。
- [ ] 逐页检查 360、768、1440 px，验证导航、焦点态、对比度、图片比例和无横向滚动。
- [ ] 仅在能复现地图问题时添加失败用例并最小修复；无问题则不改地图。
- [ ] 提交 `style: unify cinematic visual system across site`；如有地图修复，另交 `fix: resolve verified contact map issue`。

### Task 4: Final Quality Gate

**Files:**
- Modify: `README.md`
- Modify: `docs/DEPLOY-HANDOVER.md`

- [ ] 运行全部 artifact/资产测试、`scripts/build-site.sh _site` 和 `git diff --check`。
- [ ] 本地以 `_site` 为根检查控制台、404、资源请求、弱网与 reduced-motion；确认地图代理回退仍工作。
- [ ] 更新重渲、预算、缓存版本和回滚说明，清除 `_site`。
- [ ] 提交 `docs: record cinematic homepage operations`。
