/* ==========================================================================
 * 北京鼎熠科技官网 · 全站交互脚本（零依赖）
 * 导航 / 滚动动画 / 数字滚动 / Logo 走马灯 / 配置注入 / 表单
 * ========================================================================== */

(function () {
  "use strict";

  var doc = document;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 顶部导航：滚动加实底 ---------- */
  var header = doc.getElementById("siteHeader");
  function onScrollHeader() {
    if (!header) return;
    header.classList.toggle("scrolled", window.scrollY > 30);
  }
  window.addEventListener("scroll", onScrollHeader, { passive: true });
  onScrollHeader();

  /* ---------- 移动端菜单 ---------- */
  var navToggle = doc.getElementById("navToggle");
  if (navToggle && header) {
    var menuLinks = doc.querySelectorAll(".main-nav a");
    var mobileMenuQuery = window.matchMedia && window.matchMedia("(max-width: 900px)");

    function closeMenu(returnFocus) {
      header.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", "打开菜单");
      if (returnFocus) navToggle.focus();
    }

    navToggle.addEventListener("click", function () {
      var open = header.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      navToggle.setAttribute("aria-label", open ? "关闭菜单" : "打开菜单");
      // Toggle 在 DOM 中位于导航之后；打开时主动进入首个链接，
      // 否则键盘用户下一次 Tab 会直接越过整组菜单。
      if (open && menuLinks.length) {
        window.requestAnimationFrame(function () {
          if (header.classList.contains("nav-open")) menuLinks[0].focus();
        });
      }
    });
    // 点击菜单项后收起
    menuLinks.forEach(function (a) {
      a.addEventListener("click", function () {
        closeMenu(false);
      });
    });
    doc.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && header.classList.contains("nav-open")) {
        closeMenu(true);
      }
    });
    function onMenuBreakpoint(event) {
      if (!event.matches) closeMenu(false);
    }
    if (mobileMenuQuery) {
      if (typeof mobileMenuQuery.addEventListener === "function") {
        mobileMenuQuery.addEventListener("change", onMenuBreakpoint);
      } else if (typeof mobileMenuQuery.addListener === "function") {
        mobileMenuQuery.addListener(onMenuBreakpoint);
      }
    }
  }

  /* ---------- 当前页导航高亮 ---------- */
  var path = location.pathname.split("/").pop() || "index.html";
  doc.querySelectorAll(".main-nav a").forEach(function (a) {
    var href = a.getAttribute("href") || "";
    var current = href.split("#")[0] === path;
    a.classList.toggle("active", current);
    if (current) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });

  /* ---------- 滚动渐入 ---------- */
  var revealEls = doc.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("revealed");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("revealed"); });
  }

  /* ---------- 数字滚动（data-count 元素） ---------- */
  function animateCount(el) {
    var target = parseFloat(el.getAttribute("data-count")) || 0;
    var dur = 1400, start = null;
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.firstChild.nodeValue = Math.round(target * eased);
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  // HTML 中已写入最终数值，无 JS / reduced-motion 场景直接可读；
  // 仅在支持动画时先归零再滚动计数
  var countEls = doc.querySelectorAll("[data-count]");
  if ("IntersectionObserver" in window && !reduceMotion) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.firstChild.nodeValue = "0";
          animateCount(e.target);
          cio.unobserve(e.target);
        }
      });
    }, { threshold: 0.4 });
    countEls.forEach(function (el) { cio.observe(el); });
  }

  /* ---------- Logo 走马灯：复制一份轨道实现无缝循环 ----------
     reduced-motion 下 CSS 会静态平铺展示，因此不做复制；
     克隆节点设置 aria-hidden，避免读屏重复播报品牌名 */
  if (!reduceMotion) {
    doc.querySelectorAll(".marquee-track").forEach(function (track) {
      Array.prototype.slice.call(track.children).forEach(function (node) {
        var clone = node.cloneNode(true);
        clone.setAttribute("aria-hidden", "true");
        track.appendChild(clone);
      });
    });
  }

  /* ---------- 业务页锚点导航高亮 ---------- */
  var subnavLinks = doc.querySelectorAll(".subnav a[href^='#']");
  if (subnavLinks.length && "IntersectionObserver" in window) {
    var secMap = {};
    subnavLinks.forEach(function (a) {
      var id = a.getAttribute("href").slice(1);
      var sec = doc.getElementById(id);
      if (sec) secMap[id] = a;
    });
    var sio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          subnavLinks.forEach(function (a) { a.classList.remove("current"); });
          var link = secMap[e.target.id];
          if (link) {
            link.classList.add("current");
            link.scrollIntoView({ block: "nearest", inline: "center", behavior: reduceMotion ? "auto" : "smooth" });
          }
        }
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    Object.keys(secMap).forEach(function (id) { sio.observe(doc.getElementById(id)); });
  }

  /* ---------- 回到顶部 ---------- */
  var backtop = doc.getElementById("backtop");
  if (backtop) {
    window.addEventListener("scroll", function () {
      backtop.classList.toggle("show", window.scrollY > 600);
    }, { passive: true });
    backtop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }

  /* ---------- 页脚年份 ---------- */
  var yearEl = doc.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ---------- 站点配置注入（联系方式等） ---------- */
  var cfg = window.SITE_CONFIG || {};
  doc.querySelectorAll("[data-config]").forEach(function (el) {
    var key = el.getAttribute("data-config");
    // 允许空字符串覆盖（如未备案时清除备案号占位）
    if (key in cfg && cfg[key] != null) el.textContent = cfg[key];
  });
  // tel: / mailto: 链接
  doc.querySelectorAll("[data-config-href]").forEach(function (el) {
    var key = el.getAttribute("data-config-href");
    if (!cfg[key]) return;
    if (key === "phone" || key === "mobile") el.setAttribute("href", "tel:" + cfg[key].replace(/[^\d+]/g, ""));
    if (key === "email") el.setAttribute("href", "mailto:" + cfg[key]);
  });

  /* ---------- 留言表单 ----------
     首选：FormSubmit 免费服务直接送达邮箱（无需后端）；
     失败或浏览器不支持 fetch 时：回退为唤起访客邮件客户端（mailto）。
     注意：FormSubmit 首次收到提交时会向收件邮箱发送激活确认邮件，点击确认后生效。 */
  var form = doc.getElementById("contactForm");
  var statusEl = doc.getElementById("formStatus");

  function showStatus(type, msg) {
    if (!statusEl) return;
    statusEl.hidden = false;
    statusEl.className = "form-status " + type;
    statusEl.textContent = msg;
  }

  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      // 蜜罐命中：机器人填写了隐藏字段，静默丢弃
      if (form.elements._honey && form.elements._honey.value) return;

      var get = function (n) { return (form.elements[n] && form.elements[n].value.trim()) || ""; };
      var subject = "【官网留言】" + get("name") + " - " + (get("subject") || "业务咨询");
      var bodyText = [
        "姓名：" + get("name"),
        "单位：" + get("org"),
        "电话：" + get("tel"),
        "邮箱：" + get("mail"),
        "",
        "留言内容：",
        get("message")
      ].join("\n");
      var mailtoUrl = "mailto:" + (cfg.email || "") +
        "?subject=" + encodeURIComponent(subject) +
        "&body=" + encodeURIComponent(bodyText);

      function fallbackMailto() {
        showStatus("warn", "在线发送未成功，已尝试打开您的邮件客户端发送；亦可直接致电 " + (cfg.phone || "") + "。");
        location.href = mailtoUrl;
      }

      var formTo = cfg.formEmail || cfg.email;
      if (!window.fetch || !formTo) { fallbackMailto(); return; }

      var btn = form.querySelector('button[type="submit"]');
      var restore = function () { if (btn) { btn.disabled = false; btn.textContent = "提交留言"; } };
      if (btn) { btn.disabled = true; btn.textContent = "发送中…"; }
      if (statusEl) statusEl.hidden = true;

      var ctrl = ("AbortController" in window) ? new AbortController() : null;
      var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, 8000) : null;

      fetch("https://formsubmit.co/ajax/" + formTo, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        signal: ctrl ? ctrl.signal : undefined,
        body: JSON.stringify({
          _subject: subject,
          _template: "table",
          _captcha: "false",
          "姓名": get("name"),
          "单位": get("org"),
          "电话": get("tel"),
          "邮箱": get("mail"),
          "咨询主题": get("subject"),
          "留言内容": get("message")
        })
      }).then(function (r) {
        if (timer) clearTimeout(timer);
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      }).then(function () {
        restore();
        form.reset();
        showStatus("ok", "留言已发送，我们会在收到后尽快与您联系。");
      }).catch(function () {
        if (timer) clearTimeout(timer);
        restore();
        fallbackMailto();
      });
    });
  }
})();
