/* ==========================================================================
 * 首页 · 低温泵拆解 scrollytelling（零依赖，渐进增强，仅 index.html 引用）
 * 预渲染 WebP 帧序列随滚动擦除播放；任何门槛不满足或帧加载失败时，
 * 保持/回退 HTML 静态版式（爆炸全景图 + 零件清单），不破相。
 * ========================================================================== */
(function () {
  "use strict";

  var doc = document;
  var section = doc.getElementById("pumpScrolly");
  if (!section) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var saveData = !!(navigator.connection && navigator.connection.saveData);
  var canvas = section.querySelector(".pump-canvas");
  var stage = section.querySelector(".pump-stage");
  var ctx = canvas && canvas.getContext && canvas.getContext("2d");

  // 升级门槛：任一不满足则保持静态版式（与 main.js 的 reduceMotion 语义一致）
  if (reduceMotion || saveData || !ctx || !("IntersectionObserver" in window)) return;
  // 滚动恢复/锚点已进入或越过本章节时升级会造成布局跳动——放弃升级。
  // 阈值取半屏：正常首屏加载时本章节顶部位于 hero 底部（约 0.92 视口高），不会误伤
  var rect0 = section.getBoundingClientRect();
  if (rect0.top < window.innerHeight * 0.5) return;

  var TOTAL = parseInt(section.getAttribute("data-frames"), 10) || 80;
  var BASE = section.getAttribute("data-src") || "assets/pump-seq/";
  var VER = section.getAttribute("data-v") || "";
  var captions = Array.prototype.slice.call(section.querySelectorAll(".pump-caption"));

  var frames = new Array(TOTAL);
  var loaded = new Array(TOTAL);
  var loadedCount = 0, started = false, downgraded = false;
  var curFrame = -1, ticking = false;
  // 画布底色 = 章节背景色(与帧序列烘焙背景一致),letterbox 空白带借此无缝
  var bgColor = getComputedStyle(section).backgroundColor || "#06201f";

  function pad3(n) { n = String(n); while (n.length < 3) n = "0" + n; return n; }
  function frameUrl(i) { return BASE + "f" + pad3(i) + ".webp" + (VER ? "?v=" + VER : ""); }

  // 立即升级布局（高度尽早稳定，避免用户临近时页面高度突变）；帧按 IO 懒加载
  section.classList.add("pump-on");

  // 尺寸：DPR 封顶 2；iOS 地址栏伸缩触发的 resize 只在尺寸真变时重建
  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = Math.round(stage.clientWidth * dpr);
    var h = Math.round(stage.clientHeight * dpr);
    if (canvas.width === w && canvas.height === h) return;
    canvas.width = w; canvas.height = h;
    curFrame = -1;
    requestDraw();
  }

  // 归一化滚动进度 p ∈ [0,1]（同 main.js animateCount 的进度模式；
  // 擦除保持线性，缓动已烘焙在帧序列的关键帧里）
  function progress() {
    var r = section.getBoundingClientRect();
    var total = section.offsetHeight - window.innerHeight;
    return total > 0 ? Math.max(0, Math.min(1, -r.top / total)) : 0;
  }

  // 目标帧未加载时找最近已加载帧，保证画面永不空白
  function nearest(t) {
    if (loaded[t]) return t;
    for (var d = 1; d < TOTAL; d++) {
      if (t - d >= 0 && loaded[t - d]) return t - d;
      if (t + d < TOTAL && loaded[t + d]) return t + d;
    }
    return -1;
  }

  function draw() {
    var p = progress();
    var t = Math.round(p * (TOTAL - 1));
    var i = nearest(t);
    if (i >= 0 && i !== curFrame) {
      var img = frames[i];
      var cw = canvas.width, ch = canvas.height;
      // contain 完整显示(帧是 4:3,视口横竖比不定;cover 会裁掉泵体两端/上下),
      // 空白带填与帧背景相同的纯色,视觉无缝
      var s = Math.min(cw / img.naturalWidth, ch / img.naturalHeight);
      var dw = img.naturalWidth * s, dh = img.naturalHeight * s;
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, cw, ch);
      ctx.drawImage(img, (cw - dw) / 2, (ch - dh) / 2, dw, dh);
      curFrame = i;
    }
    updateCaptions(p);
  }

  function requestDraw() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { ticking = false; draw(); });
  }

  // 字幕按进度区间淡入淡出；首幕起点与末幕终点保持全显
  var FADE = 0.05;
  function updateCaptions(p) {
    captions.forEach(function (el) {
      var a = parseFloat(el.getAttribute("data-start"));
      var b = parseFloat(el.getAttribute("data-end"));
      var o = 0;
      if (p >= a && p <= b) {
        var fin = a === 0 ? 1 : (p - a) / FADE;
        var fout = b === 1 ? 1 : (b - p) / FADE;
        o = Math.max(0, Math.min(fin, fout, 1));
      }
      el.style.opacity = o.toFixed(3);
      el.style.visibility = o > 0.01 ? "visible" : "hidden";
    });
  }

  // 帧加载：先每 4 帧铺骨架（含末帧）再补齐，并发 6；
  // 骨架先行保证快速滚动时 nearest() 有邻近帧可画
  function loadAll() {
    if (started) return;
    started = true;
    var order = [], i;
    for (i = 0; i < TOTAL; i += 4) order.push(i);
    if (order.indexOf(TOTAL - 1) === -1) order.push(TOTAL - 1);
    for (i = 0; i < TOTAL; i++) if (i % 4 !== 0 && i !== TOTAL - 1) order.push(i);
    var idx = 0;
    function next() {
      if (idx >= order.length || downgraded) return;
      var n = order[idx++];
      var img = new Image();
      img.decoding = "async";
      img.onload = function () { loaded[n] = true; loadedCount++; requestDraw(); next(); };
      img.onerror = function () {
        if (n === 0 && loadedCount === 0) downgrade(); // 首帧即失败：整体退回静态版式
        next();
      };
      img.src = frameUrl(n);
      frames[n] = img;
    }
    for (var k = 0; k < 6; k++) next();
  }

  // 失败降级：撤销升级恢复静态版式（IO 提前 600px 触发，此时用户尚未到场，重排无感）
  function downgrade() {
    downgraded = true;
    section.classList.remove("pump-on");
    window.removeEventListener("scroll", requestDraw);
    window.removeEventListener("resize", onResize);
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { io.disconnect(); loadAll(); }
    });
  }, { rootMargin: "600px 0px" });
  io.observe(section);

  function onResize() { resize(); }
  window.addEventListener("scroll", requestDraw, { passive: true });
  window.addEventListener("resize", onResize);
  resize();
  updateCaptions(0);

  // 验证钩子（headless 浏览器断言用，不参与业务逻辑）
  window.__PUMP__ = {
    get on() { return !downgraded; },
    get frame() { return curFrame; },
    get loaded() { return loadedCount; },
    get total() { return TOTAL; }
  };
})();
