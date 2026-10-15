#!/usr/bin/env python3
"""Run the prepared firewall4's actual offload functions against network fixtures.

--source is the prepared/installed fw4.uc. --unpatched optionally supplies the
baseline source and proves that it fails the same PPPoE anchor regression case.
Use a host ucode interpreter; no router, nftables or hardware is accessed.
"""
import argparse, json, os, subprocess, tempfile
from pathlib import Path

def function(source, name):
    start = source.index('function ' + name + '(')
    end = source.index('\n}', start) + 2
    return source[start:end]

def method(source, name):
    start = source.index('\t' + name + ': function() {')
    end = source.index('\n\t},', start) + 4
    return source[start:end]

prefix = r'''
let tree = {"br-lan":["lower_lan1","lower_lan2"], "lan1":[], "lan2":[], "pon0":[], "pppoe-wan":[], "ct-wanup":["lower_pon0"], "ct-wanup-b":["lower_pon0"]};
let devstatus = {"br-lan":{devtype:"bridge"}, "ct-wanup":{devtype:"vlan"}, "ct-wanup-b":{devtype:"vlan"}, "pppoe-wan":{devtype:"ppp"}};
let fs = {
 opendir: function(path) {
  let name = replace(path, "/sys/class/net/", "");
  if (!exists(tree, name)) return null;
  let i = 0;
  return {read:function(){ return tree[name][i++]; },close:function(){}};
 },
 access:function(path){ return exists(tree, replace(path, "/sys/class/net/", "")); }
};
let ubus = {connect:function(){return {call:function(){return devstatus;},disconnect:function(){}};}};
let hw_ok = true;
function nft_try_hw_offload(devices) {return hw_ok;}
'''

suffix = r'''
let anchor = [{device:"ct-wanup"}];
let zones = [{related_physdevs:["br-lan","pppoe-wan"],device:anchor}];
let defaults = {flow_offloading_hw:true,flow_offloading:true};
fw4.state = {defaults};
fw4.default_option = function(name){ return defaults[name]; };
fw4.zones = function(){ return zones; };
fw4.warn = function(message){};
let count = 0;
function check(condition, message) {if(!condition) die(message+"\n"); count++;}
let result = fw4.resolve_offload_devices();
check(index(result,"pon0")>=0 && index(result,"lan1")>=0 && index(result,"ct-wanup")<0,"VLAN anchor must resolve to physical PON");
zones[0].device = [ ...anchor, {device:"ct-wanup-b"}, {device:"ct-wanup"} ];
result = fw4.resolve_offload_devices();
check(length(filter(result,x=>x=="pon0"))==1,"two WAN anchors must deduplicate the shared PON");
devstatus["ct-wanup"].devtype="bridge";
result=fw4.resolve_offload_devices();
check(index(result,"pon0")>=0,"untagged bridge anchor must resolve to PON");
zones[0].device=[{device:"pon0",invert:true},{device:"pon0",any:true},{device:"ct-wanup+"},"pon0"];
result=fw4.resolve_offload_devices();
check(index(result,"pon0")<0,"inverted, wildcard, any and nonparsed entries must not become anchors");
zones[0].device=anchor; defaults.flow_offloading_hw=false;
result=fw4.resolve_offload_devices();
check(index(result,"ct-wanup")>=0,"software mode must retain explicit existing zone device");
defaults.flow_offloading_hw=true; hw_ok=false;
result=fw4.resolve_offload_devices();
check(defaults.flow_offloading_hw==false && index(result,"ct-wanup")>=0,"hardware refusal must retain software fallback");
defaults.flow_offloading=false;
check(length(fw4.resolve_offload_devices())==0,"offload disabled must stay disabled");
defaults.flow_offloading=true; defaults.flow_offloading_hw=true; hw_ok=true; zones[0].device=[];
result=fw4.resolve_offload_devices();
check(index(result,"lan1")>=0 && index(result,"pon0")<0,"original zone.network behavior must stay intact");
print({cases:count,failed:0},"\n");
'''

if __name__ == '__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,required=True)
 parser.add_argument('--ucode',default='ucode')
 parser.add_argument('--unpatched',type=Path)
 args=parser.parse_args()
 source=args.source.read_text()
 code=prefix+function(source,'to_array')+'\n'+function(source,'resolve_lower_devices')+'\n'+function(source,'zone_offload_devices')
 code+='\nlet fw4 = {\n'+method(source,'resolve_hw_offload_devices')+'\n'+method(source,'resolve_offload_devices')+'\n};\n'+suffix
 with tempfile.TemporaryDirectory(prefix='fw4-zone-offload-test-') as directory:
  fixture=Path(directory)/'test.uc';fixture.write_text(code)
  result=json.loads(subprocess.check_output([args.ucode,str(fixture)],text=True))
  assert result=={'cases':8,'failed':0},result
  if args.unpatched:
   before=args.unpatched.read_text()
   code=code.replace(method(source,'resolve_hw_offload_devices'),method(before,'resolve_hw_offload_devices')).replace(method(source,'resolve_offload_devices'),method(before,'resolve_offload_devices'))
   fixture.write_text(code)
   negative=subprocess.run([args.ucode,str(fixture)],capture_output=True,text=True)
   assert negative.returncode and 'VLAN anchor must resolve' in negative.stderr,negative
   result['negative_control']='reproduced missing physical PON'
  print(json.dumps(result))
