// Exercise the shipped LuCI view with delayed/failed RPCs; no external test dependencies.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../status-index.js'), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

function harness(flush = () => Promise.resolve()) {
  let serial = 0;
  const timers = new Map(), polls = [], storage = new Map();
  function E(tag, attrs, children) {
    if (Array.isArray(tag)) return E('fragment', {}, tag);
    if (attrs == null || typeof attrs !== 'object' || Array.isArray(attrs) || attrs.tag) {
      children = attrs; attrs = {};
    }
    const node = { tag, attrs, children: [], style: {}, isConnected: true,
      classList: { add() {} }, setAttribute(key, value) { this.attrs[key] = value; }, blur() {},
      appendChild(child) {
        if (typeof child !== 'object') child = { data: String(child) };
        child.parentNode = this; this.children.push(child); this.firstChild = this.children[0];
      }
    };
    function append(child) {
      if (Array.isArray(child)) child.forEach(append);
      else if (child != null) node.appendChild(child);
    }
    append(children); return node;
  }
  const dom = { content(node, content) { node.children = []; node.appendChild(content); } };
  const window = { setTimeout(fn, delay) { const id = ++serial; timers.set(id, { fn, delay }); return id; },
    clearTimeout(id) { timers.delete(id); } };
  const localStorage = { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
  const L = { bind: (fn, self, ...args) => fn.bind(self, ...args), resource: p => '/' + p,
    resolveDefault: (p, fallback) => p.catch(() => fallback), require: () => Promise.resolve({}) };
  const view = new Function('view','dom','poll','fs','network','ui','L','E','_','window','localStorage','document','console',source)(
    { extend: object => object }, dom, { add: fn => polls.push(fn) }, {}, { flushCache: flush },
    { createHandlerFn: (self, name, ...args) => self[name].bind(self, ...args) }, L, E, text => text,
    window, localStorage, { querySelector: () => null }, { warn() {} });
  const text = node => node.data ?? node.children.map(text).join('');
  function advance(delay) {
    for (const [id, entry] of [...timers]) if (entry.delay === delay) { timers.delete(id); entry.fn(); }
  }
  return { view, E, timers, polls, storage, text, advance };
}

(async () => {
  let stuckCalls = 0, fastCalls = 0, flushCalls = 0, oneshots = 0, resolveSlow;
  const h = harness(() => { flushCalls++; return new Promise(() => {}); });
  const fast = { title: 'System', load: () => Promise.resolve(++fastCalls), render: value => h.E('p', {}, 'CPU0 CPU1 CPU2 CPU3 ' + value), oneshot: () => oneshots++ };
  const slow = { title: 'PON', load: () => { stuckCalls++; return new Promise(resolve => { resolveSlow = resolve; }); }, render: value => h.E('p', {}, value) };
  const skeleton = h.view.render([fast, slow]);
  assert.equal(typeof skeleton.then, 'undefined', 'Whole view must not await card RPCs');
  assert.match(h.text(skeleton), /System.*PON/);
  const containers = skeleton.children.map(section => section.children[1]);
  h.advance(0); await tick();
  assert.match(h.text(containers[0]), /CPU0 CPU1 CPU2 CPU3 1/);
  assert.equal(oneshots, 1);
  assert.equal(stuckCalls, 1);
  assert.equal(flushCalls, 1);
  h.advance(10000);
  assert.match(h.text(containers[1]), /Waiting for data/);
  for (let i = 0; i < 3; i++) { h.polls[0](); await tick(); }
  assert.equal(stuckCalls, 1, 'Hung RPC must not accumulate requests after notice timeout');
  assert.equal(flushCalls, 1, 'Hung network flush must not accumulate requests');
  assert.equal(oneshots, 1, 'One-shot callback must run once');
  assert.match(h.text(containers[0]), /CPU3 4/);
  resolveSlow('Optics available'); await tick();
  assert.match(h.text(containers[1]), /Optics available/);

  let attempts = 0;
  const retry = harness();
  const flaky = { title: 'Retry', load: () => ++attempts === 1 ? Promise.reject(Error('RPC failed')) : Promise.resolve('Recovered'), render: value => retry.E('p', {}, value) };
  const rv = retry.view.render([flaky]), card = rv.children[0].children[1];
  retry.advance(0); await tick();
  assert.match(retry.text(card), /RPC call failed/);
  retry.polls[0](); await tick();
  assert.match(retry.text(card), /Recovered/);
  assert.equal(attempts, 2);
  const button = retry.E('span', {}, 'Hide');
  retry.view.handleToggleSection(flaky, card, { currentTarget: button });
  retry.polls[0](); await tick();
  assert.equal(attempts, 2, 'Collapsed cards must skip subsequent polls');
  assert.equal(card.style.display, 'none');
  assert.equal(retry.storage.get('Retry'), 'hide');
  retry.view.handleToggleSection(flaky, card, { currentTarget: button });
  retry.polls[0](); await tick();
  assert.equal(attempts, 3);
  assert.match(retry.text(card), /Recovered/);
  assert.equal(card.style.display, 'block');

  const detached = harness(); let complete;
  const old = { title: 'Old page', load: () => new Promise(resolve => { complete = resolve; }), render: value => detached.E('p', {}, value) };
  const oldRv = detached.view.render([old]), oldCard = oldRv.children[0].children[1];
  detached.advance(0); await tick(); oldCard.isConnected = false;
  complete('Stale'); await tick();
  assert.doesNotMatch(detached.text(oldCard), /Stale/, 'Late RPC must not redraw a detached page');

  const optional = harness();
  const optionalRv = optional.view.render([{ title: 'No device', render: () => null }]);
  optional.advance(0); await tick();
  assert.equal(optionalRv.children[0].style.display, 'none', 'Absent optional devices must disappear');
  console.log('Overview RPC tests passed: immediate skeleton, independent cards/cache, single request, delayed completion, retries, toggle, one-shot, detached page and optional cards');
})().catch(error => { console.error(error); process.exitCode = 1; });
