const {test,expect}=require('@playwright/test');
const {defaultUci,renderOverview}=require('./helpers/luci-rpc-mock');

for(const [name,extra] of [
 ['MAC',{src_mac:['02:00:00:00:00:11']}],
 ['domain',{domain:['example.com']}],
 ['DSCP',{dscp:'46'}],
 ['protocol',{proto:'tcp'}],
 ['plain catch-all',{}]
]) {
 test(`custom 0/0 ${name} rule stays named, editable and movable`,async({page})=>{
  const uci=defaultUci();
  uci.mwan4.unshift({'.name':'custom_pin','.type':'rule','.index':-1,label:'My custom rule',dest_ip:['0.0.0.0/0'],use_strategy:'failover',enabled:'1',...extra});
  await renderOverview(page,{uci});
  const row=page.locator('[data-rule="custom_pin"]');
  await expect(row).not.toHaveClass(/is-default/);
  await expect(row).toContainText('My custom rule');
  await expect(row.getByRole('button',{name:'Edit routing rule My custom rule',exact:true})).toBeVisible();
  await expect(row.getByRole('checkbox')).toBeVisible();
  await row.getByRole('button',{name:'Edit routing rule My custom rule',exact:true}).click();
  await expect(page.locator('.modal input[name="label"]')).toHaveValue('My custom rule');
 });
}

test('reserved default name with a MAC condition stays a custom rule',async({page})=>{
 const uci=defaultUci();
 Object.assign(uci.mwan4.find(s=>s['.name']==='default_rule_v4'),{src_mac:['02:00:00:00:00:11'],label:'Specific device'});
 await renderOverview(page,{uci});
 await expect(page.locator('[data-rule="default_rule_v4"]')).not.toHaveClass(/is-default/);
 await expect(page.getByRole('button',{name:'Edit routing rule Specific device',exact:true})).toBeVisible();
 await expect(page.locator('[data-rule="default_rule_v6"]')).toHaveClass(/is-default/);
});
