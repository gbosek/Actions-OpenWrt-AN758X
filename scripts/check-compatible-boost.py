#!/usr/bin/env python3
"""Check the compiled kernel, runtime policy and actual FIT CPU OPPs."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def fdt(data):
    if len(data)<40 or data[:4]!=bytes.fromhex('d00dfeed'):
        raise ValueError('Not a flattened device tree')
    magic,total,off_struct,off_strings,_,_,_,_,size_strings,size_struct=struct.unpack_from('>10I',data)
    if total>len(data): raise ValueError('Truncated FDT')
    names=data[off_strings:off_strings+size_strings]
    pos=off_struct;stack=[];nodes={}
    while pos<off_struct+size_struct:
        token=struct.unpack_from('>I',data,pos)[0];pos+=4
        if token==1:
            end=data.index(0,pos);name=data[pos:end].decode();pos=(end+4)&~3
            stack.append(name);path='/'.join(stack) or '/';nodes[path]={}
        elif token==2:stack.pop()
        elif token==3:
            length,nameoff=struct.unpack_from('>II',data,pos);pos+=8
            end=names.index(0,nameoff);name=names[nameoff:end].decode()
            nodes['/'.join(stack) or '/'][name]=data[pos:pos+length];pos=(pos+length+3)&~3
        elif token==4:pass
        elif token==9:return nodes,total
        else:raise ValueError(f'Unknown FDT token: {token}')
    raise ValueError('No FDT end token')


def cells(value):
    assert len(value)%4==0
    return struct.unpack('>'+str(len(value)//4)+'I',value)


def board_from_fit(path):
    raw=path.read_bytes();nodes,total=fdt(raw)
    for node,props in nodes.items():
        if not node.startswith('/images/') or props.get('type',b'').rstrip(b'\0')!=b'flat_dt':continue
        assert props.get('compression',b'none\0').rstrip(b'\0')==b'none', 'Unexpected DT compression'
        if 'data' in props:data=props['data']
        else:
            size=cells(props['data-size'])[0]
            start=cells(props['data-position'])[0] if 'data-position' in props else ((total+3)&~3)+cells(props['data-offset'])[0]
            data=raw[start:start+size]
        return fdt(data)[0]
    raise ValueError('FIT has no board device tree')


def check_lan_leds(nodes):
    for index, color, function in [(0, 2, b'link'), (1, 4, b'activity')]:
        matches = [p for n,p in nodes.items() if n.endswith(f'/ethernet-phy@f/leds/led@{index}')]
        assert len(matches) == 1, 'Missing LAN3 PHY LED in actual FIT'
        led = matches[0]
        assert cells(led['reg']) == (index,) and cells(led['color']) == (color,)
        assert led['function'].rstrip(b'\0') == function


def check_board(nodes):
    assert b'gemtek,xg2010g' in nodes['/']['compatible'].split(b'\0'), 'Wrong board'
    phandles={cells(p['phandle'])[0]:n for n,p in nodes.items() if 'phandle' in p}
    cpus=[p for n,p in nodes.items() if re.match(r'^/cpus/cpu@[^/]+$',n)]
    assert len(cpus)==4, 'Not four CPU cores'
    tables={cells(p['operating-points-v2'])[0] for p in cpus}
    assert len(tables)==1, 'CPU OPP tables are not shared'
    table=phandles[next(iter(tables))];entries=[]
    for node,props in nodes.items():
        if not node.startswith(table+'/') or 'opp-hz' not in props:continue
        hz=cells(props['opp-hz']);assert len(hz)==2
        mhz=((hz[0]<<32)|hz[1])//1000000
        state_node=phandles[cells(props['required-opps'])[0]]
        state=cells(nodes[state_node]['opp-level'])[0]
        if mhz==1400:
            assert state==15 and 'turbo-mode' in props, '1400MHz must be turbo state15'
            assert cells(props['clock-latency-ns'])[0]==1000000000
        else:assert mhz==500+50*state and state<=14
        entries.append(mhz)
    assert sorted(entries)==list(range(500,1201,50))+[1400], ('Unexpected OPPs',entries)
    controller=[p for p in nodes.values() if 'gemtek,1400mhz-boost' in p]
    assert len(controller)==1 and 'airoha,force-direct-pll' not in controller[0]
    assert 'airoha,chip-scu' in controller[0]
    assert cells(controller[0]['reg'])==(0,0x1efbe000,0,0x1000)
    assert b'mcucfg' in controller[0]['reg-names'].split(b'\0')
    assert b'cpufreq.default_governor=powersave' in nodes['/chosen']['bootargs']
    check_lan_leds(nodes)
    return sorted(entries)


def check(root):
    kernels=[p.parent for p in (root/'build_dir').glob('target-*/linux-*/linux-6.18.*/.config') if (p.parent/'drivers/pmdomain/mediatek/airoha-cpu-pmdomain.c').exists()]
    assert len(kernels)==1, 'Expected one configured CPU-domain kernel'
    kernel=kernels[0];cfg=(kernel/'.config').read_text()
    for key in ('CONFIG_AIROHA_CPU_PM_DOMAIN','CONFIG_CPU_FREQ','CONFIG_CPU_FREQ_GOV_ONDEMAND','CONFIG_SMP'):
        assert re.search(rf'^{key}=y$',cfg,re.M),key
    driver=kernel/'drivers/pmdomain/mediatek'
    body=(driver/'airoha-cpu-pmdomain.c').read_text();helper=(driver/'xg2010g-cpu-boost.h').read_text()
    for marker in ('xg2010g_boost_set_state','boost_capable','boost_backend','boost_transitioning','gemtek,1400mhz-boost'):
        assert marker in body,marker
    for marker in ('stop_machine(xg2010g_pll_program','stop_machine(xg2010g_pll_finish','msleep(1000)','rollback failed','XG_BOOST_STATE 15'):
        assert marker in helper,marker
    binary=driver/'airoha-cpu-pmdomain.o'
    assert binary.is_file() and b'XG2010G compatibility boost backend: kernel-pll' in binary.read_bytes(), 'CPU compatibility driver not compiled'
    fits=list((root/'bin/targets/airoha/an7581').glob('*gemtek_xg2010g*sysupgrade*.itb'))
    assert len(fits)==1, 'Expected one XG2010G sysupgrade image'
    frequencies=check_board(board_from_fit(fits[0]))
    roots=list((root/'build_dir').glob('target-*/root-airoha'));assert len(roots)==1
    installed=roots[0]
    for rel in ('usr/libexec/xg2010g-cpu-policy','etc/init.d/cpufreq'):
        f=installed/rel;assert f.is_file() and f.stat().st_mode&0o111,rel
    repo=Path(__file__).resolve().parents[1]
    for rel,original in (('usr/libexec/xg2010g-cpu-policy','xg2010g-cpu-policy'),('etc/init.d/cpufreq','cpufreq.init')):
        assert (installed/rel).read_bytes()==(repo/'CPU/runtime'/original).read_bytes(), 'Stale shared CPU runtime: '+rel
    policy=(installed/'usr/libexec/xg2010g-cpu-policy').read_text()
    assert '1200000' in policy and '1400000' in policy and 'capable' in policy
    init=(installed/'etc/init.d/cpufreq').read_text()
    assert 'START=89' in init and 'xg2010g-cpu-policy apply' in init
    assert 'xg2010g-cpu-policy watch' not in init and 'procd_set_param respawn' not in init
    rpc=(installed/'usr/libexec/rpcd/luci.airoha_npu').read_text()
    assert 'xg2010g-cpu-policy set-max' in rpc and 'boost_backend' in rpc
    assert not re.search(r'\bdevmem\s+0x1(?:fa20|efbe)[0-9a-f]+\s+32\s',rpc), 'Direct userspace CPU PLL writes remain'
    meta=json.loads((installed/'etc/xg2010g-cpu-boost-source.json').read_text())
    patch=root/'target/linux/airoha/patches-6.18'/meta['kernel_patch']
    assert hashlib.sha256(patch.read_bytes()).hexdigest()==meta['kernel_patch_sha256']
    dts_patch=Path(__file__).resolve().parents[1]/'source-patches/airoha'/meta['source_dts_patch']
    assert hashlib.sha256(dts_patch.read_bytes()).hexdigest()==meta['source_dts_patch_sha256']
    print(f'Compatibility boost verified in {kernel.name}, CPU driver object, actual FIT {frequencies} MHz, and staged runtime')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args();check(a.source.resolve())
