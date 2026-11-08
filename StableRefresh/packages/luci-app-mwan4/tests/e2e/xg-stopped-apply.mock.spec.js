const {test,expect}=require('@playwright/test');
const {defaultStatus,renderOverview}=require('./helpers/luci-rpc-mock');

test('applying a rule while stopped saves configuration without starting the service',async({page})=>{
 const status=defaultStatus();status.diagnostics.service_running=false;
 await renderOverview(page,{operatorAccess:true,status,connections:null});
 await page.getByRole('button',{name:'Add routing rule',exact:true}).first().click();
 await page.locator('.modal input[name="label"]').fill('Office site');
 await page.locator('.modal textarea[name="what"]').fill('example.com');
 await page.getByRole('button',{name:'Preview changes',exact:true}).click();
 await page.getByRole('button',{name:'Apply pending changes',exact:true}).click();
 await expect(page.getByText('MultiWAN 4 settings applied. Service remains stopped.',{exact:true})).toBeVisible();
 expect((await page.evaluate(()=>window.__mwan4Mock.rpcCalls)).filter(x=>x.method==='control')).toEqual([]);
 const config=await page.evaluate(()=>window.__mwan4Mock.getUci());
 expect(config.mwan4.some(s=>s.label==='Office site'&&s.domain.includes('example.com'))).toBe(true);
});

test('runtime refresh reads status without issuing control or changing configuration',async({page})=>{
 const status=defaultStatus();status.diagnostics.service_running=false;
 await renderOverview(page,{operatorAccess:true,status,connections:null});
 const saved=await page.evaluate(()=>window.__mwan4Mock.getUci());
 await page.getByRole('button',{name:'Refresh MultiWAN 4 runtime',exact:true}).click();
 await expect(page.getByRole('button',{name:'Refresh MultiWAN 4 runtime',exact:true})).toBeEnabled();
 expect((await page.evaluate(()=>window.__mwan4Mock.rpcCalls)).filter(x=>x.method==='control')).toEqual([]);
 expect(await page.evaluate(()=>window.__mwan4Mock.getUci())).toEqual(saved);
 await expect(page.locator('#mwan4-command-center .mwan4-pill')).toHaveText('Stopped');
});
