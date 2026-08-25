# 首页动态背景移除设计

## 目标

首页不再展示或加载真空系统帧动画，也不保留静态设备海报。五幕公司能力文案继续存在，背景改为纯 CSS 的黑色与钢灰色静态渐变。

## 页面结构

- 删除 `company-stage` 及其中的 `picture`、`canvas`、渐晕、进度条和滚动提示。
- 删除首页的 `data-manifest` 与 `js/company-scrolly.js` 引用。
- 保留五个 `article.company-act`、CTA、工程示意说明和后续业务区块。
- 五幕从绝对定位的 500svh 滚动舞台改为普通文档流；桌面每幕保留充足留白，移动端自然堆叠。

## 视觉

- `company-scrolly` 使用不移动的石墨黑、钢铁灰径向/线性渐变。
- 不使用图片、Canvas、视频、视差或随滚动状态变化的背景。
- 铜色标签和青绿色 CTA 沿用现有全站设计变量。

## 资产与运行时

- Blender 工程和历史渲染资产保留在源码仓库，便于追溯，不删除源资产。
- `scripts/build-site.sh` 从发布产物排除 `assets/scrolly/v2/` 和 `js/company-scrolly.js`。
- 浏览器不请求 manifest、海报或序列帧，不创建 `window.__COMPANY_SCROLLY__`。

## 验证

- 静态契约确认舞台元素和运行时引用已移除、五幕文案仍完整、CSS 为静态渐变。
- 构建契约确认动态资产不进入 `_site`。
- Playwright 在桌面/手机、无 JS、Reduced Motion、Save-Data 下检查五幕可读、无横向溢出、无动态资产请求和控制台错误。
