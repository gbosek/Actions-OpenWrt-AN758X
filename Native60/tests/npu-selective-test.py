#!/usr/bin/env python3
"""Compile actual prepared helper bodies; stubs model path discovery, not hardware."""
from pathlib import Path
import argparse, subprocess, tempfile, json, hashlib

q=argparse.ArgumentParser();q.add_argument('kernel',type=Path);q.add_argument('--report',type=Path);a=q.parse_args()
p=a.kernel/'drivers/net/ethernet/airoha/airoha_ppe.c';source=p.read_text()
def function(name):
    pos=source.index(name+'(');begin=source.rfind('\nstatic ',0,pos)+1
    start=source.index('{',pos);depth=1;end=start+1
    while depth:
        depth += (source[end]=='{')-(source[end]=='}');end+=1
    return source[begin:end]

c=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <arpa/inet.h>
typedef uint32_t u32; typedef uint16_t __be16;
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define ETH_P_8021Q 0x8100
#define ETH_P_8021AD 0x88a8
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define IS_ERR(p) ((intptr_t)(p)<0)
#define DEV_PATH_PPPOE 1
#define DEV_PATH_VLAN 2
#define DEV_PATH_ETHERNET 3
#define DEV_PATH_BRIDGE 4
struct net_device { int id, refs; };
struct net_device_path {
 int type; const struct net_device *dev;
 struct { unsigned short id, proto; unsigned char h_dest[6]; } encap;
};
struct net_device_path_stack { int num_paths; struct net_device_path path[8]; };
struct airoha_flow_data {
 struct { uint8_t num; struct { unsigned short id, proto; } hdr[2]; } vlan;
 struct { uint8_t num; unsigned short sid; } pppoe;
 struct { unsigned char h_dest[6]; } eth;
};
static struct net_device_path_stack fixture;
static int path_error, rcu_depth, tests;
static struct net_device ppp={1,0}, pon={2,0}, ethernet={3,0};
static int dev_fill_forward_path(const struct net_device *dev,const unsigned char *mac,struct net_device_path_stack *s)
{ assert(dev==&ppp); assert(mac[0]==0x20); assert(rcu_depth==1); *s=fixture; return path_error; }
static void rcu_read_lock(void) { assert(!rcu_depth); rcu_depth++; }
static void rcu_read_unlock(void) { assert(rcu_depth==1); rcu_depth--; }
static bool ether_addr_equal(const unsigned char *a,const unsigned char *b) { return !memcmp(a,b,6); }
static void dev_hold(struct net_device *d) { d->refs++; }
static void dev_put(struct net_device *d) { d->refs--; assert(d->refs==0); }
'''
c+='\n'.join(function(n) for n in ['airoha_ppe_vlan_vpm','airoha_ppe_vlan_push_ok','airoha_ppe_pppoe_lower_dev'])
c+=r'''
static struct airoha_flow_data setup(int tagged,struct net_device *lower)
{
 struct airoha_flow_data d={0}; memset(&fixture,0,sizeof(fixture));path_error=0;
 d.pppoe.num=1;d.pppoe.sid=71;d.eth.h_dest[0]=0x20;
 fixture.num_paths=tagged+2;
 fixture.path[0].type=DEV_PATH_PPPOE;fixture.path[0].dev=&ppp;
 fixture.path[0].encap.id=71;fixture.path[0].encap.h_dest[0]=0x20;
 if(tagged) { d.vlan.num=1; d.vlan.hdr[0].id=41;d.vlan.hdr[0].proto=htons(ETH_P_8021Q);
 fixture.path[1].type=DEV_PATH_VLAN;fixture.path[1].encap.id=41;fixture.path[1].encap.proto=htons(ETH_P_8021Q); }
 fixture.path[tagged+1].type=DEV_PATH_ETHERNET;fixture.path[tagged+1].dev=lower;
 return d;
}
static void expect(struct airoha_flow_data d,struct net_device *want)
{
 struct net_device *got=airoha_ppe_pppoe_lower_dev(&ppp,&d);
 assert(rcu_depth==0);
 if(want) { assert(got==want);assert(want->refs==1);dev_put(got); }
 else { assert(IS_ERR(got));assert(!pon.refs && !ethernet.refs); }
 tests++;
}
int main(void)
{
 struct airoha_flow_data d={0};
 assert(airoha_ppe_vlan_vpm(&d)==0);tests++;
 assert(airoha_ppe_vlan_push_ok(&d,htons(ETH_P_8021Q)));tests++;
 assert(airoha_ppe_vlan_push_ok(&d,htons(ETH_P_8021AD)));tests++;
 assert(!airoha_ppe_vlan_push_ok(&d,htons(0x9100)));tests++;
 d.vlan.num=1;d.vlan.hdr[0].proto=htons(ETH_P_8021Q);
 assert(airoha_ppe_vlan_vpm(&d)==1);tests++;
 assert(airoha_ppe_vlan_push_ok(&d,htons(ETH_P_8021Q)));tests++;
 assert(airoha_ppe_vlan_push_ok(&d,htons(ETH_P_8021AD)));tests++;
 d.vlan.hdr[0].proto=htons(ETH_P_8021AD);
 assert(airoha_ppe_vlan_vpm(&d)==2);tests++;
 assert(!airoha_ppe_vlan_push_ok(&d,htons(ETH_P_8021Q)));tests++;
 d.vlan.num=2;d.vlan.hdr[0].proto=htons(ETH_P_8021Q);d.vlan.hdr[1].proto=htons(ETH_P_8021Q);
 assert(airoha_ppe_vlan_vpm(&d)==1);tests++;
 d.vlan.hdr[1].proto=htons(ETH_P_8021AD);
 assert(airoha_ppe_vlan_vpm(&d)==2);tests++;
 assert(!airoha_ppe_vlan_push_ok(&d,htons(ETH_P_8021Q)));tests++;
 d=setup(0,&pon);expect(d,&pon);
 d=setup(1,&pon);expect(d,&pon);
 d=setup(0,&ethernet);expect(d,&ethernet);
 d=setup(1,&ethernet);expect(d,&ethernet);
 d=setup(0,&pon);d.pppoe.sid=72;expect(d,NULL);
 d=setup(0,&pon);d.eth.h_dest[1]=1;expect(d,NULL);
 d=setup(1,&pon);d.vlan.hdr[0].id=42;expect(d,NULL);
 d=setup(1,&pon);d.vlan.hdr[0].proto=htons(ETH_P_8021AD);expect(d,NULL);
 d=setup(1,&pon);d.vlan.num=0;expect(d,NULL);
 d=setup(0,&pon);d.vlan.num=1;expect(d,NULL);
 d=setup(0,&pon);fixture.path[1].type=DEV_PATH_BRIDGE;expect(d,NULL);
 d=setup(0,&pon);path_error=-1;expect(d,NULL);
 d=setup(0,&pon);fixture.num_paths=1;expect(d,NULL);
 d=setup(0,&pon);fixture.path[1].dev=NULL;expect(d,NULL);
 d=setup(0,&pon);d.pppoe.num=0;expect(d,NULL);
 d=setup(0,&pon);d.pppoe.num=2;expect(d,NULL);
 d=setup(0,&pon);d.pppoe.sid=0;expect(d,NULL);
 d=setup(0,&pon);fixture.path[0].dev=&ethernet;expect(d,NULL);
 d=setup(0,&pon);fixture.path[0].type=DEV_PATH_BRIDGE;expect(d,NULL);
 d=setup(0,&pon);fixture.num_paths=3;fixture.path[2].type=DEV_PATH_ETHERNET;fixture.path[2].dev=&ethernet;expect(d,NULL);
 printf("%d helper cases passed\n",tests);return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
    f=Path(t)/'test.c';exe=Path(t)/'test';f.write_text(c)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(f),'-o',str(exe)],check=True)
    output=subprocess.check_output([str(exe)],text=True).strip()
result={'status':'passed','cases':int(output.split()[0]),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'scope':'Actual helper bodies, mocked kernel path discovery; not network/hardware/runtime race validation'}
if a.report:a.report.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
