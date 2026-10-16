// Render the shipped view with the firmware's actual Aurora/Argon CSS.
const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = process.env.PON_TEST_ROOT;
if (!root) throw new Error('PON_TEST_ROOT must point to the staged/extracted firmware root');
const ponSource = fs.readFileSync(process.env.PON_TEST_SOURCE || path.join(root, 'www/luci-static/resources/view/status/include/15_xg2010g_pon.js'), 'utf8');
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
        await page.evaluate(({ ponSource, statusSource, compact }) => {
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
          const snapshot = [{ device: 'pon0', frontend: { rx_power_dbm: -16.74, tx_power_dbm: 6.42, temperature_celsius: 47.34, tx_bias_ma: 12.16, voltage_volts: 3.2758 }, rate: { tx: 4.18, rx: 1.32 }, conns: { tcp: { total: 580, npu: 46 }, udp: { total: 447, npu: 38 } } }];
          pon.load = () => Promise.resolve(snapshot);
          const callbacks = [];
          const overview = new Function('view', 'dom', 'poll', 'fs', 'network', 'ui', 'L', 'E', '_', statusSource)(
            { extend: object => object }, { content: (node, content) => node.replaceChildren(content) }, { add: fn => callbacks.push(fn) }, {},
            { flushCache: () => Promise.resolve() }, { createHandlerFn: (self, name, ...args) => self[name].bind(self, ...args) }, L, E, text => text);
          const system = { title: '系统', render: () => E('table', { class: 'table' }, E('tr', {}, [E('td', {}, '主机名'), E('td', {}, 'ponwrt')])) };
          document.getElementById('view').replaceChildren(overview.render([system, pon]));
          window.pollPON = () => callbacks[0]();
        }, { ponSource, statusSource, compact });

        const card = page.locator('.pon-optics-card');
        await expect(card).toBeVisible();
        const measure = () => page.evaluate(() => {
          const card = document.querySelector('.pon-optics-card');
          const section = card.closest('.cbi-section');
          const style = getComputedStyle(section);
          return {
            card: card.getBoundingClientRect().width,
            available: section.getBoundingClientRect().width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight) - parseFloat(style.borderLeftWidth) - parseFloat(style.borderRightWidth),
            font: parseFloat(getComputedStyle(card).fontSize),
            overflow: document.documentElement.scrollWidth > innerWidth,
            optics: card.querySelector('.pon-optics-values').getBoundingClientRect().toJSON(),
            rates: card.querySelector('.pon-optics-top').lastElementChild.getBoundingClientRect().toJSON()
          };
        });
        async function assertLayout() {
          const size = await measure();
          expect(Math.abs(size.card - size.available)).toBeLessThan(2);
          expect(size.font).toBeGreaterThanOrEqual(14);
          expect(size.overflow).toBe(false);
          expect(size.rates.left).toBeGreaterThanOrEqual(size.optics.right);
          expect(Math.abs(size.rates.top - size.optics.top)).toBeLessThan(2);
          expect(size.rates.bottom).toBeLessThanOrEqual(size.optics.bottom + 2);
        }
        await assertLayout();
        await expect(card).toContainText('-16.74 dBm');
        await expect(card).toContainText('3.2758 V');
        await expect(card).toContainText('580');
        await expect(card).toContainText('447');
        await expect(card).toContainText('4.18');
        await expect(card.locator('header')).toHaveText('PON');
        // A normal poll and a section hide/show must not restore a small box.
        await page.evaluate(() => window.pollPON());
        await expect(page.locator('.pon-optics-card')).toHaveCount(1);
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
