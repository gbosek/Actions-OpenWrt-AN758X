#!/usr/bin/env python3
"""Run real prepared control/lifecycle functions; inspect compiled AArch64 output."""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'scripts'))
from check_ppe_functions import find_kernel, check as old_regressions

def function(text, name):
    m = re.search(r'^(?:static\s+)?(?:bool|void|int|struct net_device \*)[\s\n]*'+re.escape(name)+r'\([^;]*?\)\s*\{', text, re.M)
    assert m, name
    i = m.end(); depth = 1
    while depth:
        if text[i] == '{': depth += 1
        if text[i] == '}': depth -= 1
        i += 1
    return text[m.start():i]

PREFIX = r'''
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <arpa/inet.h>
#include <linux/ip.h>
#include <linux/ipv6.h>
#include <linux/udp.h>
#include <linux/tcp.h>
#include <linux/if_ether.h>
typedef uint32_t u32;
typedef uint64_t u64;
typedef uint8_t u8;
typedef uint16_t __be16;
struct vlan_hdr { uint16_t h_vlan_TCI, h_vlan_encapsulated_proto; };
struct net_device { bool bridge, vlan; struct net_device *master, *real; uint8_t dev_addr[6]; };
struct sk_buff { uint8_t *head, *tail, *mac; struct net_device *dev; };
static bool netif_is_bridge_master(struct net_device *d) { return d->bridge; }
static struct net_device *netdev_master_upper_dev_get_rcu(struct net_device *d) {return d->master;}
static bool is_vlan_dev(struct net_device *d) {return d->vlan;}
static struct net_device *vlan_dev_real_dev(struct net_device *d) {return d->real;}
static bool skb_mac_header_was_set(const struct sk_buff *s) {return s->mac != NULL;}
static struct ethhdr *eth_hdr(const struct sk_buff *s) {return (struct ethhdr *)s->mac;}
static uint8_t *skb_tail_pointer(const struct sk_buff *s) {return s->tail;}
static bool is_valid_ether_addr(const uint8_t *a) { static uint8_t z[6]; return !(a[0]&1) && memcmp(a,z,6); }
static bool ether_addr_equal_64bits(const uint8_t *a,const uint8_t *b) {return !memcmp(a,b,6);}
static void rcu_read_lock(void) {}
static void rcu_read_unlock(void) {}
static bool eth_type_vlan(uint16_t p) {return p==htons(ETH_P_8021Q)||p==htons(ETH_P_8021AD);}
static bool ip_is_fragment(const struct iphdr *p) {return ntohs(p->frag_off)&0x3fff;}
#define AIROHA_FOE_IB1_BIND_STATE 0x30000000u
#define AIROHA_FOE_STATE_INVALID 0
#define FIELD_PREP(m,v) ((v) << __builtin_ctz(m))
struct airoha_foe_entry {u32 ib1;};
struct fake_eth {void *dev;};
struct airoha_ppe {struct fake_eth *eth; void *foe; u32 bridge_ft_refs; u64 bridge_generation; bool bridge_fallback_fault; unsigned long *bridge_fallback;};
static int ppe_lock, lock_depth, commits, yields, fail_hash=-1;
static void spin_lock_bh(int *p) {(void)p; if(lock_depth++) abort();}
static void spin_unlock_bh(int *p) {(void)p; if(--lock_depth) abort();}
static u32 airoha_ppe_get_total_num_entries(struct airoha_ppe *p) {(void)p;return 8;}
static u32 airoha_ppe_get_total_sram_num_entries(struct airoha_ppe *p) {(void)p;return 4;}
static int test_bit(u32 b,unsigned long *p) {return !!(*p&(1ul<<b));}
static void __clear_bit(u32 b,unsigned long *p) {*p &= ~(1ul<<b);}
static int airoha_ppe_foe_commit_sram_entry(struct airoha_ppe *p,u32 h) {(void)p;commits++;return (int)h==fail_hash?-110:0;}
static void cond_resched(void) {if(lock_depth)abort();yields++;}
#define for_each_set_bit(b,p,n) for((b)=0;(b)<(n);(b)++) if(test_bit((b),(p)))
#define wmb() do {} while(0)
#define dev_warn(...) do {} while(0)
static int cases;
#define check(x) do {cases++; if(!(x)){fprintf(stderr,"case %d line %d failed\n",cases,__LINE__);exit(1);}}while(0)
'''
TESTS = r'''
int main(void) {
    uint8_t buffer[256]={0};
    uint8_t *frame=buffer+2;
    struct net_device bridge={.bridge=true,.dev_addr={2,1,1,1,1,1}};
    struct net_device port={.master=&bridge,.dev_addr={2,2,2,2,2,2}};
    struct sk_buff skb={.head=frame,.tail=frame+14+20+20,.mac=frame,.dev=&port};
    struct ethhdr *eh=(struct ethhdr *)frame;
    eh->h_source[0]=2;eh->h_dest[0]=4;eh->h_proto=htons(ETH_P_IP);
    struct iphdr *ip=(struct iphdr *)(frame+14);
    ip->version=4;ip->ihl=5;ip->protocol=IPPROTO_UDP;
    struct udphdr *udp=(struct udphdr *)(frame+14+20);
    udp->source=htons(50000);udp->dest=htons(443);
    check(!airoha_ppe_foe_skb_is_local(&skb));
    check(!airoha_ppe_foe_bridge_control(&skb));
    int ports[]={67,68,546,547};
    for(int i=0;i<4;i++) {udp->dest=htons(ports[i]);check(airoha_ppe_foe_bridge_control(&skb));udp->dest=htons(443);udp->source=htons(ports[i]);check(airoha_ppe_foe_bridge_control(&skb));}
    udp->source=htons(50000);ip->protocol=IPPROTO_TCP;
    check(!airoha_ppe_foe_bridge_control(&skb));
    skb.tail=frame+14+20+4;check(airoha_ppe_foe_bridge_control(&skb));skb.tail=frame+14+20+20;
    ip->frag_off=htons(0x2000);check(airoha_ppe_foe_bridge_control(&skb));ip->frag_off=0;
    memcpy(eh->h_dest,port.dev_addr,6);check(airoha_ppe_foe_skb_is_local(&skb));
    memcpy(eh->h_dest,bridge.dev_addr,6);check(airoha_ppe_foe_skb_is_local(&skb));
    memset(eh->h_dest,0xff,6);check(airoha_ppe_foe_skb_is_local(&skb));
    memset(eh->h_dest,0,6);eh->h_dest[0]=4;
    skb.dev=NULL;check(airoha_ppe_foe_skb_is_local(&skb));skb.dev=&port;
    skb.mac=NULL;check(airoha_ppe_foe_skb_is_local(&skb));skb.mac=frame;
    eh->h_proto=htons(ETH_P_ARP);check(airoha_ppe_foe_bridge_control(&skb));
    eh->h_proto=htons(ETH_P_IPV6);
    struct ipv6hdr *ip6=(struct ipv6hdr *)(frame+14);memset(ip6,0,sizeof(*ip6));ip6->version=6;ip6->nexthdr=IPPROTO_UDP;
    skb.tail=frame+14+40+20;udp=(struct udphdr *)(frame+14+40);udp->source=htons(50000);udp->dest=htons(443);
    check(!airoha_ppe_foe_bridge_control(&skb));udp->dest=htons(547);check(airoha_ppe_foe_bridge_control(&skb));
    ip6->nexthdr=IPPROTO_ICMPV6;check(airoha_ppe_foe_bridge_control(&skb));
    ip6->nexthdr=0;check(airoha_ppe_foe_bridge_control(&skb));
    struct airoha_foe_entry table[8];for(int i=0;i<8;i++)table[i].ib1=0x20000000u;
    unsigned long bits=(1ul<<1)|(1ul<<6); struct fake_eth eth={0};
    struct airoha_ppe p={.eth=&eth,.foe=table,.bridge_ft_refs=2,.bridge_fallback=&bits};
    airoha_ppe_flowtable_ref(&p,false);check(p.bridge_ft_refs==1 && bits && commits==0);
    airoha_ppe_flowtable_ref(&p,false);check(p.bridge_ft_refs==0 && bits==0 && commits==1 && yields==2);
    check(table[1].ib1==0 && table[6].ib1==0 && table[3].ib1==0x20000000u);
    airoha_ppe_flowtable_ref(&p,false);check(p.bridge_ft_refs==0);
    airoha_ppe_flowtable_ref(&p,true);airoha_ppe_flowtable_ref(&p,true);check(p.bridge_ft_refs==2);
    p.bridge_ft_refs=1;bits=(1ul<<1)|(1ul<<2);commits=0;fail_hash=1;
    airoha_ppe_flowtable_ref(&p,false);check(p.bridge_ft_refs==0 && p.bridge_fallback_fault && commits==1 && bits==6);
    check(lock_depth==0);
    printf("{\"cases\":%d,\"failed\":0}\n",cases);return 0;
}
'''

def check(kernel, compiled=False, images=None):
    ppe = (kernel/'drivers/net/ethernet/airoha/airoha_ppe.c').read_text()
    eth = (kernel/'drivers/net/ethernet/airoha/airoha_eth.c').read_text()
    markers = ['br_vlan_get_info_rcu(ingress, ctx.vlan[0].id', 'egress == ingress',
               'AIROHA_PRIV_F_PON', 'BR_STATE_FORWARDING', 'BR_ISOLATED',
               '__dev_fill_forward_path(&ctx', 'ppe->bridge_ft_refs &&', '__set_bit(hash, ppe->bridge_fallback)',
               'offsetof(struct airoha_foe_l2b, data)']
    for marker in markers: assert marker in ppe, marker
    assert 'type == TC_SETUP_FT' in eth and 'bool flowtable)' in eth
    wrapper = function(ppe, 'airoha_ppe_foe_commit_subflow_entry')
    assert wrapper.index('hlist_add_head') < wrapper.index('return airoha_ppe_foe_commit_subflow'), 'ACK failure loses parent cleanup ownership'
    body = '\n'.join(function(ppe,n) for n in ['airoha_ppe_foe_get_bridge_master_rcu','airoha_ppe_foe_skb_is_local','airoha_ppe_foe_bridge_control','airoha_ppe_flowtable_ref'])
    with tempfile.TemporaryDirectory(prefix='naoki-offload-test-') as d:
        c = Path(d)/'checks.c'; binary = Path(d)/'checks'
        c.write_text(PREFIX+body+TESTS)
        subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True)
        result = json.loads(subprocess.check_output([str(binary)],text=True))
    result['retained_regressions'] = old_regressions(kernel)
    from bridge_safety import check as safety_check
    result['safety_regressions'] = safety_check(kernel, function)
    result['scope'] = 'Prepared source checks and real function fixtures, not hardware/packet-path validation'
    metadata = json.loads((REPO/'Offload/SOURCE.json').read_text())
    result['source_sha256'] = {n:hashlib.sha256((kernel/n).read_bytes()).hexdigest() for n in metadata['expected_prepared_sources']}
    mismatch = {name: {'expected': metadata['expected_prepared_sources'].get(name), 'actual': digest}
                for name, digest in result['source_sha256'].items()
                if digest != metadata['expected_prepared_sources'].get(name)}
    assert result['source_sha256'] == metadata['expected_prepared_sources'], \
        'Prepared implementation differs from the reviewed patch set: ' + json.dumps(mismatch, sort_keys=True)
    result['patches'] = metadata['patches']
    if compiled:
        result['compiled_objects'] = {}
        for n in ['drivers/net/ethernet/airoha/airoha_ppe.o','drivers/net/ethernet/airoha/airoha_eth.o','drivers/net/ethernet/airoha/airoha_ppe_debugfs.o','drivers/net/ethernet/airoha/airoha_npu.o','net/core/dev.o','net/netfilter/core.o','net/bridge/br_vlan.o','net/bridge/br_if.o']:
            raw=(kernel/n).read_bytes();assert raw[:4]==b'\x7fELF' and raw[18:20]==b'\xb7\0', n
            result['compiled_objects'][n]=hashlib.sha256(raw).hexdigest()
        for name,symbol in [('drivers/net/ethernet/airoha/airoha_ppe.o',' T airoha_ppe_flowtable_ref'),('drivers/net/ethernet/airoha/airoha_eth.o',' U airoha_ppe_flowtable_ref'),('net/core/dev.o',' T __dev_fill_forward_path'),
                            ('drivers/net/ethernet/airoha/airoha_ppe.o',' T airoha_ppe_bridge_boot_gate'),
                            ('drivers/net/ethernet/airoha/airoha_ppe_debugfs.o',' U airoha_ppe_bridge_boot_gate'),
                            ('drivers/net/ethernet/airoha/airoha_ppe.o',' U nf_register_hook_observer'),
                            ('drivers/net/ethernet/airoha/airoha_ppe.o',' U br_vlan_is_forwarding_rcu'),
                            ('drivers/net/ethernet/airoha/airoha_ppe.o',' U br_offload_state_sync'),
                            ('net/netfilter/core.o',' T nf_register_hook_observer'),
                            ('net/bridge/br_vlan.o',' T br_vlan_is_forwarding_rcu'),
                            ('net/bridge/br_if.o',' T br_offload_state_sync')]:
            assert symbol in subprocess.check_output(['nm',str(kernel/name)],text=True), name
        image=kernel.parent/'Image'
        result['kernel_image_sha256']=hashlib.sha256(image.read_bytes()).hexdigest() if image.is_file() else None
        result['kernel_image_role']='KDIR/Image: normal sysupgrade input, not mutable arch/arm64/boot/Image'
        arch=kernel/'arch/arm64/boot/Image'
        result['diagnostic_arch_image_sha256']=hashlib.sha256(arch.read_bytes()).hexdigest() if arch.is_file() else None
        if images:
            from packaged_kernel import check as packaged_check
            result['packaged_images']=packaged_check(kernel.parent,images)
            assert result['packaged_images']['sysupgrade']['input_sha256']==result['kernel_image_sha256']
    result['hardware_tested']=False
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--kernel',type=Path);g.add_argument('--build-dir',type=Path)
    p.add_argument('--compiled',action='store_true');p.add_argument('--report',type=Path)
    p.add_argument('--images',type=Path,help='Require exact normal/recovery kernel identity against final FITs')
    a=p.parse_args()
    assert not a.images or a.compiled,'Packaged-image verification requires compiled-object checks'
    result=check(a.kernel or find_kernel(a.build_dir),a.compiled,a.images)
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
