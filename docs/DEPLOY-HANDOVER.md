# 交接文档：官网迁移部署到阿里云服务器

> 写给接手的会话/工程师。上一阶段（建站 + GitHub Pages 上线）已完成，
> 本文档说明项目现状、服务器部署任务与全部注意事项。

## 一、项目现状（截至交接时）

- **仓库**：`yrjmdqmmx/dykj-web`，唯一分支 `claude/dingyi-tech-website-lkp7bu`（即默认分支），**推送该分支会自动触发 GitHub Pages 部署**（`.github/workflows/pages.yml`）
- **正式线上地址**：<https://dingyivac.com/>；<https://yrjmdqmmx.github.io/dykj-web/> 作为 GitHub Pages 预览环境保留
- **技术形态**：生产站点为纯静态 HTML/CSS/JS、零运行时依赖；发布前由 `scripts/build-site.sh` 过滤源码与测试，Playwright 仅作为开发质量门禁
- **页面**：index / about / business / brands / cases / contact + GitHub Pages/ECS 双部署路径自适应 404
- **站点配置集中在 `js/site-config.js`**：电话 133-8113-6863、邮箱 19313965@qq.com、地址（海淀区成府路45号中关村智造大街D座3层305）、`formEmail`（留言表单收件）、`icp`（备案号 `京ICP备2026049830号-1`）
- **正式域名已上线**：六个内容页的 canonical / `og:url`、`sitemap.xml`、`robots.txt` 及 404 无 JS 兜底指向 `https://dingyivac.com`；DNS、双域名证书、HTTP/www 规范跳转与未知 Host 拒绝均已配置，首发未启用 HSTS
- **在线留言**：前端 fetch POST 到 `https://formsubmit.co/ajax/<formEmail>`，失败自动回退 mailto。链路已用 Gmail 验证可用；当前 formEmail=19313965@qq.com，**QQ 邮箱尚未做 FormSubmit 激活**（首次收到提交时会收到激活邮件，可能在垃圾箱，点击确认后生效）
- **公司位置**：嵌入式高德实时地图已上线（`js/map.js`，渐进增强，Key/GCJ-02 坐标在 `site-config.js` 的 `map` 字段）；Key 为空、GitHub Pages 无同源代理或加载失败时自动回退 SVG 占位卡片（零地图请求），并始终保留高德/百度导航链接。ECS/正式域名通过同源 Nginx 代理保存安全密钥（模板 `docs/nginx-amap-proxy.conf.example`）

## 二、新阶段目标

用户已购买域名 **dingyivac.com** 和 **阿里云 ECS**（`root@116.62.146.226`，SSH 免密已配置）。正式域名已于 2026-08-25 完成切换，后续维护按以下环节复核：

1. 将最新构建产物部署到该服务器并核验内容
2. 核验域名解析、HTTPS 与 Certbot 自动续期
3. 核验备案信息、地图代理与公网访问

**用户约定：所有服务器操作通过 `ssh root@116.62.146.226 "..."` 执行；动手前先做只读检查。**

## 三、第一步：服务器只读体检（用户已明确要求先做这个）

```bash
ssh root@116.62.146.226 'bash -s' <<'EOF'
echo "===== 系统版本 ====="; grep PRETTY_NAME /etc/os-release; uname -r; uptime
echo; echo "===== CPU / 内存 ====="; echo "CPU核数: $(nproc)"; free -h
echo; echo "===== 磁盘用量 ====="; df -h | grep -vE 'tmpfs|overlay|udev|shm'
echo; echo "===== Docker ====="; docker --version 2>/dev/null || echo "未安装 docker"
docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo "未安装 compose"
echo; echo "===== 容器（含已停止） ====="; docker ps -a 2>/dev/null || echo "-"
echo; echo "===== 占用资源最高的进程 ====="; ps aux --sort=-%mem | head -8
echo; echo "===== 监听端口 ====="; ss -tulpn | grep LISTEN
echo; echo "===== 防火墙 ====="; ufw status 2>/dev/null || systemctl is-active firewalld 2>/dev/null || echo "未启用 ufw/firewalld"
echo; echo "===== Web 服务 ====="; nginx -v 2>&1 || echo "未安装 nginx"; systemctl is-active nginx 2>/dev/null || true
EOF
```

另需用户在**阿里云控制台**确认 ECS 安全组已放行入方向 80/443（SSH 22 已通）。

## 四、建议部署方案（供参考，结合体检结果调整）

1. **Nginx 静态托管**（系统包直装即可，站点小，无需 Docker；若服务器已有 Docker 生态也可用 nginx 容器）
   - Web 根目录如 `/var/www/dykj-web`，内容 = 本仓库全部文件（排除 `.git`、`.github`、`docs`）
   - Nginx 要点：`error_page 404 /404.html;`、gzip 开启、静态资源缓存头、`index index.html`
2. **自动部署**：GitHub Actions 加一个 deploy workflow，push 后 rsync 到服务器
   - 服务器建专用部署用户或用 root（用户自行权衡），私钥放 GitHub Secrets（`SSH_PRIVATE_KEY`、`SERVER_HOST`）
   - 注意：GitHub App 令牌可能无权修改 workflow 文件（本次建站时 pages.yml 是 git push 成功的，说明该仓库可以直接推 workflow）
3. **HTTPS**：当前使用 Certbot webroot 为 `dingyivac.com` 与 `www.dingyivac.com` 签发同一证书，80 端口保留 `/.well-known/acme-challenge/`；续期 deploy hook 会先 `nginx -t` 再 reload
4. **备案与仓库切换状态**：备案号 `京ICP备2026049830号-1` 已写入 `js/site-config.js` 和七页静态页脚；canonical、`og:url`、sitemap、robots 与 404 无 JS 绝对兜底已切到 `https://dingyivac.com`。`404.html` 的 JavaScript 仍按 `github.io` 与根域名自动选择 `/dykj-web/` 或 `/`，所以 GitHub Pages 预览路径继续保留。各页 `<head>` 后续仍可补 `og:image` 绝对地址（当前未配置）。

## 五、遗留小事项（非阻塞）

| 事项 | 说明 |
|---|---|
| QQ 邮箱 FormSubmit 激活 | 网站上提交一条留言 → 19313965@qq.com 收激活邮件（查垃圾箱）→ 点击确认；建议把 formsubmit.co 加入 QQ 邮箱白名单 |
| 高德地图密钥激活 | lbs.amap.com 注册实名 → 应用管理创建应用 → 添加 Key（平台选「Web端(JS API)」）→ Key + 拾取器坐标填 `site-config.js` 的 `map` 配置；「安全密钥」只进服务器 Nginx（模板 `docs/nginx-amap-proxy.conf.example`），绝不提交进仓库。正式域名切换时在高德控制台给 Key 绑域名白名单 |
| 首页五幕真空系统动画 | `assets/scrolly/v2/` 桌面/移动预渲染序列与 `js/company-scrolly.js` 已上线；统一 Blender 工程为仓库内 LFS 文件 `source/blender/dingyi-vacuum-system.blend`，可由同目录脚本复现。网页以 `manifest.json` 为唯一帧契约；降级链为无 JS / Reduced Motion / Save-Data / Canvas 不可用 / 首帧失败 → 静态关键画面和完整 HTML 五幕文案。内部结构均为工程示意，不对应具体品牌或型号；旧泵序列仅保留历史源文件且不进入发布产物。 |
| 两张央企 Logo 裁切 | `assets/img/client-avic.jpg` 与 `client-cnnc.jpg` 源素材（公司简介 PDF）右缘即被裁切，拿到官方完整 Logo 后替换 |
| 公司官方 Logo | 页头/页脚现为纯文字标识（用户要求移除了自制图标）；favicon 仍是「鼎」字自制图标，拿到官方 Logo 后可整体替换 |
| 英文版 | 未做，结构已预留，需要时可加 |

## 六、工程约定（改代码前必读）

- 内容事实以公司简介 PDF 为准，**不虚构事实**；避免「最」「第一」等广告法极限词（此前审查已清理过一轮）
- 联系方式/备案号只改 `js/site-config.js`，页面里的同值静态文本是无 JS 兜底，改配置时同步更新
- 保持零外部依赖（无 CDN/Google Fonts），兼容国内网络。**显式例外**：联系页嵌入式高德地图 SDK（国内 CDN、仅 contact 页、懒加载、任何失败都完整降级回占位卡片，基线体验仍是零依赖）
- 页面有 `noscript` 与 `prefers-reduced-motion` 兜底，改动动效相关代码时注意保持
- 每次改动后验证：本地 `python3 -m http.server` + 浏览器检查 console 无报错、图片无缺失
