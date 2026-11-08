const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const text=fs.readFileSync(path.join(__dirname,'../htdocs/luci-static/resources/view/mwan4/network/overview.js'),'utf8');
const begin=text.indexOf('function isGeneratedDefaultRule(');
let end=text.indexOf('{',begin)+1,depth=1;
while(depth){depth+=(text[end]==='{')-(text[end]==='}');end++;}
const classify=Function('return ('+text.slice(begin,end)+')')();
let cases=0;
function check(rule,expected){assert.equal(classify(rule),expected,JSON.stringify(rule));cases++;}
for(const dest of ['0.0.0.0/0','::/0',['0.0.0.0/0'],['::/0']]) {
 check({'.name':'my_catchall',dest_ip:dest},false);
 check({'.name':'default_rule_v4',dest_ip:dest},true);
 for(const extra of [{src_mac:['02:00:00:00:00:11']},{domain:['example.com']},{dscp:'46'},{dscp:'0'},{proto:'tcp'},{src_ip:['192.0.2.1']},{src_iface:'guest'},{dest_port:'443'},{src_port:'1024'},{ipset:'test_set'}]) {
  check({'.name':'custom',dest_ip:dest,...extra},false);
  check({'.name':'default_rule_v4',dest_ip:dest,...extra},false);
 }
}
check(null,false);check({},false);
check({'.name':'default_rule_v6',domain:[],src_mac:[],src_ip:[],proto:'all',dest_ip:['::/0']},true);
check({'.name':'default_rule_v4',dest_ip:'203.0.113.0/24'},false);
console.log(`PASS: ${cases} real classifier cases; catch-all conditions stay editable and only genuine generated defaults are read-only`);
