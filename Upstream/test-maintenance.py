#!/usr/bin/env python3
"""Patch round trips and actual FDB callback behavior, without router changes."""
import hashlib,json,re,subprocess,tempfile,shutil,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1]; kernel=Path(sys.argv[1])
meta=json.loads((repo/'Offload/SOURCE.json').read_text())
patches=sorted((repo/'Upstream/patches').glob('*.patch'))
names=set()
for p in patches:names.update(re.findall(r'^\+\+\+ b/(.+)$',p.read_text(),re.M))
with tempfile.TemporaryDirectory(prefix='xg-upstream-') as d:
    root=Path(d)
    for n in names:
        dst=root/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(kernel/n,dst)
    for direction,items in [('-R',list(reversed(patches))),('-N',patches)]:
        for patch in items:
            proc=subprocess.run(['patch','--batch','--fuzz=0','-p1',direction,'-i',str(patch)],cwd=root,capture_output=True,text=True)
            assert proc.returncode==0,(patch.name,proc.stdout,proc.stderr)
    for n in names:assert (root/n).read_bytes()==(kernel/n).read_bytes(),n
    # Compile the real prepared callback, including aged-out FDB behavior and PVID.
    source=(kernel/'net/bridge/br_nf_utils.c').read_text()
    body=source[source.index('static bool nf_br_fdb_valid_dst'):source.index('static const struct nf_br_utils')]
    prefix=r'''
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
typedef unsigned short u16;
struct net_bridge { bool vlan; };
struct net_bridge_port { struct net_bridge *br; u16 pvid; };
struct net_device { struct net_bridge_port *port; };
struct net_bridge_fdb_entry { struct net_bridge_port *dst; };
static struct net_bridge_fdb_entry *fdb;
static u16 lookup_vid;
#define BROPT_VLAN_ENABLED 1
#define READ_ONCE(x) (x)
static struct net_bridge_port *br_port_get_check_rcu(const struct net_device *d) {return d->port;}
static bool br_opt_get(struct net_bridge *b,int ignored) {(void)ignored;return b->vlan;}
static const struct net_bridge_port *nbp_vlan_group_rcu(const struct net_bridge_port *p) {return p;}
static u16 br_get_pvid(const struct net_bridge_port *p) {return p->pvid;}
static struct net_bridge_fdb_entry *br_fdb_find_rcu(struct net_bridge *b,const unsigned char *a,u16 v) {(void)b;(void)a;lookup_vid=v;return fdb;}
'''
    tests=r'''
int main(void) {
 struct net_bridge b={0};struct net_bridge_port p={&b,42},q={&b,77};
 struct net_device dev={&p};struct net_bridge_fdb_entry f={&p};unsigned char mac[6]={2};
 fdb=&f;assert(nf_br_fdb_valid_dst(&dev,mac,0));assert(lookup_vid==0);
 f.dst=&q;assert(!nf_br_fdb_valid_dst(&dev,mac,0));
 fdb=NULL;assert(nf_br_fdb_valid_dst(&dev,mac,0));
 b.vlan=true;assert(nf_br_fdb_valid_dst(&dev,mac,0));assert(lookup_vid==42);
 assert(nf_br_fdb_valid_dst(&dev,mac,123));assert(lookup_vid==123);
 dev.port=NULL;assert(!nf_br_fdb_valid_dst(&dev,mac,123));
 puts("FDB callback: 9 assertions passed");return 0;
}
'''
    c=root/'fdb-test.c';c.write_text(prefix+body+tests)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(c),'-o',str(root/'test')],check=True)
    subprocess.run([str(root/'test')],check=True)
print('PASS: exact fuzz=0 reverse/reapply round trip; prepared FDB destination/PVID callback')
