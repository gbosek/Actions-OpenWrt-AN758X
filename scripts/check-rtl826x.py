#!/usr/bin/env python3
"""Check the pinned PHY source, actual reset/match functions and ARM64 objects."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from check_ppe_functions import find_kernel

REPO = Path(__file__).resolve().parents[1]


def function(text, name):
    m = re.search(r'^static int ' + re.escape(name) + r'\([^;]*?\)\s*\{', text, re.M)
    assert m, name
    end, depth = m.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[m.start():end]


FIXTURE = r'''
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MDIO_MMD_VEND1 30
#define MDIO_MMD_VEND2 31
#define RTL826X_VND2_INER 0xa424
#define RTL826X_VEND1_PKG_MODEL 0x103
#define RTL826X_VEND1_PKG_MODEL_8261 0x8261
#define RTL826X_VEND1_VERSION_ID 0x104
#define RTL826X_VEND1_VERSION_ID_MODEL 0xffc0
#define RTL826X_VEND1_VERSION_ID_MODEL_BE 0x1140
#define RTL_8261N 0x1ccaf3
#define BIT(x) (1u << (x))
#define phydev_err(...) do {} while (0)
struct phy_driver {int unused;};
struct mii_bus {bool read_c45;};
static struct mii_bus bus={true};
struct phy_device {struct {struct mii_bus *bus;} mdio;int calls,fail,release_fail,releases,patches,polarity,patch_error,polarity_error,last_delay,pkg,version,read_error,reset_requests;bool c45,asserted;};
static struct phy_device *active;
static int op(struct phy_device *p) {return ++p->calls==p->fail?-5:0;}
static int phy_write_mmd(struct phy_device *p,int m,int r,int v) {(void)m;(void)r;(void)v;return op(p);}
static int phy_set_bits_mmd(struct phy_device *p,int m,int r,int v) {(void)m;(void)r;(void)v;return op(p);}
static int phy_clear_bits_mmd(struct phy_device *p,int m,int r,int v) {
    (void)m;(void)v;int err=op(p);if(r==0x145 && ++p->releases<=p->release_fail)return -5;return err;
}
static void msleep(int n) {active->last_delay=n;}
static int rtlgen_phy_patch(struct phy_device *p) {if(p->last_delay!=150)abort();p->patches++;return p->patch_error;}
static int rtl826x_config_serdes_polarity(struct phy_device *p) {p->polarity++;return p->polarity_error;}
static bool rtlgen_is_c45_match(struct phy_device *p,int id,bool c45) {(void)id;(void)c45;return p->c45;}
static void phy_device_reset(struct phy_device *p,int value) {p->reset_requests++;p->asserted=value;}
static int phy_read_mmd(struct phy_device *p,int m,int r) {(void)m;if(p->asserted)return 0xffff;if(r==p->read_error)return -5;return r==0x103?p->pkg:p->version;}
'''
CASES = r'''
int main(void) {
    for(int i=0;i<8;i++) {
        struct phy_device p={0};active=&p;int expected=0;
        if(i>=1 && i<=3){p.fail=i;expected=-5;}
        if(i==4){p.release_fail=6;expected=-5;}
        if(i==5)p.release_fail=2;
        if(i==6){p.patch_error=-6;expected=-6;}
        if(i==7){p.polarity_error=-7;expected=-7;}
        int result=rtl826x_config_init(&p);
        if(result!=expected)abort();
        if(i>=1 && i<=4){if(p.patches || p.polarity)abort();}
        else {if(p.patches!=1 || p.polarity!=(i==6?0:1))abort();}
        if(i==5 && p.releases!=3)abort();
    }
    int models[]={0x8251,0x8254,0x8261,0x8264,0xffff},matches=0;
    for(int i=0;i<5;i++)for(int be=0;be<2;be++) {
        struct phy_device p={.mdio={&bus},.c45=true,.pkg=models[i],.version=be?0x1140:0};
        if(rtl8261be_match_phy_device(&p,NULL)!=(models[i]==0x8261 && be))abort();
        if(rtl8261n_match_phy_device(&p,NULL)!=(models[i]==0x8261 && !be))abort();
        matches++;
    }
    for(int i=0;i<3;i++) {
        struct phy_device p={.mdio={&bus},.c45=i!=2,.pkg=0x8261,.version=0x1140,.read_error=i==0?0x103:i==1?0x104:0};
        if(rtl8261be_match_phy_device(&p,NULL) || rtl8261n_match_phy_device(&p,NULL))abort();
        matches++;
    }
    for(int be=0;be<2;be++) {
        struct phy_device p={.mdio={&bus},.c45=true,.pkg=0x8261,.version=be?0x1140:0,.asserted=true};
        int actual=be?rtl8261be_match_phy_device(&p,NULL):rtl8261n_match_phy_device(&p,NULL);
        if(!actual || p.asserted || p.reset_requests!=1)abort();
        matches++;
    }
    bus.read_c45=false;
    struct phy_device no_c45={.mdio={&bus},.c45=true,.pkg=0x8261,.asserted=true};
    if(rtl8261be_match_phy_device(&no_c45,NULL) || rtl8261n_match_phy_device(&no_c45,NULL) || no_c45.reset_requests)abort();
    bus.read_c45=true;
    printf("{\"reset_cases\":8,\"match_cases\":%d,\"deferred_probe_reset_cases\":2,\"unsupported_bus_kept_in_reset\":true,\"failures\":0}",matches);
    return 0;
}
'''


def check(kernel, compiled=False, require_staged=False):
    meta = json.loads((REPO / 'PHY-RTL826X-SOURCE.json').read_text())
    hashes = {}
    for name, expected in meta['prepared_sources_sha256'].items():
        hashes[name] = hashlib.sha256((kernel / name).read_bytes()).hexdigest()
        assert hashes[name] == expected, 'Unexpected prepared PHY source: ' + name
    source = (kernel / meta['prepared_source']).read_text()
    probe = function(source, 'rtl826x_probe')
    for speed in ['100', '1000', '2500', '5000', '10000']:
        assert 'phy_disable_eee_mode(phydev, ETHTOOL_LINK_MODE_' + speed + 'baseT_Full_BIT)' in probe
    assert 'rtl826x_link_change_notify' in source and 'RTL826X_SDS_MAX_RESETS' in source
    assert source.count('data = rtl826x_read_pkg_model(phydev);') == 5
    body = '\n'.join(function(source, n) for n in ['rtl826x_config_init', 'rtl826x_read_pkg_model', 'rtl8261be_match_phy_device', 'rtl8261n_match_phy_device'])
    with tempfile.TemporaryDirectory(prefix='rtl826x-actual-functions-') as d:
        c, exe = Path(d) / 'test.c', Path(d) / 'test'
        c.write_text(FIXTURE + body + CASES)
        subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(c), '-o', str(exe)], check=True)
        cases = json.loads(subprocess.check_output([str(exe)], text=True))
    result = dict(cases, source_sha256=hashes, compiled_arm64=compiled,
                  upstream_commit=meta['commit'], match_reset_release=meta['match_reset_release'], hardware_tested=False)
    if compiled:
        objects = {}
        for name in ['realtek_main.o', 'phy_patch.o', 'phy_patch_rtl826x.o', 'realtek.o']:
            data = (kernel / 'drivers/net/phy/realtek' / name).read_bytes()
            assert data[:5] == b'\x7fELF\x02' and int.from_bytes(data[18:20], 'little') == 183, name
            objects[name] = hashlib.sha256(data).hexdigest()
        result['objects_sha256'] = objects
    if require_staged:
        assert compiled
        modules = list(kernel.parent.parent.glob('root-*/lib/modules/6.18.55/realtek.ko'))
        assert modules, 'No staged realtek.ko'
        digests = {hashlib.sha256(f.read_bytes()).hexdigest() for f in modules}
        assert len(digests) == 1, 'Conflicting staged PHY modules'
        result['staged_module_sha256'] = next(iter(digests))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel', type=Path)
    p.add_argument('--build-dir', type=Path)
    p.add_argument('--compiled', action='store_true')
    p.add_argument('--require-staged', action='store_true')
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    result = check(a.kernel or find_kernel(a.build_dir), a.compiled, a.require_staged)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
