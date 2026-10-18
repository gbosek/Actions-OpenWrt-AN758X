#!/usr/bin/env python3
"""Check repeat installation, preservation of extroot config, and PHY errors."""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
scripts = repo / ('scripts' if (repo / 'scripts').exists() else 'Scripts')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kernel', type=Path)
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='xg2010g-boot-test-') as temporary:
    root = Path(temporary)
    (root/'target/linux/generic').mkdir(parents=True)
    version = root/'target/linux/generic/kernel-6.18'
    version.write_text('LINUX_VERSION-6.18 = .55\n')
    (root/'target/linux/airoha/patches-6.18').mkdir(parents=True)
    (root/'.config').write_text('# CONFIG_BUSYBOX_CONFIG_FEATURE_SYSLOG_INFO is not set\n')
    command = [sys.executable, str(scripts/'apply-boot-log-fixes.py'), str(root)]
    for _ in range(2):
        subprocess.run(command, check=True)
        assert (root/'.config').read_text().count('CONFIG_BUSYBOX_CONFIG_FEATURE_SYSLOG_INFO=y') == 1
        assert (root/'files/etc/config/fstab').read_bytes() == (repo/'Boot/root/etc/config/fstab').read_bytes()
    fstab = root/'files/etc/config/fstab'
    custom = "config global\nconfig mount\n option target '/overlay'\n option uuid 'preserve-me'\n"
    fstab.write_text(custom)
    subprocess.run(command, check=True)
    assert fstab.read_text() == custom, 'Existing extroot configuration overwritten'
    version.write_text('LINUX_VERSION-6.18 = .999\n')
    assert subprocess.run(command, capture_output=True).returncode != 0

    if args.kernel:
        source = (args.kernel/'drivers/net/phy/mediatek/mtk-ge-soc.c').read_text()
        function = re.search(r'static int an7581_phy_probe\(.*?\n\}', source, re.S)
        assert function and 'of_property_match_string' in function[0]
        stub = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define GFP_KERNEL 0
#define ENOMEM 12
#define IS_ERR(p) ((intptr_t)(p) < 0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct device { void *of_node; };
struct phy_device { struct { struct device dev; } mdio; void *priv; };
struct pinctrl { int unused; };
struct mtk_socphy_priv { int unused; };
static int state, failure, nomem, calls, errors;
static int of_property_match_string(void *n, const char *p, const char *s)
{ (void)n; (void)p; (void)s; return state; }
static struct pinctrl *devm_pinctrl_get_select(struct device *d, const char *s)
{ static struct pinctrl ok; (void)d; (void)s; calls++; return failure ? (void *)(intptr_t)failure : &ok; }
static int dev_err_probe(struct device *d, int e, const char *s)
{ (void)d; (void)s; errors++; return e; }
static void *devm_kzalloc(struct device *d, size_t n, int flags)
{ (void)d; (void)flags; return nomem ? NULL : calloc(1,n); }
'''
        cases = r'''
int main(void) {
    int states[] = {-22,0,0,0,-22};
    int failures[] = {0,0,-517,-5,0};
    int expected[] = {0,0,-517,-5,-ENOMEM};
    for (int i=0; i<5; i++) {
        struct phy_device phy = {0};
        state=states[i]; failure=failures[i]; nomem=(i==4); calls=errors=0;
        int result=an7581_phy_probe(&phy);
        if (result != expected[i] || calls != (state>=0) || errors != (failure!=0)) return 1;
        free(phy.priv);
    }
    puts("PASS: optional state absent, present, probe deferral, mux failure, allocation failure");
    return 0;
}
'''
        cfile, binary = root/'phy-test.c', root/'phy-test'
        cfile.write_text(stub + function[0] + cases)
        subprocess.run(['cc','-Wall','-Wextra','-Werror',str(cfile),'-o',str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
print('PASS: boot fix installation is repeatable; existing mounts preserved; unknown kernel rejected')
