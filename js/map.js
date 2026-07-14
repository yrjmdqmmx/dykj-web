/* ==========================================================================
 * 联系页嵌入式高德地图（渐进增强，仅 contact.html 引用）
 * SITE_CONFIG.map.amapKey 为空 / SDK 加载失败 / 初始化失败 / 无 JS 时，
 * 本文件零副作用：保留 SVG 占位视觉 + 高德/百度导航链接，与未启用时完全一致。
 * 安全密钥默认走本站 Nginx 代理 /_AMapService（见 docs/DEPLOY-HANDOVER.md）。
 * ========================================================================== */
(function () {
  "use strict";

  var cfg = (window.SITE_CONFIG && window.SITE_CONFIG.map) || {};
  var visual = document.getElementById("mapVisual");
  var box = document.getElementById("amapContainer");
  // 双重开关：key 或坐标未配置即整体禁用，页面保持现状
  if (!visual || !box || !cfg.amapKey || !Array.isArray(cfg.center)) return;

  // GitHub Pages 不能提供同源 /_AMapService 安全代理。未显式配置
  // securityJsCode 时不加载 SDK，保留地址与高德/百度导航链接作为完整兜底。
  if (!cfg.securityJsCode && /(^|\.)github\.io$/i.test(location.hostname)) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var started = false;

  function loadSdk() {
    if (started) return;
    started = true;
    // 安全密钥配置必须先于 SDK 脚本加载：
    // securityJsCode 非空用明文（仅本地调试），否则走本站 Nginx 代理
    window._AMapSecurityConfig = cfg.securityJsCode
      ? { securityJsCode: cfg.securityJsCode }
      : { serviceHost: location.origin + "/_AMapService" };

    var s = document.createElement("script");
    var timer = setTimeout(fail, 8000); // 与留言表单一致的 8s 超时约定
    s.src = "https://webapi.amap.com/maps?v=2.0&key=" + encodeURIComponent(cfg.amapKey);
    s.onload = function () { clearTimeout(timer); initMap(); };
    s.onerror = function () { clearTimeout(timer); fail(); };
    document.head.appendChild(s);
    function fail() { s.onload = s.onerror = null; } // 失败：不动 DOM，占位视觉即兜底
  }

  function initMap() {
    if (!window.AMap) return;
    try {
      // 先撑高卡片（CSS .map-on），原渐变占位在地图淡入前充当骨架屏
      visual.classList.add("map-on");
      var map = new AMap.Map(box, {
        center: cfg.center,
        zoom: cfg.zoom || 16,
        viewMode: "2D",
        animateEnable: !reduceMotion,
        resizeEnable: true
      });
      var markerOpts = { position: cfg.center };
      if (cfg.markerTitle) {
        markerOpts.title = cfg.markerTitle;
        markerOpts.label = {
          content: cfg.markerTitle,
          direction: "top",
          offset: new AMap.Pixel(0, -8)
        };
      }
      map.add(new AMap.Marker(markerOpts));
      // 10s 内未完成首屏渲染（如 key 无效）则回退占位
      var guard = setTimeout(function () {
        visual.classList.remove("map-on");
        map.destroy();
      }, 10000);
      map.on("complete", function () {
        clearTimeout(guard);
        visual.classList.add("map-ready");
        // 地图可交互后不再是纯装饰，恢复读屏可达并标注语义
        visual.removeAttribute("aria-hidden");
        box.setAttribute("role", "region");
        box.setAttribute("aria-label", "高德地图：" + (cfg.markerTitle || "公司位置"));
      });
    } catch (e) {
      visual.classList.remove("map-on");
    }
  }

  // 滚到卡片附近才加载 SDK；无 IntersectionObserver 的老浏览器退化为立即加载
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { io.disconnect(); loadSdk(); }
      });
    }, { rootMargin: "200px 0px" });
    io.observe(visual);
  } else {
    loadSdk();
  }
})();
