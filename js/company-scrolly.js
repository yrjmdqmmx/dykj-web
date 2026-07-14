/* ==========================================================================
 * 首页 · 五幕公司能力滚动叙事
 *
 * 零依赖、渐进增强：海报和五幕 HTML 是基础体验。只有清单与首帧都成功
 * 解码后才显示 Canvas；其余帧按边界优先、当前位置邻域其次进行有界加载。
 * ========================================================================== */
(function () {
  "use strict";

  var doc = document;
  var section = doc.getElementById("companyScrolly");
  if (!section) return;

  var canvas = section.querySelector(".company-canvas");
  var stage = section.querySelector(".company-stage");
  var progressItems = Array.prototype.slice.call(
    section.querySelectorAll(".company-progress [data-progress-act]")
  );
  var acts = Array.prototype.slice.call(section.querySelectorAll(".company-act[data-act]"));
  var breakpointQuery = window.matchMedia && window.matchMedia("(max-width: 767px)");
  var variant = breakpointQuery ? (breakpointQuery.matches ? "mobile" : "desktop") :
    (window.innerWidth <= 767 ? "mobile" : "desktop");
  var hardCacheLimit = variant === "mobile" ? 9 : 16;
  var cacheLimit = hardCacheLimit;
  var enhanced = false;
  var targetFrame = 1;
  var drawnFrame = null;
  var cache = new Map();
  var failed = new Set();
  var requested = new Set();
  var inflight = new Set();
  var frameCount = 0;
  var indexPad = 4;
  var frameTemplate = "";
  var manifestBase = null;
  var manifestData = null;
  var actRanges = [];
  var ticking = false;
  var canvasDirty = true;
  var listenersBound = false;
  var loadGeneration = 0;
  var activeRequests = new Set();

  // 只暴露不可变快照，供浏览器自动化验证，不参与页面业务逻辑。
  Object.defineProperty(window, "__COMPANY_SCROLLY__", {
    configurable: false,
    enumerable: false,
    get: function () {
      return Object.freeze({
        variant: variant,
        enhanced: enhanced,
        targetFrame: targetFrame,
        drawnFrame: drawnFrame,
        cacheKeys: Object.freeze(Array.from(cache.keys())),
        cacheLimit: cacheLimit,
        failed: Object.freeze(Array.from(failed)),
        requested: Object.freeze(Array.from(requested)),
        inflight: Object.freeze(Array.from(inflight))
      });
    }
  });

  var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  var reduceMotion = !!(
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  var saveData = !!(connection && connection.saveData);
  var ctx = null;

  try {
    ctx = canvas && canvas.getContext && canvas.getContext("2d");
  } catch (error) {
    ctx = null;
  }

  // 所有降级分支都在请求 manifest/帧序列之前退出。
  if (reduceMotion || saveData || !canvas || !stage || !ctx || !("fetch" in window)) return;

  var manifestAttribute = section.getAttribute("data-manifest");
  if (!manifestAttribute) return;

  var manifestURL;
  try {
    manifestURL = new URL(manifestAttribute, doc.baseURI);
  } catch (error) {
    return;
  }

  if (breakpointQuery) {
    if (typeof breakpointQuery.addEventListener === "function") {
      breakpointQuery.addEventListener("change", onBreakpointChange);
    } else if (typeof breakpointQuery.addListener === "function") {
      breakpointQuery.addListener(onBreakpointChange);
    }
  }

  fetch(manifestURL.href, { credentials: "same-origin" })
    .then(function (response) {
      if (!response.ok) throw new Error("manifest request failed");
      manifestBase = new URL(response.url || manifestURL.href, manifestURL.href);
      return response.json();
    })
    .then(function (manifest) {
      manifestData = manifest;
      return activateVariant();
    })
    .catch(function () {
      // 海报与完整 HTML 文案已经在 DOM 中，无需再改变页面状态。
    });

  function onBreakpointChange(event) {
    var nextVariant = event.matches ? "mobile" : "desktop";
    if (nextVariant === variant) return;

    variant = nextVariant;
    hardCacheLimit = variant === "mobile" ? 9 : 16;
    cacheLimit = hardCacheLimit;
    if (!manifestData) return;

    activateVariant().catch(function () {
      // 新序列首帧失败时继续显示当前断点的原生海报与完整 HTML 文案。
    });
  }

  function activateVariant() {
    var generation = loadGeneration + 1;
    loadGeneration = generation;
    cancelActiveRequests();
    resetVariantState();

    var sequence = manifestData && manifestData.sequences && manifestData.sequences[variant];
    if (!sequence) throw new Error("sequence missing");

    frameCount = toPositiveInteger(sequence.frameCount);
    indexPad = toPositiveInteger(sequence.indexPad) || 4;
    frameTemplate = typeof sequence.frameTemplate === "string" ? sequence.frameTemplate : "";
    if (!frameCount || frameTemplate.indexOf("{frame}") === -1) {
      throw new Error("invalid sequence contract");
    }

    var configuredLimit = toPositiveInteger(sequence.cacheSize) || hardCacheLimit;
    cacheLimit = Math.min(hardCacheLimit, configuredLimit);
    actRanges = normalizeActRanges(manifestData.acts);
    resolvePoster(sequence.poster);

    return loadDecodedFrame(1, generation).then(function (image) {
      if (generation !== loadGeneration) return;
      cachePut(1, image);

      try {
        resizeCanvas();
        drawImage(1, image);
      } catch (error) {
        cache.clear();
        drawnFrame = null;
        throw error;
      }

      canvas.hidden = false;
      enhanced = true;
      section.classList.add("canvas-ready");

      updateFromScroll();
      bindRuntimeListeners();

      queuePriorityFrames(sequence.priorityFrames);
      queueNeighborhood(targetFrame);
    });
  }

  function bindRuntimeListeners() {
    if (listenersBound) return;
    listenersBound = true;
    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", onResize);
  }

  function cancelActiveRequests() {
    Array.from(activeRequests).forEach(function (request) {
      request.cancel();
    });
    activeRequests.clear();
  }

  function resetVariantState() {
    enhanced = false;
    targetFrame = 1;
    drawnFrame = null;
    cache.clear();
    failed.clear();
    requested.clear();
    inflight.clear();
    priorityQueue.length = 0;
    nearbyQueue.length = 0;
    queued.clear();
    activeLoads = 0;
    activePriorityLoads = 0;
    activeNearbyLoads = 0;
    canvasDirty = true;
    canvas.hidden = true;
    section.classList.remove("canvas-ready");
  }

  function toPositiveInteger(value) {
    var number = Number(value);
    return Number.isInteger(number) && number > 0 ? number : 0;
  }

  function normalizeActRanges(manifestActs) {
    if (!Array.isArray(manifestActs) || manifestActs.length !== acts.length) {
      return acts.map(function (_, index) {
        return [index / acts.length, (index + 1) / acts.length];
      });
    }

    return manifestActs.map(function (act, index) {
      var range = act && act.progress;
      var start = Array.isArray(range) ? Number(range[0]) : NaN;
      var end = Array.isArray(range) ? Number(range[1]) : NaN;
      if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end > 1 || end <= start) {
        return [index / manifestActs.length, (index + 1) / manifestActs.length];
      }
      return [start, end];
    });
  }

  function resolvePoster(posterPath) {
    if (typeof posterPath !== "string" || !posterPath) return;

    var posterURL = new URL(posterPath, manifestBase).href;
    var picture = section.querySelector(".company-poster");
    var image = picture && picture.querySelector("img");
    if (image) image.src = posterURL;

    if (variant === "mobile" && picture) {
      var sources = picture.querySelectorAll("source");
      Array.prototype.forEach.call(sources, function (source) {
        source.srcset = posterURL;
      });
    }
  }

  function frameURL(frame) {
    var padded = String(frame).padStart(indexPad, "0");
    var path = frameTemplate.replace(/\{frame\}/g, padded);
    return new URL(path, manifestBase).href;
  }

  function loadDecodedFrame(frame, generation) {
    requested.add(frame);
    inflight.add(frame);

    return new Promise(function (resolve, reject) {
      var image = new Image();
      var settled = false;
      var request = {};
      var timer;

      function cleanup() {
        clearTimeout(timer);
        image.onload = image.onerror = null;
        activeRequests.delete(request);
      }

      function fail(error, cancelImage) {
        if (settled) return;
        settled = true;
        cleanup();
        if (cancelImage) image.src = "";
        reject(error);
      }

      request.cancel = function () {
        var error = new Error("image request cancelled");
        error.cancelled = true;
        fail(error, true);
      };
      activeRequests.add(request);

      timer = setTimeout(function () {
        fail(new Error("image request timed out"), true);
      }, 12000);

      image.decoding = "async";
      image.onload = function () {
        if (settled) return;
        if (typeof image.decode !== "function") {
          fail(new Error("image decode unavailable"), false);
          return;
        }

        image.decode().then(function () {
          if (settled) return;
          settled = true;
          cleanup();
          resolve(image);
        }, function () {
          fail(new Error("image decode failed"), false);
        });
      };
      image.onerror = function () {
        fail(new Error("image request failed"), false);
      };
      image.src = frameURL(frame);
    }).then(function (image) {
      if (generation === loadGeneration) inflight.delete(frame);
      return image;
    }, function (error) {
      if (generation === loadGeneration) {
        inflight.delete(frame);
        if (!error.cancelled) failed.add(frame);
      }
      throw error;
    });
  }

  function cachePut(frame, image) {
    if (cache.has(frame)) cache.delete(frame);
    cache.set(frame, image);

    while (cache.size > cacheLimit) {
      cache.delete(cache.keys().next().value);
    }
  }

  function cacheGet(frame) {
    if (!cache.has(frame)) return null;
    var image = cache.get(frame);
    cache.delete(frame);
    cache.set(frame, image);
    return image;
  }

  function resizeCanvas() {
    var rect = stage.getBoundingClientRect();
    var width = Math.max(1, Math.round(rect.width || stage.clientWidth || window.innerWidth || 1));
    var height = Math.max(1, Math.round(rect.height || stage.clientHeight || window.innerHeight || 1));
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pixelWidth = Math.max(1, Math.round(width * dpr));
    var pixelHeight = Math.max(1, Math.round(height * dpr));

    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
      canvasDirty = true;
    }
  }

  function drawImage(frame, image) {
    var sourceWidth = image.naturalWidth || image.width;
    var sourceHeight = image.naturalHeight || image.height;
    if (!sourceWidth || !sourceHeight) throw new Error("decoded image has no dimensions");

    var scale = Math.max(canvas.width / sourceWidth, canvas.height / sourceHeight);
    var drawWidth = sourceWidth * scale;
    var drawHeight = sourceHeight * scale;
    var x = (canvas.width - drawWidth) / 2;
    var y = (canvas.height - drawHeight) / 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, x, y, drawWidth, drawHeight);
    drawnFrame = frame;
    canvasDirty = false;
  }

  function scrollProgress() {
    var rect = section.getBoundingClientRect();
    var distance = Math.max(0, section.offsetHeight - window.innerHeight);
    if (!distance) return 0;
    return clamp(-rect.top / distance, 0, 1);
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function requestUpdate() {
    if (!enhanced || ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      ticking = false;
      updateFromScroll();
    });
  }

  function updateFromScroll() {
    if (!enhanced) return;

    var progress = scrollProgress();
    var previousTarget = targetFrame;
    targetFrame = 1 + Math.round(progress * (frameCount - 1));

    updateAct(progress);
    renderNearest(targetFrame);
    if (targetFrame !== previousTarget) queueNeighborhood(targetFrame);
  }

  function updateAct(progress) {
    var currentIndex = actRanges.length - 1;

    for (var index = 0; index < actRanges.length; index += 1) {
      var range = actRanges[index];
      if (progress >= range[0] && (progress < range[1] || index === actRanges.length - 1)) {
        currentIndex = index;
        break;
      }
    }

    progressItems.forEach(function (item) {
      var itemAct = Number(item.getAttribute("data-progress-act"));
      item.classList.toggle("is-active", itemAct === currentIndex + 1);
    });

    acts.forEach(function (article) {
      var articleAct = Number(article.getAttribute("data-act"));
      article.classList.toggle("is-current", articleAct === currentIndex + 1);
    });
  }

  function nearestCached(frame) {
    var direct = cacheGet(frame);
    if (direct) return { frame: frame, image: direct };

    var nearestFrame = null;
    var nearestImage = null;
    var nearestDistance = Infinity;

    cache.forEach(function (image, cachedFrame) {
      var distance = Math.abs(cachedFrame - frame);
      if (
        distance < nearestDistance ||
        (distance === nearestDistance && (nearestFrame === null || cachedFrame < nearestFrame))
      ) {
        nearestFrame = cachedFrame;
        nearestImage = image;
        nearestDistance = distance;
      }
    });

    if (nearestImage) {
      cacheGet(nearestFrame);
      return { frame: nearestFrame, image: nearestImage };
    }

    return null;
  }

  function renderNearest(frame) {
    var candidate = nearestCached(frame);
    if (!candidate) return;
    if (!canvasDirty && candidate.frame === drawnFrame) return;
    drawImage(candidate.frame, candidate.image);
  }

  function onResize() {
    if (!enhanced) return;
    resizeCanvas();
    requestUpdate();
  }

  var priorityQueue = [];
  var nearbyQueue = [];
  var queued = new Set();
  var activeLoads = 0;
  var activePriorityLoads = 0;
  var activeNearbyLoads = 0;
  var maxConcurrent = 3;

  function queuePriorityFrames(frames) {
    var list = Array.isArray(frames) ? frames : [];
    list.forEach(function (frame) {
      enqueue(toPositiveInteger(frame), true);
    });
    pumpQueue();
  }

  function queueNeighborhood(center) {
    nearbyQueue.forEach(function (frame) {
      queued.delete(frame);
    });
    nearbyQueue.length = 0;

    var radius = variant === "mobile" ? 1 : 2;
    var order = [center];
    for (var distance = 1; distance <= radius; distance += 1) {
      order.push(center - distance, center + distance);
    }
    order.forEach(function (frame) {
      enqueue(frame, false);
    });
    pumpQueue();
  }

  function enqueue(frame, priority) {
    if (
      !frame || frame < 1 || frame > frameCount || cache.has(frame) ||
      failed.has(frame) || inflight.has(frame) || queued.has(frame) ||
      (!canvasDirty && drawnFrame === frame)
    ) {
      return;
    }

    queued.add(frame);
    (priority ? priorityQueue : nearbyQueue).push(frame);
  }

  function takeQueuedFrame(queue, priority) {
    while (queue.length) {
      var frame = queue.shift();
      queued.delete(frame);

      if (
        frame >= 1 && frame <= frameCount && !cache.has(frame) &&
        !failed.has(frame) && !inflight.has(frame) &&
        (canvasDirty || drawnFrame !== frame)
      ) {
        return { frame: frame, priority: priority };
      }
    }
    return null;
  }

  function nextQueuedTask() {
    var nearbyTask = takeQueuedFrame(nearbyQueue, false);
    if (nearbyTask) return nearbyTask;

    // 边界预载最多占两条通道，始终给当前滚动邻域留一条通道。
    if (activePriorityLoads >= maxConcurrent - 1) return null;
    return takeQueuedFrame(priorityQueue, true);
  }

  function pumpQueue() {
    while (enhanced && activeLoads < maxConcurrent) {
      var task = nextQueuedTask();
      if (!task) return;

      activeLoads += 1;
      if (task.priority) activePriorityLoads += 1;
      else activeNearbyLoads += 1;
      task.generation = loadGeneration;
      runLoadTask(task);
    }
  }

  function runLoadTask(task) {
    function finish() {
      if (task.generation !== loadGeneration) return;
      activeLoads -= 1;
      if (task.priority) activePriorityLoads -= 1;
      else activeNearbyLoads -= 1;
      pumpQueue();
    }

    loadDecodedFrame(task.frame, task.generation).then(function (image) {
      if (task.generation !== loadGeneration) return;
      cachePut(task.frame, image);
      renderNearest(targetFrame);
    }, function () {
      // 失败帧已由 loadDecodedFrame 记入 failed，后续不会重试。
    }).then(finish, finish);
  }
})();
