#!/usr/bin/env python3
"""Run actual DT parser against binary fixtures, without a boot log."""
from pathlib import Path
import tempfile,struct,json,subprocess,os,shlex
R=Path(__file__).resolve().parents[1];app=R/'Packages/NPU/naoki/luci-app-airoha-npu'
helper=app/'root/usr/libexec/airoha-npu-memory';ucode=os.environ.get('UCODE_BIN') or 'ucode'
def write(p,*values):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(struct.pack('>'+'I'*len(values),*values))
with tempfile.TemporaryDirectory(prefix='npu-memory-') as d:
    root=Path(d);mem=root/'reserved-memory';reg=mem/'npu-binary@84000000';npu=root/'soc/npu@1e900000'
    write(mem/'#address-cells',2);write(mem/'#size-cells',2);write(reg/'phandle',51);write(npu/'memory-region',51);write(reg/'reg',0,0x84000000,0,0xa00000)
    def run():return json.loads(subprocess.check_output([ucode,str(helper),str(root)],text=True))
    out=run();assert out==[{'name':'npu-binary','start':'0x84000000','end':'0x849fffff','size':'10240 KiB'}],out
    # Another valid reserve is not NPU-owned and must never be summed.
    write(mem/'qdma@87000000/phandle',52);write(mem/'qdma@87000000/reg',0,0x87000000,0,0x2000000)
    assert run()==out
    write(reg/'reg',1,0,0,4096);assert run()[0]['start']=='0x100000000'
    write(mem/'#address-cells',1);write(mem/'#size-cells',1);write(reg/'reg',0x84000000,0xa00000);assert run()==out
    write(reg/'reg',0x84000000,0);assert run()==[]
    (reg/'reg').write_bytes(b'\0\1');assert run()==[]
    write(reg/'reg',0x84000000,0xa00000);write(npu/'memory-region',99);assert run()==[]
    write(npu/'memory-region',51);(reg/'phandle').rename(reg/'linux,phandle');assert run()==out
    write(reg/'reg',0x84000000,1024,0x85000000,2048);assert len(run())==2
    write(mem/'#address-cells',3);assert run()==[]
    write(mem/'#address-cells',1);write(reg/'reg',0x84000000,0xa00000)
    rpc=(app/'root/usr/libexec/rpcd/luci.airoha_npu').read_text()
    block=rpc[rpc.index('\t# DT is authoritative'):rpc.index('\t# === CPU Frequency Status ===')]
    wrapper=root/'reader';wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(ucode)+' '+shlex.quote(str(helper))+' '+shlex.quote(str(root))+'\n');wrapper.chmod(0o755)
    block=block.replace('/usr/libexec/airoha-npu-memory',str(wrapper)).replace('/tmp/npu-mem-regions',str(root/'mem'))
    shell='dmesg() { :; }\nread_regions() {\n'+block+'\nprintf "%s" "$regions"\n}\nread_regions\n'
    def cached():return json.loads(subprocess.check_output(['sh','-c',shell],text=True))
    (root/'mem.json').write_text('[]')  # old bad cache, no boot log
    assert cached()==out
    assert (root/'mem-v2.json').exists()
    (root/'mem-v2.json').unlink();write(npu/'memory-region',99)
    assert cached()==[] and not (root/'mem-v2.json').exists()
    write(npu/'memory-region',51);assert cached()==out
rpc=(app/'root/usr/libexec/rpcd/luci.airoha_npu').read_text()
assert 'local mem_cache="/tmp/npu-mem-regions-v2.json"' in rpc
assert 'regions=$(/usr/libexec/airoha-npu-memory 2>/dev/null)' in rpc
assert '[ "$regions" != \'[]\' ] && mem_tmp=' in rpc
assert 'root/usr/libexec/airoha-npu-memory $(1)/usr/libexec/' in (app/'Makefile').read_text()
print('PASS actual NPU parser/RPC cache: phandle ownership, 1/2 cells, >4GiB, malformed/zero, multiple tuples, old-empty-cache recovery, retry after failed discovery, no boot log')
