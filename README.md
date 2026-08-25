# 北京鼎熠科技有限公司 官网

纯静态企业官网（HTML / CSS / 原生 JS，无应用编译、零外部依赖），内容与图片素材源自公司简介资料。

## 页面结构

| 页面 | 说明 |
|---|---|
| `index.html` | 首页：普通企业 Hero、主营能力、经营品牌、客户与案例 |
| `about.html` | 关于我们：公司简介、公司优势、发展理念、服务网络 |
| `business.html` | 主营业务：真空系统集成 / 超高纯气路 / 合同能源管理 / 腔体加工 / 非标定制 / 低温泵与防爆产品 / 维修服务 |
| `brands.html` | 产品与品牌：九大经营品牌与产品类别导览 |
| `cases.html` | 客户与案例：国企 / 高校 / 科研院所客户与成功案例 |
| `contact.html` | 联系我们：联系方式、在线留言、嵌入地图与导航链接 |
| `404.html` | 404 页面 |

## 本地预览

```bash
python3 -m http.server 8000
# 打开 http://localhost:8000
```

（直接双击 HTML 文件也能浏览，全站为相对路径。）

## 部署

任何静态托管均可：虚拟主机、Nginx、阿里云 OSS / 腾讯云 COS 静态网站、GitHub Pages 等。
部署前运行 `scripts/build-site.sh _site`，只上传生成的 `_site/`；源码、文档、测试和构建脚本不会进入线上站点。

**当前已配置 GitHub Pages 自动部署**：推送到 `claude/dingyi-tech-website-lkp7bu` 分支即触发
`.github/workflows/pages.yml` 工作流，发布到 <https://yrjmdqmmx.github.io/dykj-web/>
（要求仓库 Settings → Pages → Source 为 "GitHub Actions"）。

## 上线与外部切换清单

1. ~~替换联系方式~~（已完成）：联系方式维护于 `js/site-config.js`，如有变更改此一处即可全站生效。
2. **备案与正式 URL（已上线）**：`js/site-config.js` 及七页静态页脚使用备案号 `京ICP备2026049830号-1`；六个内容页的 canonical / `og:url`、`sitemap.xml` 与 `robots.txt` 均指向 `https://dingyivac.com`。
3. **域名基础设施（已上线）**：
   - `dingyivac.com` A 记录和 `www` CNAME 已指向 `116.62.146.226`，Nginx 使用 Certbot 证书提供 HTTPS；HTTP 与 www 统一跳转到 `https://dingyivac.com`，未知 Host 拒绝访问，首发未启用 HSTS；
   - 各页 `<head>` 后续可补充 `og:image` 绝对地址（当前未配置）。
4. **嵌入式地图**（已上线）：联系页内嵌高德实时地图（`js/map.js`，渐进增强），Key/坐标配置在 `js/site-config.js` 的 `map` 字段；安全密钥走服务器 Nginx 代理（模板见 `docs/nginx-amap-proxy.conf.example`，详见交接文档）。Key 为空、GitHub Pages 无同源代理或加载失败时自动回退 SVG 占位卡片，并始终保留高德/百度导航链接。
5. **留言表单**：通过 FormSubmit 免费服务直发 `js/site-config.js` 中 `formEmail` 指定的邮箱（当前 zqairtop@163.com），发送失败自动回退 mailto。链路已用 Gmail 验证可用；**163 邮箱首次收到提交时需点击 FormSubmit 激活确认邮件（注意查垃圾箱）**。
6. **两张客户 Logo 待换**：`assets/img/client-avic.jpg`（中国航空工业）与 `client-cnnc.jpg`（中国核工业）源素材右缘在公司简介 PDF 中即被裁切，建议上线前替换为官方完整 Logo。
7. **404 双部署路径**：`404.html` 会按 `github.io` 与根域名自动选择 `/dykj-web/` 或 `/`，无需在正式域名切换时手工改链接。

## 目录说明

```
css/style.css        全站样式（设计变量集中在 :root）
css/home.css         首页企业 Hero 与黑钢工业视觉
js/site-config.js    联系方式等站点配置（占位信息集中处）
js/main.js           导航 / 滚动动画 / 数字滚动 / 走马灯 / 表单
js/company-scrolly.js 历史预渲染序列运行时（源码保留，不发布）
js/map.js            联系页嵌入式高德地图（渐进增强）
assets/img/          图片素材（源自公司简介 PDF，语义化命名）
assets/scrolly/v2/   历史五幕 WebP 序列、海报与 manifest（源码保留，不发布）
source/blender/      历史五幕真空系统 .blend、构建/预览脚本与质量关口静帧
tests/e2e/           Playwright 浏览器质量门禁（不进入发布产物）
assets/favicon.svg   历史站点图标源文件（保留、不发布）
```

`js/pump-scrolly.js`、`assets/pump-seq/`、`js/company-scrolly.js` 与 `assets/scrolly/v2/` 仅保留作历史源文件，`scripts/build-site.sh` 会明确排除，不会发布。首页使用约 620px 的左右分栏企业 Hero，右侧直接加载真实业务照片 `assets/img/hero-helium.jpg`，移动端自然堆叠；不加载 Canvas、视频、帧序列或滚动叙事运行时。

七个页面均显式声明空 favicon，浏览器标签页不显示自制“鼎”字图标。`favicon.ico`、`assets/favicon.svg` 与 `assets/apple-touch-icon.png` 只作为历史源码保留，构建时全部排除。

Blender 工程及 HDR/EXR/TIFF 源素材由 Git LFS 管理；历史 WebP 帧与质量关口预览仍使用普通 Git，便于代码审查与追溯，但不进入发布产物。场景内部结构为工程示意，不对应具体品牌或型号。
