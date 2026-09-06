# 浏览器自动化

生产站点继续使用原生 HTML、CSS 与 JavaScript；本目录只为发布前浏览器质量门禁提供 Playwright 测试。

## 本地运行

```bash
npm ci
npx playwright install chromium
npm run test:browser
```

Playwright 会先调用 `scripts/build-site.sh _site`，再用本目录的只读静态服务器运行测试。浏览器、追踪、截图和 HTML 报告均不提交；失败产物位于 `output/playwright/`。

测试服务器默认使用 `127.0.0.1:4173`。如果该端口被其他项目占用，可指定一个空闲端口；服务器、浏览器和路径断言会使用同一配置，且不会复用已有服务器：

```bash
DINGYI_QA_PORT=4174 npm run test:browser
```

常用窄化命令：

```bash
npm run test:e2e -- --project=desktop-chromium
npm run test:e2e -- tests/e2e/fallbacks.spec.js
npm run test:e2e:headed
```

## 覆盖范围

- 1440×900 桌面与 390×844 手机断点的静态企业首页、真实业务图片、行动入口和无横向溢出；
- 首页不请求历史滚动叙事运行时或帧序列资源；
- Reduced Motion、Save-Data 和无 JavaScript 下的首页可读性；
- 移动菜单键盘操作、内部链接、站点控制台错误；
- ECS 根路径与 GitHub Pages 项目路径下的深层 404；
- 高德地图 SDK 成功与失败的确定性路由模拟，且始终保留静态导航入口。

测试不访问真实高德服务，不验证真实 Key 的平台白名单、Nginx `/_AMapService` 安全代理或阿里云网络状态；这些必须在部署后的 canary 检查中完成。
