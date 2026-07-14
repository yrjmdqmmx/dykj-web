# 浏览器自动化

生产站点继续使用原生 HTML、CSS 与 JavaScript；本目录只为发布前浏览器质量门禁提供 Playwright 测试。

## 本地运行

```bash
npm ci
npx playwright install chromium
npm run test:browser
```

Playwright 会先调用 `scripts/build-site.sh _site`，再用本目录的只读静态服务器运行测试。浏览器、追踪、截图和 HTML 报告均不提交；失败产物位于 `output/playwright/`。

常用窄化命令：

```bash
npm run test:e2e -- --project=desktop-chromium
npm run test:e2e -- tests/e2e/fallbacks.spec.js
npm run test:e2e:headed
```

## 覆盖范围

- 1440×900、1920×1080 桌面与 390×844 手机断点及对应序列；
- 五幕滚动进度、桌面到手机的运行时切换与有界缓存；
- 弱网首帧延迟、首帧或中间帧 404、Reduced Motion、Save-Data、无 JavaScript；
- 移动菜单键盘操作、内部链接、站点控制台错误；
- ECS 根路径与 GitHub Pages 项目路径下的深层 404；
- 高德地图 SDK 成功与失败的确定性路由模拟，且始终保留静态导航入口。

测试不访问真实高德服务，不验证真实 Key 的平台白名单、Nginx `/_AMapService` 安全代理或阿里云网络状态；这些必须在部署后的 canary 检查中完成。
