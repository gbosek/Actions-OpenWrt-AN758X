const { test, expect } = require('@playwright/test');
const { defaultStatus, renderOverview } = require('./helpers/luci-rpc-mock');

function runtime(running) {
	const status = defaultStatus();
	status.diagnostics.service_running = running;
	return status;
}

test('stop confirms backend state immediately and start resumes without changing saved WAN config', async ({ page }) => {
	await renderOverview(page, { operatorAccess: true, status: runtime(true), controlStatus: { stop: runtime(false), start: runtime(true) } });
	const saved = await page.evaluate(() => window.__mwan4Mock.getUci());
	await expect(page.locator('#mwan4-command-center')).toContainText('Ready');
	await page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true }).click();
	await expect(page.locator('#mwan4-command-center .mwan4-pill')).toHaveText('Stopped');
	await expect(page.locator('#mwan4-command-center')).not.toContainText('2/2 online');
	await expect(page.getByText('MultiWAN 4 service stopped.', { exact: true })).toBeVisible();
	await page.getByRole('button', { name: 'Start MultiWAN 4 service', exact: true }).click();
	await expect(page.locator('#mwan4-command-center .mwan4-pill')).toHaveText('Ready');
	expect(await page.evaluate(() => window.__mwan4Mock.getUci())).toEqual(saved);
	const calls = await page.evaluate(() => window.__mwan4Mock.rpcCalls);
	expect(calls.filter(c => c.method == 'control').map(c => c.params[0])).toEqual(['stop', 'start']);
});

for (const response of [{ ok: false, errors: [{ message: 'teardown failed' }] }, {}]) {
	test('failed or unacknowledged stop cannot report success: ' + JSON.stringify(response), async ({ page }) => {
		await renderOverview(page, { operatorAccess: true, status: runtime(true), controlResult: response });
		await page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true }).click();
		await expect(page.getByText(/Control failed:/)).toBeVisible();
		await expect(page.locator('#mwan4-command-center .mwan4-pill')).toHaveText('Ready');
		await expect(page.getByText('MultiWAN 4 service stopped.', { exact: true })).toHaveCount(0);
		await expect(page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true })).toBeEnabled();
	});
}

test('transport failure is visible and unlocks the button', async ({ page }) => {
	await renderOverview(page, { operatorAccess: true, status: runtime(true), controlError: 'Permission denied' });
	await page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true }).click();
	await expect(page.getByText('Control failed: Permission denied')).toBeVisible();
	await expect(page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true })).toBeEnabled();
});

test('acknowledgement alone cannot claim stopped while procd still reports running', async ({ page }) => {
	await renderOverview(page, { operatorAccess: true, status: runtime(true) });
	await page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true }).click();
	await expect(page.getByText(/Control failed: Service did not reach/)).toBeVisible({ timeout: 10000 });
	await expect(page.getByText('MultiWAN 4 service stopped.', { exact: true })).toHaveCount(0);
});

test('a poll issued before stop cannot overwrite the confirmed stopped state', async ({ page }) => {
	await renderOverview(page, { operatorAccess: true, status: runtime(true), controlStatus: { stop: runtime(false) } });
	await page.evaluate(() => {
		window.__mwan4Mock.setStatusDelay(250);
		window.pendingPoll = window.__mwan4Mock.runPoll();
		window.__mwan4Mock.setStatusDelay(0);
	});
	await page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true }).click();
	await expect(page.locator('#mwan4-command-center .mwan4-pill')).toHaveText('Stopped');
	await page.evaluate(() => window.pendingPoll);
	await expect(page.locator('#mwan4-command-center .mwan4-pill')).toHaveText('Stopped');
});

test('viewer cannot issue a stop request', async ({ page }) => {
	await renderOverview(page, { operatorAccess: false, status: runtime(true) });
	await expect(page.getByRole('button', { name: 'Stop MultiWAN 4 service', exact: true })).toHaveCount(0);
	expect((await page.evaluate(() => window.__mwan4Mock.rpcCalls)).some(c => c.method == 'control')).toBe(false);
});
