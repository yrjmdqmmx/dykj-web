#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../js/map.js"), "utf8");

function runMapRuntime(hostname, securityJsCode = "") {
  const appendedScripts = [];
  const visual = { classList: { add() {}, remove() {} } };
  const box = {};
  const location = { hostname, origin: `https://${hostname}` };

  class IntersectionObserverStub {
    constructor(callback) { this.callback = callback; }
    observe() { this.callback([{ isIntersecting: true }]); }
    disconnect() {}
  }

  const document = {
    getElementById(id) {
      if (id === "mapVisual") return visual;
      if (id === "amapContainer") return box;
      return null;
    },
    createElement(tag) { return { tagName: tag.toUpperCase() }; },
    head: { appendChild(node) { appendedScripts.push(node); } }
  };
  const window = {
    SITE_CONFIG: {
      map: {
        amapKey: "public-web-js-api-key",
        center: [116.335266, 39.994199],
        securityJsCode
      }
    },
    location,
    matchMedia() { return { matches: false }; },
    IntersectionObserver: IntersectionObserverStub
  };

  vm.runInNewContext(source, {
    window,
    document,
    location,
    IntersectionObserver: IntersectionObserverStub,
    setTimeout() { return 1; },
    clearTimeout() {},
    console
  }, { filename: "js/map.js" });

  return { appendedScripts, window };
}

function testGithubPagesWithoutSecurityCodeKeepsStaticFallback() {
  const runtime = runMapRuntime("zdywrnm.github.io");

  assert.equal(runtime.appendedScripts.length, 0);
  assert.equal(runtime.window._AMapSecurityConfig, undefined);
}

function testEcsHostStillUsesSameOriginSecurityProxy() {
  const runtime = runMapRuntime("116.62.146.226");

  assert.equal(runtime.appendedScripts.length, 1);
  assert.equal(
    runtime.window._AMapSecurityConfig.serviceHost,
    "https://116.62.146.226/_AMapService"
  );
}

testGithubPagesWithoutSecurityCodeKeepsStaticFallback();
process.stdout.write("ok - github.io without a security code keeps static map fallback\n");
testEcsHostStillUsesSameOriginSecurityProxy();
process.stdout.write("ok - ECS host still uses the same-origin AMap proxy\n");
