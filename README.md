# 北京鼎熠科技有限公司 官网

纯静态企业官网（HTML / CSS / 原生 JS，零构建、零外部依赖），内容与图片素材源自公司简介资料。

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
将仓库全部文件上传到站点根目录（或子目录）即可，无需构建。

## ⚠️ 上线前待办清单

1. **替换联系方式**：编辑 `js/site-config.js`，填入真实电话、邮箱、地址、工作时间 —— 全站页脚与联系页自动同步。
2. **备案号**：`js/site-config.js` 中的 `icp` 字段替换为真实备案号（工信部要求境内主机部署需 ICP 备案）。
3. **域名相关**：
   - `sitemap.xml` 与 `robots.txt` 中的 `www.example.com` 替换为实际域名；
   - 各页 `<head>` 中可补充 `og:image` 绝对地址（已留注释）。
4. **地图**：`contact.html` 的地图占位区替换为高德 / 百度地图嵌入代码。
5. **留言表单**：当前通过 mailto 发送；如需服务端收集，替换 `js/main.js` 中表单提交逻辑为后端接口。
6. **两张客户 Logo 待换**：`assets/img/client-avic.jpg`（中国航空工业）与 `client-cnnc.jpg`（中国核工业）源素材右缘在公司简介 PDF 中即被裁切，建议上线前替换为官方完整 Logo。
7. **子路径部署**：若站点部署在子路径（如 GitHub Pages 项目站点 `/dykj-web/`），请将 `404.html` 中「返回首页」的 `href="/"` 改为 `href="/子路径/"`。

## 目录说明

```
css/style.css        全站样式（设计变量集中在 :root）
js/site-config.js    联系方式等站点配置（占位信息集中处）
js/main.js           导航 / 滚动动画 / 数字滚动 / 走马灯 / 表单
assets/img/          图片素材（源自公司简介 PDF，语义化命名）
assets/favicon.svg   站点图标
```
