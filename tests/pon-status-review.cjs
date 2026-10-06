'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../packages/luci-app-pon-status/htdocs/luci-static/resources/view/status/include/15_pon.js'), 'utf8');
let deviceStats = {};
let sysfsStats = {};
let sections = [];
const rpc = { declare: () => async () => deviceStats };
const api = new Function('baseclass', 'fs', 'rpc', 'uci', 'L', '_', 'window', source.replace('return baseclass.extend({', 'return { metric, netRate, sampleNet, getSources: () => statsSource, view: baseclass.extend({').replace(/\}\);\s*$/, '}) };'))(
  { extend: value => value },
  {
    trimmed: async name => { if (!(name in sysfsStats)) throw new Error('unavailable'); return sysfsStats[name]; },
    exec: async () => ({ stdout: 'tcp_total=0\ntcp_npu=0\nudp_total=0\nudp_npu=0\n' }),
    exec_direct: async () => JSON.stringify({ schema_version: 1, frontend: { rx_power_dbm: -18.2 } })
  },
  rpc,
  { load: async () => null, sections: () => sections },
  { resolveDefault: (p, fallback) => Promise.resolve(p).catch(() => fallback), isObject: value => value !== null && typeof value === 'object' },
  value => value,
  { setTimeout: callback => callback() }
);
(async () => {
  for (const invalid of [null, undefined, '', '  ', false, true, [], {}, Infinity, NaN])
    assert.equal(api.metric({ x: invalid }, 'x', 'V', 2), '不支持');
  assert.equal(api.metric({ x: 0 }, 'x', 'V', 2), '0.00 V');
  assert.equal(api.metric({ x: '3.30' }, 'x', 'V', 2), '3.30 V');
  assert.equal(api.netRate({ rx: 100, tx: 100, t: 1 }, { rx: 10, tx: 150, t: 2 }), null);
  assert.equal(api.netRate({ rx: 100, tx: 100, t: 1 }, { rx: 150, tx: 150, t: 1 }), null);
  assert.equal(api.netRate({ rx: 0, tx: 0, t: 0 }, { rx: 1048576, tx: 2097152, t: 1000 }).rx, 8);
  sysfsStats = { '/sys/class/net/pon0/statistics/rx_bytes': '10', '/sys/class/net/pon0/statistics/tx_bytes': '20' };
  assert.equal((await api.sampleNet('pon0')).rx, 10);
  deviceStats = { pon1: { statistics: { rx_bytes: 30, tx_bytes: 40 } } };
  assert.equal((await api.sampleNet('pon1')).rx, 30);
  assert.equal(api.getSources().pon0, 'sysfs');
  assert.equal(api.getSources().pon1, 'ubus');
  sysfsStats = {};
  deviceStats.pon0 = { statistics: { rx_bytes: 50, tx_bytes: 60 } };
  assert.equal((await api.sampleNet('pon0')).rx, 50);
  sections = [{ device: 'pon0' }, { device: 'pon0' }, { device: '../invalid' }, { device: 123 }];
  assert.equal((await api.view.load()).length, 1);
  sections = [{ device: 'constructor' }];
  deviceStats.constructor = { statistics: { rx_bytes: 10, tx_bytes: 20 } };
  assert.equal((await api.view.load())[0].device, 'constructor');
  sections = [];
  assert.equal((await api.view.load())[0].device, 'pon0');
  console.log('PASS: optical values, counter reset, rate calculation, per-port sources, fallback recovery, device filtering and deduplication');
})().catch(error => { console.error(error); process.exitCode = 1; });
