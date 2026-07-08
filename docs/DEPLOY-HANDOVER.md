# 交接文档：官网迁移部署到阿里云服务器

> 写给接手的会话/工程师。上一阶段（建站 + GitHub Pages 上线）已完成，
> 本文档说明项目现状、服务器部署任务与全部注意事项。

## 一、项目现状（截至交接时）

- **仓库**：`zdywrnm/dykj-web`，唯一分支 `claude/dingyi-tech-website-lkp7bu`（即默认分支），**推送该分支会自动触发 GitHub Pages 部署**（`.github/workflows/pages.yml`）
- **线上地址**：<https://zdywrnm.github.io/dykj-web/>（GitHub Pages，作为临时/预览环境，迁移后可保留）
- **技术形态**：纯静态 HTML/CSS/JS，零构建零依赖，全站相对路径（根目录或子路径部署均可），直接把仓库文件放到 Web 根目录即可运行
- **页面**：index / about / business / brands / cases / contact + 自包含 404
- **站点配置集中在 `js/site-config.js`**：电话 133-8113-6863、邮箱 19313965@qq.com、地址（海淀区成府路45号中关村智造大街D座3层305）、`formEmail`（留言表单收件）、`icp`（备案号，当前为空字符串）
- **在线留言**：前端 fetch POST 到 `https://formsubmit.co/ajax/<formEmail>`，失败自动回退 mailto。链路已用 Gmail 验证可用；当前 formEmail=19313965@qq.com，**QQ 邮箱尚未做 FormSubmit 激活**（首次收到提交时会收到激活邮件，可能在垃圾箱，点击确认后生效）
- **公司位置**：嵌入式高德实时地图已上线（`js/map.js`，渐进增强，Key/GCJ-02 坐标在 `site-config.js` 的 `map` 字段）；Key 为空或加载失败时自动回退 SVG 占位卡片（零地图请求）。原高德/百度检索导航链接已按用户要求移除（2026-07）。安全密钥走服务器 Nginx 代理（模板 `docs/nginx-amap-proxy.conf.example`）

## 二、新阶段目标

用户已购买 **域名**（具体域名请向用户确认）和 **阿里云 ECS**（`root@116.62.146.226`，SSH 免密已配置），计划：

1. 将网站部署到该服务器（从而可做 ICP 备案）
2. 域名解析 + HTTPS
3. 完成 ICP 备案后正式上线

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
3. **HTTPS**：域名解析到 116.62.146.226 后，用阿里云免费 DV 证书（每年申领，控制台下发 pem/key）或 certbot（Let's Encrypt，需 80 端口可达；注意备案前域名解析到国内服务器 80/443 会被阿里云拦截提示未备案）
4. **ICP 备案**：在阿里云 ICP 代备案系统提交（需营业执照、法人/负责人身份证、真实性核验等）。**备案审核期间管局要求域名不可访问**——期间网站可先只用 IP 验证或保持 GitHub Pages 预览。备案通过后：
   - `js/site-config.js` 的 `icp` 填入真实备案号（页脚自动显示）
   - `sitemap.xml`、`robots.txt` 里的 `zdywrnm.github.io/dykj-web` 全局替换为正式域名
   - `404.html`「返回首页」`href="/dykj-web/"` 改回 `href="/"`
   - 各页 `<head>` 可补 `og:image` 绝对地址（已留注释）

## 五、遗留小事项（非阻塞）

| 事项 | 说明 |
|---|---|
| QQ 邮箱 FormSubmit 激活 | 网站上提交一条留言 → 19313965@qq.com 收激活邮件（查垃圾箱）→ 点击确认；建议把 formsubmit.co 加入 QQ 邮箱白名单 |
| 高德地图密钥激活 | lbs.amap.com 注册实名 → 应用管理创建应用 → 添加 Key（平台选「Web端(JS API)」）→ Key + 拾取器坐标填 `site-config.js` 的 `map` 配置；「安全密钥」只进服务器 Nginx（模板 `docs/nginx-amap-proxy.conf.example`），绝不提交进仓库。备案切正式域名后在高德控制台给 Key 绑域名白名单 |
| 首页低温泵拆解动画 | 帧序列 `assets/pump-seq/`（80 帧 WebP，预算 ≤2.5MB），Blender 工程在部署机 `~/aliyun-deploy/pump-src/cryopump.blend`（仓库外）。重渲/换帧后**必须**同步 bump `index.html` 里 `#pumpScrolly` 的 `data-v` 与静态图 `?v=` 参数击穿缓存；帧数变了改 `data-frames`。降级链：无 JS / reduce-motion / Save-Data / 帧加载失败 → 自动回静态爆炸图+零件清单版式 |
| 两张央企 Logo 裁切 | `assets/img/client-avic.jpg` 与 `client-cnnc.jpg` 源素材（公司简介 PDF）右缘即被裁切，拿到官方完整 Logo 后替换 |
| 公司官方 Logo | 页头/页脚现为纯文字标识（用户要求移除了自制图标）；favicon 仍是「鼎」字自制图标，拿到官方 Logo 后可整体替换 |
| 英文版 | 未做，结构已预留，需要时可加 |

## 六、工程约定（改代码前必读）

- 内容事实以公司简介 PDF 为准，**不虚构事实**；避免「最」「第一」等广告法极限词（此前审查已清理过一轮）
- 联系方式/备案号只改 `js/site-config.js`，页面里的同值静态文本是无 JS 兜底，改配置时同步更新
- 保持零外部依赖（无 CDN/Google Fonts），兼容国内网络。**显式例外**：联系页嵌入式高德地图 SDK（国内 CDN、仅 contact 页、懒加载、任何失败都完整降级回占位卡片，基线体验仍是零依赖）
- 页面有 `noscript` 与 `prefers-reduced-motion` 兜底，改动动效相关代码时注意保持
- 每次改动后验证：本地 `python3 -m http.server` + 浏览器检查 console 无报错、图片无缺失
