#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const RUNTIME_PATH = path.join(ROOT, "js/company-scrolly.js");
const RUNTIME_SOURCE = fs.readFileSync(RUNTIME_PATH, "utf8");

class ClassList {
  constructor(initial) {
    this.values = new Set(initial || []);
  }

  add(value) {
    this.values.add(value);
  }

  remove(value) {
    this.values.delete(value);
  }

  toggle(value, force) {
    if (force === undefined) force = !this.values.has(value);
    if (force) this.values.add(value);
    else this.values.delete(value);
    return force;
  }
}

class MediaQueryListStub {
  constructor(matches) {
    this.matches = matches;
    this.listeners = new Set();
  }

  addEventListener(type, listener) {
    if (type === "change") this.listeners.add(listener);
  }

  addListener(listener) {
    this.listeners.add(listener);
  }

  dispatch(matches) {
    this.matches = matches;
    const event = { matches, media: "(max-width: 767px)" };
    this.listeners.forEach((listener) => listener(event));
  }
}

function manifestFixture() {
  return {
    sequences: {
      desktop: {
        frameCount: 96,
        frameTemplate: "desktop/frame-{frame}.webp",
        indexPad: 4,
        poster: "poster-desktop.webp",
        priorityFrames: [1, 18, 19, 37, 38, 55, 56, 78, 79, 96],
        cacheSize: 16
      },
      mobile: {
        frameCount: 40,
        frameTemplate: "mobile/frame-{frame}.webp",
        indexPad: 4,
        poster: "poster-mobile.webp",
        priorityFrames: [1, 8, 9, 16, 17, 24, 25, 32, 33, 40],
        cacheSize: 9
      }
    },
    acts: Array.from({ length: 5 }, (_, index) => ({
      progress: [index / 5, (index + 1) / 5]
    }))
  };
}

function createRuntime() {
  const breakpoint = new MediaQueryListStub(false);
  const reduceMotion = new MediaQueryListStub(false);
  const images = [];
  const timers = new Map();
  const windowListeners = new Map();
  let timerId = 0;

  const progressItems = Array.from({ length: 5 }, (_, index) => ({
    classList: new ClassList(index === 0 ? ["is-active"] : []),
    getAttribute(name) {
      return name === "data-progress-act" ? String(index + 1) : null;
    }
  }));
  const acts = Array.from({ length: 5 }, (_, index) => ({
    classList: new ClassList(),
    getAttribute(name) {
      return name === "data-act" ? String(index + 1) : null;
    }
  }));
  const posterImage = { src: "poster-desktop.webp" };
  const posterSources = [{ srcset: "poster-mobile.webp" }];
  const picture = {
    querySelector(selector) {
      return selector === "img" ? posterImage : null;
    },
    querySelectorAll(selector) {
      return selector === "source" ? posterSources : [];
    }
  };
  const context2d = {
    clearRect() {},
    drawImage() {}
  };
  const canvas = {
    hidden: true,
    width: 0,
    height: 0,
    getContext(kind) {
      return kind === "2d" ? context2d : null;
    }
  };
  const stage = {
    clientWidth: 1200,
    clientHeight: 1000,
    getBoundingClientRect() {
      return { width: 1200, height: 1000 };
    }
  };
  const section = {
    offsetHeight: 5000,
    classList: new ClassList(),
    getAttribute(name) {
      return name === "data-manifest" ? "assets/scrolly/v2/manifest.json" : null;
    },
    getBoundingClientRect() {
      return { top: 0 };
    },
    querySelector(selector) {
      if (selector === ".company-canvas") return canvas;
      if (selector === ".company-stage") return stage;
      if (selector === ".company-poster") return picture;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === ".company-progress [data-progress-act]") return progressItems;
      if (selector === ".company-act[data-act]") return acts;
      return [];
    }
  };
  const document = {
    baseURI: "https://example.test/",
    getElementById(id) {
      return id === "companyScrolly" ? section : null;
    }
  };

  class ImageStub {
    constructor() {
      this._src = "";
      this.onload = null;
      this.onerror = null;
      this.decode = () => Promise.resolve();
      this.naturalWidth = 1920;
      this.naturalHeight = 1080;
      this.resolved = false;
      images.push(this);
    }

    get src() {
      return this._src;
    }

    set src(value) {
      this._src = value;
    }
  }

  const window = {
    innerWidth: 1200,
    innerHeight: 1000,
    devicePixelRatio: 1,
    navigator: { connection: { saveData: false } },
    matchMedia(query) {
      if (query === "(max-width: 767px)") return breakpoint;
      if (query === "(prefers-reduced-motion: reduce)") return reduceMotion;
      return new MediaQueryListStub(false);
    },
    addEventListener(type, listener) {
      if (!windowListeners.has(type)) windowListeners.set(type, new Set());
      windowListeners.get(type).add(listener);
    },
    requestAnimationFrame(callback) {
      callback();
      return 1;
    }
  };

  function fetchStub() {
    return Promise.resolve({
      ok: true,
      url: "https://example.test/assets/scrolly/v2/manifest.json",
      json: () => Promise.resolve(manifestFixture())
    });
  }
  window.fetch = fetchStub;

  const context = {
    URL,
    Image: ImageStub,
    console,
    document,
    fetch: fetchStub,
    navigator: window.navigator,
    window,
    setTimeout(callback) {
      timerId += 1;
      timers.set(timerId, callback);
      return timerId;
    },
    clearTimeout(id) {
      timers.delete(id);
    }
  };

  vm.runInNewContext(RUNTIME_SOURCE, context, { filename: RUNTIME_PATH });

  return {
    breakpoint,
    images,
    window,
    resolve(image) {
      assert(image, "expected a pending image");
      image.resolved = true;
      assert.equal(typeof image.onload, "function", "image request has no load handler");
      image.onload();
    },
    activeImages() {
      return images.filter((image) => image.src && !image.resolved);
    }
  };
}

async function flush(iterations = 8) {
  for (let index = 0; index < iterations; index += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

async function testNeighborhoodKeepsAConcurrencySlot() {
  const runtime = createRuntime();
  await flush();
  runtime.resolve(runtime.activeImages()[0]);
  await flush();

  const requestedURLs = runtime.activeImages().map((image) => image.src);
  assert(
    requestedURLs.some((url) => /desktop\/frame-000[23]\.webp$/.test(url)),
    `nearby frame was starved by boundary frames: ${requestedURLs.join(", ")}`
  );
  assert(
    requestedURLs.filter((url) => /desktop\/frame-(0018|0019|0037|0038|0055|0056|0078|0079|0096)\.webp$/.test(url)).length <= 2,
    "boundary preload must never occupy all three image slots"
  );
}

async function testBreakpointSwitchCancelsAndReinitializes() {
  const runtime = createRuntime();
  await flush();
  runtime.resolve(runtime.activeImages()[0]);
  await flush();
  const oldPending = runtime.activeImages().slice();

  runtime.window.innerWidth = 390;
  runtime.breakpoint.dispatch(true);
  await flush();

  const snapshot = runtime.window.__COMPANY_SCROLLY__;
  assert.equal(snapshot.variant, "mobile");
  assert.equal(snapshot.cacheLimit, 9);
  assert.deepEqual(Array.from(snapshot.cacheKeys), []);
  assert.deepEqual(Array.from(snapshot.failed), []);
  assert.deepEqual(Array.from(snapshot.requested), [1]);
  assert.deepEqual(Array.from(snapshot.inflight), [1]);
  assert(oldPending.every((image) => image.src === ""), "old desktop image requests were not cancelled");

  const mobileFirst = runtime.activeImages().find((image) => /mobile\/frame-0001\.webp$/.test(image.src));
  assert(mobileFirst, "mobile first frame was not requested after crossing 767px");
  runtime.resolve(mobileFirst);
  await flush();
  assert.equal(runtime.window.__COMPANY_SCROLLY__.enhanced, true);
  assert(runtime.window.__COMPANY_SCROLLY__.cacheKeys.length <= 9);
}

function testLRUHasNoOutOfCacheImageReference() {
  assert(
    !/\blastDrawnImage\b/.test(RUNTIME_SOURCE),
    "lastDrawnImage retains an evicted image outside the bounded LRU"
  );
}

async function main() {
  const tests = [
    ["neighborhood keeps one concurrency slot", testNeighborhoodKeepsAConcurrencySlot],
    ["breakpoint switch cancels and reinitializes", testBreakpointSwitchCancelsAndReinitializes],
    ["LRU owns every retained decoded image", testLRUHasNoOutOfCacheImageReference]
  ];

  for (const [name, test] of tests) {
    await test();
    process.stdout.write(`ok - ${name}\n`);
  }
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
