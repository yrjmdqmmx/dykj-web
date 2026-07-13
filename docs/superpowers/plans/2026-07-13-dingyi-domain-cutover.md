# Dingyi Domain Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在备案合规硬门槛满足后，将 `dingyivac.com` 安全切到 `116.62.146.226` 并启用可回滚的 HTTPS。

**Architecture:** DNS 使用 apex A 记录和 `www` CNAME；Nginx 以 webroot 完成 ACME 验证，正式站监听 443，未知 Host 返回 444。首发不发送 HSTS，以保留 HTTP/DNS 回滚空间。

**Tech Stack:** Alibaba Cloud DNS、Nginx、Certbot webroot、GitHub Actions rsync、curl、dig、openssl

---

## Hard Gate

- [ ] 在阿里云备案系统确认状态为“审核通过”，并取得完整、真实的备案号。
- [ ] 将该备案号写入 `js/site-config.js` 并在本地构建产物页脚验证。任一项未满足时立即停止：不改 DNS、不签证书、不开放正式域名。

### Task 1: Capture Baseline and Rollback Material

**Files:**
- Modify: `js/site-config.js`
- Modify: `robots.txt`
- Modify: `sitemap.xml`
- Modify: `404.html`

- [ ] 导出当前 DNS 记录截图/JSON；记录原 TTL、记录值和解析结果。
- [ ] 在服务器备份站点与 Nginx：`tar -C /var/www -czf /root/dykj-web-before-cutover.tgz dykj-web`，并复制启用中的 Nginx 配置到带日期的 `.bak`。
- [ ] 写入真实备案号，将正式 URL 改为 `https://dingyivac.com`，把 404 首页链接改为 `/`；运行 `scripts/build-site.sh _site` 并人工核对页脚。
- [ ] 独立提交 `chore: prepare dingyivac.com cutover`，部署后用服务器 IP 验证内容仍正确。

### Task 2: Change DNS with TTL 600

**Files:**
- No repository files.

- [ ] 在阿里云 DNS 设置 `@` / `A` / `116.62.146.226` / TTL `600`。
- [ ] 设置 `www` / `CNAME` / `dingyivac.com` / TTL `600`，删除会冲突的 `www` A/AAAA 记录。
- [ ] 用 `dig +short A dingyivac.com @223.5.5.5` 和 `dig +short CNAME www.dingyivac.com @223.5.5.5` 验证；未分别得到服务器 IP 与 apex 时不继续。

### Task 3: Enable HTTPS with Certbot Webroot

**Files:**
- Modify on server: `/etc/nginx/sites-available/dykj-web`
- Create on server: `/etc/nginx/sites-available/00-default-deny`

- [ ] 先配置 80 端口站点，使 `/.well-known/acme-challenge/` 从 `/var/www/dykj-web` 提供；默认未知 Host 的 80 端口 server 使用 `return 444`。
- [ ] 运行 `nginx -t && systemctl reload nginx`，放置测试 challenge 并从两个域名请求验证。
- [ ] 签发证书：`certbot certonly --webroot -w /var/www/dykj-web -d dingyivac.com -d www.dingyivac.com`。
- [ ] 配置正式 443 server、80 到 HTTPS 跳转，以及 443 `default_server` 未知 Host `return 444`；首发明确不添加 `Strict-Transport-Security`。
- [ ] 再运行 `nginx -t && systemctl reload nginx`，并执行 `certbot renew --dry-run`。

### Task 4: Verify and Roll Back if Needed

**Files:**
- No repository files.

- [ ] 验证 `curl -fsS https://dingyivac.com/index.html | cmp - index.html`、`curl -I https://www.dingyivac.com/`、证书 SAN/有效期和所有页面静态资源。
- [ ] 用错误 Host 请求 IP 的 80/443，确认连接被 444 关闭；确认响应中没有 HSTS。
- [ ] 观察至少一个 TTL 周期的 4xx/5xx、证书和资源错误后再宣布切换完成。
- [ ] 如失败，立即恢复备份 Nginx 配置和站点压缩包、执行 `nginx -t && systemctl reload nginx`，再把 `@`/`www` 恢复为 Task 1 记录的原值与 TTL；证书文件保留供排障，不强制删除。
