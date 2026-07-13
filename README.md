# 北京鼎熠科技有限公司 官网

纯静态企业官网（HTML / CSS / 原生 JS，无应用编译、零外部依赖），内容与图片素材源自公司简介资料。

## 页面结构

| 页面 | 说明 |
|---|---|
| `index.html` | 首页：Hero、公司简介、主营业务、经营品牌、客户群体、成功案例 |
| `about.html` | 关于我们：公司简介、公司优势、发展理念、服务网络 |
| `business.html` | 主营业务：真空系统集成 / 超高纯气路 / 合同能源管理 / 腔体加工 / 非标定制 / 低温泵与防爆产品 / 维修服务 |
| `brands.html` | 产品与品牌：九大经营品牌与产品类别导览 |
| `cases.html` | 客户与案例：国企 / 高校 / 科研院所客户与成功案例 |
| `contact.html` | 联系我们：联系方式、在线留言、地图占位 |
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
`.github/workflows/pages.yml` 工作流，发布到 <https://zdywrnm.github.io/dykj-web/>
（要求仓库 Settings → Pages → Source 为 "GitHub Actions"）。

## ⚠️ 上线前待办清单

1. ~~替换联系方式~~（已完成）：联系方式维护于 `js/site-config.js`，如有变更改此一处即可全站生效。
2. **备案号**：`js/site-config.js` 中的 `icp` 字段替换为真实备案号（工信部要求境内主机部署需 ICP 备案）。
3. **域名相关**：
   - `sitemap.xml` 与 `robots.txt` 当前指向 GitHub Pages 临时地址，启用正式域名后请全局替换；
   - 各页 `<head>` 中可补充 `og:image` 绝对地址（已留注释）。
4. **嵌入式地图**（已上线）：联系页内嵌高德实时地图（`js/map.js`，渐进增强），Key/坐标配置在 `js/site-config.js` 的 `map` 字段；安全密钥走服务器 Nginx 代理（模板见 `docs/nginx-amap-proxy.conf.example`，详见交接文档）。Key 为空或加载失败时自动回退 SVG 占位卡片（导航外链已按用户要求于 2026-07 移除）。
5. **留言表单**：通过 FormSubmit 免费服务直发 `js/site-config.js` 中 `formEmail` 指定的邮箱（当前 19313965@qq.com），发送失败自动回退 mailto。链路已用 Gmail 验证可用；**QQ 邮箱首次收到提交时需点击 FormSubmit 激活确认邮件（注意查垃圾箱）**。
6. **两张客户 Logo 待换**：`assets/img/client-avic.jpg`（中国航空工业）与 `client-cnnc.jpg`（中国核工业）源素材右缘在公司简介 PDF 中即被裁切，建议上线前替换为官方完整 Logo。
7. **404 首页链接**：`404.html` 中「返回首页」当前指向 GitHub Pages 子路径 `/dykj-web/`；迁移到正式域名根部署时请改回 `href="/"`。

## 目录说明

```
css/style.css        全站样式（设计变量集中在 :root）
js/site-config.js    联系方式等站点配置（占位信息集中处）
js/main.js           导航 / 滚动动画 / 数字滚动 / 走马灯 / 表单
js/map.js            联系页嵌入式高德地图（渐进增强）
js/pump-scrolly.js   首页低温泵拆解 scrollytelling（帧序列滚动擦除）
assets/img/          图片素材（源自公司简介 PDF，语义化命名）
assets/pump-seq/     低温泵拆解帧序列（Blender 渲染 f000-f079.webp + 静态兜底图；
                     下一阶段计划将源文件存放于 source/blender/dingyi-vacuum-system.blend，
                     生成后按交接文档执行重渲）
assets/favicon.svg   站点图标
```

计划中的 Blender 工程及 HDR/EXR/TIFF 源素材将由 Git LFS 管理；部署用 WebP 帧仍使用普通 Git，便于静态托管直接读取。
