// Render the shipped view with the firmware's actual Aurora/Argon CSS.
const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = process.env.PON_TEST_ROOT;
if (!root) throw new Error('PON_TEST_ROOT must point to the staged/extracted firmware root');
const ponSource = fs.readFileSync(process.env.PON_TEST_SOURCE || path.join(root, 'www/luci-static/resources/view/status/include/29a_xg2010g_pon.js'), 'utf8');
const systemSource = fs.readFileSync(path.join(root, 'www/luci-static/resources/view/status/include/10_system.js'), 'utf8');
const statusSource = fs.readFileSync(process.env.PON_TEST_STATUS || path.join(root, 'www/luci-static/resources/view/status/index.js'), 'utf8');

for (const theme of ['aurora', 'argon']) {
  for (const width of [1440, 390, 320]) {
    for (const compact of [false, true]) {
      test(`${theme} ${width}px ${compact ? 'compact' : 'spaced'} styles stay full width`, async ({ page }) => {
        await page.setViewportSize({ width, height: 1000 });
        await page.route('http://router.test/**', route => route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><html><body></body></html>' }));
        await page.goto('http://router.test/');
        await page.setContent('<body data-page="admin-status-overview"><div class="main"><div class="main-right"><main id="maincontent"><div class="container"><h2>状态</h2><div id="view"></div></div></main></div></div></body>');
        const css = theme === 'aurora' ? 'www/luci-static/aurora/main.css' : 'www/luci-static/argon/css/cascade.css';
        await page.addStyleTag({ content: fs.readFileSync(path.join(root, css), 'utf8') });
        await page.evaluate(({ ponSource, statusSource, systemSource, compact }) => {
          function E(tag, attrs, children) {
            if (Array.isArray(tag)) { children = tag; tag = null; attrs = {}; }
            if (typeof attrs !== 'object' || attrs == null || Array.isArray(attrs) || attrs instanceof Node) { children = attrs; attrs = {}; }
            const element = tag ? document.createElement(tag) : document.createDocumentFragment();
            for (const [key, value] of Object.entries(attrs)) {
              if (typeof value === 'function') element.addEventListener(key, value); else element.setAttribute(key, value);
            }
            function append(child) {
              if (Array.isArray(child)) child.forEach(append);
              else if (child instanceof Node) element.appendChild(child);
              else if (child != null) element.appendChild(document.createTextNode(String(child)));
            }
            append(children); return element;
          }
          const L = {
            bind: (fn, self, ...args) => fn.bind(self, ...args), isObject: v => v != null && typeof v === 'object',
            itemlist: (span, list) => { list.forEach((v, i) => { span.appendChild(E(i % 2 ? 'span' : 'strong', {}, v)); if (i % 2) span.appendChild(E('br')); }); return span; }
          };
          // Aurora has an important generic two-column rule for inline grid
          // styles. Whitespace/minification must not change the PON layout.
          if (compact) ponSource = ponSource.replaceAll('display: grid', 'display:grid');
          const pon = new Function('baseclass', 'fs', 'rpc', 'uci', 'L', 'E', '_', ponSource)(
            { extend: object => object }, {}, { declare: () => () => Promise.resolve({}) }, {}, L, E, text => text);
          const snapshot = [{ device: 'pon0', frontend: { rx_power_dbm: -16.74, tx_power_dbm: 6.42, temperature_celsius: 47.34, tx_bias_ma: 12.16, voltage_volts: 3.2758 }, line: { lifecycle: 'operational', active_mode: 'xgspon', optical_signal: true }, registration: { onu_state: 'O5' }, rate: { tx: 4.18, rx: 1.32 }, conns: { tcp: { total: 580, npu: 46 }, udp: { total: 447, npu: 38 } } }];
          pon.load = () => Promise.resolve(snapshot);
          window.ponSample = snapshot[0];
          const callbacks = [];
          const overview = new Function('view', 'dom', 'poll', 'fs', 'network', 'ui', 'L', 'E', '_', statusSource)(
            { extend: object => object }, { content: (node, content) => node.replaceChildren(content) }, { add: fn => callbacks.push(fn) }, {},
            { flushCache: () => Promise.resolve() }, { createHandlerFn: (self, name, ...args) => self[name].bind(self, ...args) }, L, E, text => text);
          const system = new Function('baseclass', 'fs', 'rpc', 'uci', 'L', 'E', '_', systemSource)(
            { extend: object => object }, {}, { declare: () => () => Promise.resolve({}) }, { get: () => null }, L, E, text => text);
          system.load = () => Promise.resolve([
            { hostname: 'XG2010G', model: 'Gemtek XG2010G', system: 'ARMv8', kernel: '6.18.55', release: { target: 'airoha/an7581', description: 'XG2010G' } },
            {}, { cpubench: '' }, { cpuinfo: 'ARMv8 · 4 cores' },
            { cpuusage: 'USR 4% · SYS 2%\nCPU0 10% · CPU1 4% · CPU2 2% · CPU3 1%' },
            { tempinfo: 'CPU 52.5°C · PON 46.3°C · LAN1 51°C · LAN2 48°C' }, { branch: 'LuCI', revision: 'fixed' }, 0
          ]);
          document.getElementById('view').replaceChildren(overview.render([system, pon]));
          window.pollPON = () => callbacks[0]();
        }, { ponSource, statusSource, systemSource, compact });

        const card = page.locator('.pon-horizontal-card');
        await expect(card).toBeVisible();
        await expect(page.locator('.cpu-sample-values')).toContainText('CPU3');
        await expect(page.locator('#view')).toContainText('52.5°C');
        const measure = () => page.evaluate(() => {
          const card = document.querySelector('.pon-horizontal-card');
          // The theme's network-status-table wrapper owns its normal gutters.
          const section = card.parentElement;
          const style = getComputedStyle(section);
          const cardStyle = getComputedStyle(card);
          return {
            card: card.getBoundingClientRect().width,
            available: section.getBoundingClientRect().width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight) - parseFloat(style.borderLeftWidth) - parseFloat(style.borderRightWidth) - parseFloat(cardStyle.marginLeft) - parseFloat(cardStyle.marginRight),
            font: parseFloat(getComputedStyle(card).fontSize),
            overflow: document.documentElement.scrollWidth > innerWidth,
            panels: [...card.querySelectorAll('.ifacebox')].map(e => e.getBoundingClientRect().toJSON())
          };
        });
        async function assertLayout() {
          const size = await measure();
          expect(Math.abs(size.card - size.available)).toBeLessThan(2);
          expect(size.overflow).toBe(false);
          for (const panel of size.panels) {
            expect(panel.width).toBeGreaterThan(0);
            expect(panel.right).toBeLessThanOrEqual(width + 1);
          }
        }
        await assertLayout();
        await expect(card).toContainText('-16.74 dBm');
        await expect(card).toContainText('3.2758 V');
        await expect(card).toContainText('O5 运行状态');
        await expect(card).toContainText('收光功率 Rx · 1577 nm');
        await expect(card).toContainText('4.18');
        await expect(card).toContainText('发光功率 Tx · 1270 nm');
        // Fast downloads create longer values; failures must stay readable too.
        await page.evaluate(() => { window.ponSample.rate = { tx: 281.18, rx: 311.32 }; return window.pollPON(); });
        await assertLayout();
        await expect(card).toContainText('311.32');
        await page.evaluate(() => { window.savedOptics = window.ponSample.frontend; window.ponSample.frontend = { error: '读取失败（设备不可用）' }; return window.pollPON(); });
        await assertLayout();
        await page.evaluate(() => { window.ponSample.frontend = window.savedOptics; window.ponSample.rate = { tx: 4.18, rx: 1.32 }; return window.pollPON(); });
        await assertLayout();
        // A normal poll and a section hide/show must not restore a small box.
        await page.evaluate(() => window.pollPON());
        await expect(page.locator('.pon-horizontal-card')).toHaveCount(1);
        const toggle = card.locator('xpath=ancestor::div[contains(@class,"cbi-section")]').locator('[data-indicator="poll-status"]');
        await toggle.click();
        await expect(card).toBeHidden();
        await toggle.click();
        await page.evaluate(() => window.pollPON());
        await expect(card).toBeVisible();
        await assertLayout();
        // Theme switching/dark mode and responsive resizing reuse the same DOM.
        await page.emulateMedia({ colorScheme: 'dark' });
        await page.evaluate(() => document.body.setAttribute('data-darkmode', 'true'));
        await assertLayout();
        if (process.env.PON_TEST_SCREENSHOTS) {
          fs.mkdirSync(process.env.PON_TEST_SCREENSHOTS, { recursive: true });
          await page.screenshot({ path: path.join(process.env.PON_TEST_SCREENSHOTS, `${theme}-${width}-${compact ? 'compact' : 'spaced'}.png`), animations: 'disabled', fullPage: true });
        }
      });
    }
  }
}
