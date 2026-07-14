#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../js/main.js"), "utf8");

class ClassList {
  constructor() { this.values = new Set(); }
  add(value) { this.values.add(value); }
  remove(value) { this.values.delete(value); }
  contains(value) { return this.values.has(value); }
  toggle(value, force) {
    if (force === undefined) force = !this.values.has(value);
    if (force) this.values.add(value);
    else this.values.delete(value);
    return force;
  }
}

class EventTargetStub {
  constructor() { this.listeners = new Map(); }
  addEventListener(type, callback) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(callback);
  }
  dispatch(type, event = {}) {
    (this.listeners.get(type) || []).forEach((callback) => callback(event));
  }
}

class MediaQueryStub extends EventTargetStub {
  constructor(matches) {
    super();
    this.matches = matches;
  }
  addListener(callback) { this.addEventListener("change", callback); }
  dispatchChange(matches) {
    this.matches = matches;
    this.dispatch("change", { matches });
  }
}

function createRuntime() {
  const documentTarget = new EventTargetStub();
  const windowTarget = new EventTargetStub();
  const mobileQuery = new MediaQueryStub(true);
  const reduceQuery = new MediaQueryStub(false);
  const header = { classList: new ClassList() };
  const attributes = new Map();

  const document = {
    activeElement: null,
    getElementById(id) {
      if (id === "siteHeader") return header;
      if (id === "navToggle") return navToggle;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === ".main-nav a") return navLinks;
      return [];
    },
    addEventListener: documentTarget.addEventListener.bind(documentTarget)
  };

  function focus(element) { document.activeElement = element; }
  const navLinks = Array.from({ length: 6 }, (_, index) => {
    const target = new EventTargetStub();
    return {
      index,
      classList: new ClassList(),
      getAttribute(name) { return name === "href" ? (index ? `page-${index}.html` : "index.html") : null; },
      setAttribute() {},
      removeAttribute() {},
      addEventListener: target.addEventListener.bind(target),
      focus() { focus(this); }
    };
  });

  const toggleTarget = new EventTargetStub();
  const navToggle = {
    classList: new ClassList(),
    setAttribute(name, value) { attributes.set(name, value); },
    getAttribute(name) { return attributes.get(name); },
    addEventListener: toggleTarget.addEventListener.bind(toggleTarget),
    focus() { focus(this); },
    click() { toggleTarget.dispatch("click", { currentTarget: this }); }
  };

  const window = {
    scrollY: 0,
    SITE_CONFIG: {},
    matchMedia(query) {
      return query === "(max-width: 900px)" ? mobileQuery : reduceQuery;
    },
    addEventListener: windowTarget.addEventListener.bind(windowTarget),
    requestAnimationFrame(callback) { callback(1); return 1; },
    scrollTo() {}
  };

  vm.runInNewContext(source, {
    window,
    document,
    location: { pathname: "/index.html", href: "https://example.test/index.html" },
    navigator: {},
    console,
    setTimeout,
    clearTimeout,
    fetch: undefined
  }, { filename: "js/main.js" });

  return { document, header, mobileQuery, navLinks, navToggle };
}

function testOpeningMenuMovesFocusIntoNavigation() {
  const runtime = createRuntime();
  runtime.navToggle.focus();
  runtime.navToggle.click();

  assert.equal(runtime.header.classList.contains("nav-open"), true);
  assert.equal(runtime.navToggle.getAttribute("aria-expanded"), "true");
  assert.equal(runtime.document.activeElement, runtime.navLinks[0]);
}

function testDesktopBreakpointClosesMobileMenu() {
  const runtime = createRuntime();
  runtime.navToggle.click();
  runtime.mobileQuery.dispatchChange(false);

  assert.equal(runtime.header.classList.contains("nav-open"), false);
  assert.equal(runtime.navToggle.getAttribute("aria-expanded"), "false");
  assert.equal(runtime.navToggle.getAttribute("aria-label"), "打开菜单");
}

testOpeningMenuMovesFocusIntoNavigation();
process.stdout.write("ok - opening menu focuses first navigation link\n");
testDesktopBreakpointClosesMobileMenu();
process.stdout.write("ok - desktop breakpoint closes mobile menu\n");
