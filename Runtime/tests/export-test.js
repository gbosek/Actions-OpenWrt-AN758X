const fs=require('fs'),path=require('path'),assert=require('assert');
const runtime=path.join(__dirname,'..');
const source=fs.readFileSync(path.join(runtime,'ppe-view.js'),'utf8');
const fragment=source.slice(source.indexOf('function exportFullPpe'),source.indexOf('function ppeCountText'));
let clicked=0,notified=0,blob=null;
const document={body:{appendChild(){}},createElement(){return{click(){clicked++},remove(){}}}};
const URL={createObjectURL(value){blob=value;return 'blob:test';},revokeObjectURL(){}};
const ui={addNotification(){notified++;}},E=(...args)=>args;
const factory=rpc=>new Function('callPpeExport','document','URL','Blob','ui','E','setTimeout',fragment+'return exportFullPpe;')(rpc,document,URL,Blob,ui,E,fn=>fn());
(async()=>{
 const button={disabled:false};let calls=0;
 await factory(async(token,offset)=>{
  assert(token===(calls?'ABCDEF':''));assert(offset===calls*128);calls++;
  const count=Math.min(128,300-offset);
  return{available:true,total:300,returned:count,offset,next_offset:offset+count,has_more:offset+count<300,
   export_id:'ABCDEF',captured_at:123,truncated:true,entries:Array.from({length:count},(_,i)=>({index:offset+i}))};
 })({currentTarget:button});
 assert(clicked===1&&calls===3&&!button.disabled);
 const full=JSON.parse(await blob.text());assert(full.entries.length===300&&full.truncated===false);
 assert(new Set(full.entries.map(x=>x.index)).size===300);
 await factory(async()=>({available:true,total:300,returned:1,offset:0,next_offset:1,has_more:false,
   export_id:'ABCDEF',captured_at:123,entries:[{}]}))({currentTarget:button});
 assert(clicked===1&&notified===1&&!button.disabled);
 calls=0;
 await factory(async(token,offset)=>({available:true,total:2,returned:1,offset,next_offset:offset+1,has_more:offset===0,
   export_id:++calls===1?'ABCDEF':'GHIJKL',captured_at:123,entries:[{}]}))({currentTarget:button});
 assert(clicked===1&&notified===2&&!button.disabled);
 console.log('PASS: bounded RPC pages assemble one complete snapshot; incomplete/mixed snapshots rejected; button restored after errors');
})().catch(e=>{console.error(e);process.exitCode=1;});
