module.exports = {
  testDir: __dirname,
  testMatch: 'pon-layout.spec.js',
  workers: 1,
  timeout: 20000,
  reporter: 'line',
  use: { browserName: 'chromium', headless: true, screenshot: 'only-on-failure' },
  outputDir: process.env.PON_TEST_OUTPUT || '/tmp/xg2010g-pon-layout-results'
};
