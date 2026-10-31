#!/usr/bin/env python3
"""Compile real prepared functions and exercise path rejection and VLAN keys."""
from pathlib import Path
import subprocess,tempfile,sys
K=Path(sys.argv[1]);t=(K/'net/netfilter/nf_flow_table_path.c').read_text()
body=t[t.index('struct nft_forward_info {'):t.index('static bool nft_flowtable_find_dev')]
ip=(K/'net/netfilter/nf_flow_table_ip.c').read_text();encap=ip[ip.index('static void nf_flow_tuple_encap'):ip.index('struct nf_flowtable_ctx')]
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <arpa/inet.h>
#undef htons
#undef ntohs
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define htons(x) ((uint16_t)((((uint16_t)(x)&255)<<8)|((uint16_t)(x)>>8)))
#else
#define htons(x) ((uint16_t)(x))
#endif
#define ntohs(x) htons(x)
typedef uint8_t u8; typedef uint16_t __u16; typedef uint16_t __be16;
#define ETH_ALEN 6
#define NF_FLOW_TABLE_ENCAP_MAX 2
#define BIT(x) (1u<<(x))
#define VLAN_VID_MASK 0xfff
#define ETH_P_8021Q 0x8100
#define ETH_P_PPP_SES 0x8864
enum flow_offload_xmit_type { FLOW_OFFLOAD_XMIT_NEIGH, FLOW_OFFLOAD_XMIT_DIRECT };
enum { DEV_PATH_ETHERNET,DEV_PATH_DSA,DEV_PATH_MTK_WDMA,DEV_PATH_VLAN,DEV_PATH_PPPOE,DEV_PATH_BRIDGE };
enum { DEV_PATH_BR_VLAN_UNTAG_HW,DEV_PATH_BR_VLAN_KEEP_HW,DEV_PATH_BR_VLAN_TAG,DEV_PATH_BR_VLAN_UNTAG,DEV_PATH_BR_VLAN_KEEP };
struct net_device { unsigned char dev_addr[6]; };
struct net_device_path { int type;const struct net_device *dev;struct {uint16_t id,proto;unsigned char h_dest[6];} encap;struct {int vlan_mode;uint16_t vlan_id,vlan_proto;} bridge;};
struct net_device_path_stack { int num_paths;struct net_device_path path[8];};
struct nf_flowtable { bool hw; };
static bool nf_flowtable_hw_offload(struct nf_flowtable *f){return f->hw;}
static bool nft_is_valid_ether_device(const struct net_device *d){return d!=NULL;}
static bool is_zero_ether_addr(const unsigned char *p){unsigned char z[6]={0};return !memcmp(p,z,6);}
struct vlan_ethhdr { uint16_t h_vlan_TCI; };
struct pppoe_hdr { uint16_t sid; };
struct sk_buff { bool tag;uint16_t vlan_tci,vlan_proto,protocol;struct vlan_ethhdr vlan;struct pppoe_hdr ppp;};
struct flow_offload_tuple {struct {uint16_t id,proto;} encap[2];};
static bool skb_vlan_tag_present(struct sk_buff *s){return s->tag;}
static uint16_t skb_vlan_tag_get_id(struct sk_buff *s){return s->vlan_tci & VLAN_VID_MASK;}
static void *skb_mac_header(struct sk_buff *s){return &s->vlan;}
static void *skb_network_header(struct sk_buff *s){return &s->ppp;}
'''
tests=r'''
int main(void){
 struct net_device dev={{2}};struct nf_flowtable ft={1};unsigned char ha[6]={4};
 struct net_device_path_stack s={.num_paths=1,.path={{.type=DEV_PATH_ETHERNET,.dev=&dev}}};
 struct nft_forward_info f={0};assert(!nft_dev_path_info(&s,&f,ha,&ft));assert(f.hw_outdev==&dev);
 s.path[0].type=99;f=(struct nft_forward_info){0};assert(nft_dev_path_info(&s,&f,ha,&ft)==-ENOENT);
 s.num_paths=0;assert(nft_dev_path_info(&s,&f,ha,&ft)==-ENOENT);
 s.num_paths=1;s.path[0].type=DEV_PATH_VLAN;f=(struct nft_forward_info){.num_encaps=2};assert(nft_dev_path_info(&s,&f,ha,&ft)==-ENOENT);
 s.path[0].type=DEV_PATH_BRIDGE;
 for(int mode=DEV_PATH_BR_VLAN_UNTAG_HW;mode<=DEV_PATH_BR_VLAN_KEEP;mode++){
   s.path[0].bridge.vlan_mode=mode;f=(struct nft_forward_info){.indev=&dev,.num_encaps=(mode==DEV_PATH_BR_VLAN_TAG||mode==DEV_PATH_BR_VLAN_KEEP_HW)?2:0};
   int r=nft_dev_path_info(&s,&f,ha,&ft);assert((mode==DEV_PATH_BR_VLAN_KEEP)==(r==0));
 }
 s.num_paths=3;s.path[0]=(struct net_device_path){.type=DEV_PATH_BRIDGE,.dev=&dev,.bridge={.vlan_mode=DEV_PATH_BR_VLAN_KEEP}};
 s.path[1]=(struct net_device_path){.type=DEV_PATH_VLAN,.dev=&dev,.encap={42,ETH_P_8021Q,{0}}};
 s.path[2]=s.path[0];f=(struct nft_forward_info){.indev=&dev};assert(!nft_dev_path_info(&s,&f,ha,&ft));assert(f.port_vlans==0&&f.num_encaps==1);
 s.num_paths=1;s.path[0]=(struct net_device_path){.type=DEV_PATH_PPPOE,.dev=&dev,.encap={65530,ETH_P_PPP_SES,{6}}};f=(struct nft_forward_info){0};assert(!nft_dev_path_info(&s,&f,ha,&ft));assert(f.encap[0].id==65530&&f.h_dest[0]==6);
 for(unsigned pcp=0;pcp<8;pcp++)for(unsigned dei=0;dei<2;dei++){
   struct sk_buff skb={.tag=true,.vlan_tci=(pcp<<13)|(dei<<12)|42,.vlan_proto=htons(ETH_P_8021Q),.protocol=htons(ETH_P_8021Q),.vlan={htons((pcp<<13)|(dei<<12)|77)}};
   struct flow_offload_tuple tuple={0};nf_flow_tuple_encap(&skb,&tuple);assert(tuple.encap[0].id==42&&tuple.encap[1].id==77);
 }
 struct sk_buff skb={.protocol=htons(ETH_P_PPP_SES),.ppp={htons(65530)}};struct flow_offload_tuple tuple={0};nf_flow_tuple_encap(&skb,&tuple);assert(tuple.encap[0].id==65530);
 puts("PASS actual functions: rejected incomplete/overflow/untag paths, nested-bridge reset, 16 PCP/DEI variants and PPPoE SID");return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='flow-path-') as d:
    c=Path(d)/'test.c';c.write_text(prefix+body+encap+tests);binary=Path(d)/'test'
    subprocess.run(['cc','-O2','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=undefined,address',str(c),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
assert 'nft_dev_path_info(&stack, &info, dst_ha, &ft->data) < 0' in t
assert 'goto err_dst_release;' in t and t.count('dst_release(route->tuple[')>=2
