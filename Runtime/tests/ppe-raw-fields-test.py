#!/usr/bin/env python3
"""Exercise the actually adapted PPE table renderer and raw/legacy entries."""
from pathlib import Path
import json, shutil, subprocess, sys, tempfile
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts'))
from adapt_npu import adapt
with tempfile.TemporaryDirectory(prefix='ppe-raw-fields-') as d:
    app=Path(d)/'luci-app-airoha-npu'
    shutil.copytree(R/'Packages/NPU/naoki/luci-app-airoha-npu',app)
    adapt(app,'naoki')
    source=(app/'htdocs/luci-static/resources/view/airoha_npu/status.js').read_text()
    helpers=source[source.index('function ppeCounterText('):source.index('function exportFullPpe(')]
    renderer=source[source.index('function ppeRows('):source.index('function renderPpeTable(')]
    script='''const assert=require('assert');
const helpers=HELPERS,renderer=RENDERER;
const E=(tag,attributes,children)=>({tag,attributes,children});
const rows=new Function('filteredPpeEntries','ppePage','PPE_SHOWN_MAX','aui','E','_',helpers+renderer+'return ppeRows;')(
 x=>x,0,50,{badge:x=>x},E,x=>x);
let cases=0;
const newFlow='203.0.113.1:123->198.51.100.2:443',eth='02:00:00:00:00:01->02:00:00:00:00:02';
function check(entry,flow,mac,vlan){
 const cells=rows([entry])[0].children;
 assert.strictEqual(cells[1].children,entry.state);assert.strictEqual(cells[4].children,entry.orig);
 assert.strictEqual(cells[5].children,flow);assert.strictEqual(cells[6].children,mac);assert.strictEqual(cells[3].children,vlan);cases++;
}
const common={index:'00308',type:'IPv4',proto:'5T',orig:'192.168.10.66:123->198.18.0.4:443',packets:null,bytes:null};
check({...common,state:'UNB',new_flow:null,eth:null,vlan:null,raw:{new_flow:newFlow,eth,vlan:'4094,0',packets:'441',bytes:'642437'}},newFlow,eth,'4094,0');
check({...common,state:'BND',new_flow:newFlow,eth,vlan:'0,0'},newFlow,eth,'0,0');
check({...common,state:'UNB',new_flow:newFlow,eth,vlan:'0,0'},newFlow,eth,'0,0');
const zero='00:00:00:00:00:00->00:00:00:00:00:00';
check({...common,state:'UNB',raw:{new_flow:'0.0.0.0:0->0.0.0.0:0',eth:zero,vlan:'0,0'}},'0.0.0.0:0->0.0.0.0:0',zero,'0,0');
check({...common,state:'UNB',raw:{new_flow:'',eth:null,vlan:''}},'-','-','-');
console.log(JSON.stringify({status:'passed',actual_renderer_cases:cases,scope:'Display only; no binding or exported validity change'}));
'''.replace('HELPERS',json.dumps(helpers)).replace('RENDERER',json.dumps(renderer))
    subprocess.run(['node','-'],input=script,text=True,check=True)
