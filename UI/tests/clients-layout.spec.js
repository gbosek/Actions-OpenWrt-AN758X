// Exercise the shipped chart renderer and theme styles at phone/desktop widths.
const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = process.env.PON_TEST_ROOT;
if (!root) throw new Error('PON_TEST_ROOT must point to the staged/extracted firmware root');
const assets = path.join(root, 'www/luci-static/resources/view/status/clients');
const source = fs.readFileSync(path.join(assets, 'overview.js'), 'utf8');

for (const theme of ['aurora', 'argon']) {
  for (const width of [390, 1440, 3840]) {
    test(`clients ${theme} ${width}px compact chart and hover`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.setContent('<html data-argon-mode="dark"><body><main id="maincontent"><div id="view"></div></main></body></html>');
      const css = theme === 'aurora' ? 'www/luci-static/aurora/main.css' : 'www/luci-static/argon/css/cascade.css';
      await page.addStyleTag({ content: fs.readFileSync(path.join(root, css), 'utf8') });
      await page.addStyleTag({ content: fs.readFileSync(path.join(assets, 'clients.css'), 'utf8') });
      await page.evaluate(source => {
        String.prototype.format = function(...values) {
          let i = 0;
          return this.replace(/%s/g, () => String(values[i++]));
        };
        function E(tag, attrs, children) {
          const el = document.createElement(tag);
          for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
          function append(v) {
            if (Array.isArray(v)) v.forEach(append);
            else if (v instanceof Node) el.appendChild(v);
            else if (v != null) el.appendChild(document.createTextNode(String(v)));
          }
          append(children); return el;
        }
        const common = {
          ensureStylesheet() {}, SAMPLE_INTERVAL: 5, TICK_INTERVAL: 1,
          formatRate: v => `${v} B/s`, formatSize: v => `${v} B`, formatCount: String
        };
        const chart = new Function('dom', 'poll', 'ui', 'common', 'L', 'E', '_', source)(
          { content: (node, contents) => node.replaceChildren(...contents) }, { add() {} }, {}, common,
          { Class: { extend: object => object }, bind: (fn, self) => fn.bind(self) }, E, text => text);
        const now = Date.now();
        chart.store = {
          state: {}, clients: () => [], bridgeRates: () => null, liveScopes: () => null, pushTrend() {},
          trend: [100, 200, 300].map((rate, i) => ({ t: now - (2 - i) * 1000, wanUp: rate, wanDown: rate / 2 }))
        };
        document.getElementById('view').appendChild(chart.render());
        window.chartUnderTest = chart;
      }, source);
      const svg = page.locator('.clients-chart__svg');
      await expect(svg).toBeVisible();
      // The pane is first rendered detached. Its next-frame fit must fill the
      // screen without magnifying labels, even before the first poll.
      await expect.poll(() => svg.evaluate(el => Math.abs(el.viewBox.baseVal.width - el.clientWidth))).toBeLessThan(2);
      const measure = () => svg.evaluate(el => ({
        height: el.getBoundingClientRect().height,
        labelHeight: el.querySelector('text').getBoundingClientRect().height,
        overflow: document.documentElement.scrollWidth > innerWidth
      }));
      expect((await measure()).height).toBeLessThanOrEqual(230);
      expect((await measure()).labelHeight).toBeLessThan(18);
      expect((await measure()).overflow).toBe(false);
      const box = await svg.boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      const tip = svg.locator('..').locator(':scope > div');
      await expect(tip).toBeVisible();
      await expect(tip).toContainText('200 B/s');
      await expect(tip).toContainText('100 B/s');
      const tipBox = await tip.boundingBox();
      expect(tipBox.x).toBeGreaterThanOrEqual(box.x - 1);
      expect(tipBox.x + tipBox.width).toBeLessThanOrEqual(box.x + box.width + 1);
      // A normal data refresh remeasures resized panels, without installing
      // a persistent window listener or a resize observer per poll.
      await page.setViewportSize({ width: width === 390 ? 1440 : 390, height: 900 });
      await page.evaluate(() => window.chartUnderTest.update());
      expect((await measure()).height).toBeLessThanOrEqual(230);
      await expect.poll(() => svg.evaluate(el => Math.abs(el.viewBox.baseVal.width - el.clientWidth))).toBeLessThan(2);
      await page.evaluate(() => { window.chartUnderTest.store.trend = []; window.chartUnderTest.renderChart(); });
      await expect(page.locator('.clients-chart__empty')).toBeVisible();
      expect(await page.locator('.clients-chart__empty').evaluate(el => el.getBoundingClientRect().height)).toBeLessThanOrEqual(230);
    });
  }
}
