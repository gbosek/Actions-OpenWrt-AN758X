
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <arpa/inet.h>
#include <linux/if_ether.h>
#include <linux/if_vlan.h>
typedef uint16_t u16;
typedef uint8_t u8;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define READ_ONCE(x) (x)
#define BR_STATE_FORWARDING 3
#define BR_STATE_BLOCKING 4
#define BR_ISOLATED (1U << 16)
#define AIROHA_PRIV_F_PON 1
#define PPE_PKT_TYPE_BRIDGE 2
#define DEV_PATH_BRIDGE 1
#define VLAN_VID_MASK 0xfff
#define VLAN_ETH_HLEN 18
struct airoha_gdm_dev { unsigned int flags; };

#define CONFIG_NETFILTER_FAMILY_BRIDGE 1
#define CONFIG_NETFILTER_INGRESS 1
#define CONFIG_NETFILTER_EGRESS 1
#define CONFIG_NET_XGRESS 1
#define BR_PORT_LOCKED 1u
#define BR_PORT_MAB 2u
#define NF_HOOK_OP_NFT_FT 3
struct nf_hook_ops { int hook_ops_type; };
struct nf_hook_entries { unsigned int num_hook_entries; struct nf_hook_ops *ops[2]; };
struct net { struct {struct nf_hook_entries *hooks_bridge[5];} nf; };
static struct net init_net, other_net;
static struct nf_hook_ops filter_ops={1}, flowtable_ops={NF_HOOK_OP_NFT_FT};
static struct nf_hook_entries filter_head={1,{&filter_ops}}, flowtable_head={1,{&flowtable_ops}};
struct net_device { bool port,running,carrier,isolated;int state,ifindex;unsigned long flags;struct net *net;struct nf_hook_entries *nf_hooks_ingress,*nf_hooks_egress;void *tcx_ingress,*tcx_egress;struct airoha_gdm_dev gdm; };
struct airoha_bridge_owner {int bridge_ifindex,egress_ifindex;u16 vid;u8 dmac[6];};
static struct nf_hook_ops **nf_hook_entries_get_hook_ops(const struct nf_hook_entries *h) {return (struct nf_hook_ops **)h->ops;}
static struct net *dev_net(struct net_device *d) {return d->net;}
static bool net_eq(struct net *a,struct net *b) {return a==b;}
#define rcu_dereference(x) (x)
#define rcu_access_pointer(x) (x)
struct net_bridge_vlan {bool usable;int state;};
struct net_bridge_port {struct net_bridge_vlan *v;};
static struct net_bridge_vlan in_vlan,out_vlan;
static struct net_bridge_port in_port={&in_vlan},out_port={&out_vlan};
static bool vlan_filtering=true;
static bool hw_vlan_tag=true;
static u16 path_vid, path_proto;

struct sk_buff { struct net_device *dev; struct ethhdr *mac; u8 *tail; uint16_t vlan_proto; };
struct bridge_vlan_info { unsigned int flags; };
struct net_device_path_ctx { struct net_device *dev; struct {u16 id,proto;} vlan[2]; int num_vlans; };
struct net_device_path_stack { int num_paths; struct {int type; struct net_device *dev;} path[3]; };
struct airoha_flow_data { struct ethhdr eth; struct { int num; struct {u16 id,proto;} hdr[2]; } vlan; };
struct airoha_foe_entry { int prepared; };
struct airoha_ppe { void *eth; };
struct vlan_ethhdr {u8 dst[6], src[6]; u16 h_vlan_proto, h_vlan_TCI, h_vlan_encapsulated_proto;};
static struct net_device master, ingress, egress;
static bool member;
static int prepare_calls;
static const char *case_name;
static struct net_bridge_port *br_port_get_check_rcu(const struct net_device *d) {return d==&ingress?&in_port:d==&egress?&out_port:NULL;}
static struct net_bridge_port *nbp_vlan_group_rcu(struct net_bridge_port *p) {return p;}
static struct net_bridge_vlan *br_vlan_find(struct net_bridge_port *p,u16 vid) {return member&&vid==100?p->v:NULL;}
static bool br_vlan_should_use(struct net_bridge_vlan *v) {return v->usable;}
static int br_vlan_get_state(struct net_bridge_vlan *v) {return v->state;}

static struct ethhdr *eth_hdr(struct sk_buff *s) {return s->mac;}
static u8 *skb_tail_pointer(struct sk_buff *s) {return s->tail;}
static bool airoha_ppe_foe_bridge_control(struct sk_buff *s) {(void)s;return false;}
static void ether_addr_copy(u8 *a,const u8 *b) {memcpy(a,b,6);}
static void rcu_read_lock(void) {}
static void rcu_read_unlock(void) {}
static struct net_device *airoha_ppe_foe_get_bridge_master_rcu(struct net_device *d) {(void)d;return &master;}
static bool is_vlan_dev(struct net_device *d) {(void)d;return false;}
static struct net_device *vlan_dev_real_dev(struct net_device *d) {return d;}
static bool netif_is_bridge_port(struct net_device *d) {return d->port;}
static int br_port_get_stp_state(struct net_device *d) {return d->state;}
static u16 vlan_dev_vlan_id(struct net_device *d) {(void)d;return 100;}
static u16 vlan_dev_vlan_proto(struct net_device *d) {(void)d;return htons(ETH_P_8021Q);}
static bool skb_vlan_tag_present(struct sk_buff *s) {(void)s;return hw_vlan_tag;}
static u16 skb_vlan_tag_get_id(struct sk_buff *s) {(void)s;return 100;}
static bool eth_type_vlan(u16 p) {return p==htons(ETH_P_8021Q)||p==htons(ETH_P_8021AD);}
static bool br_vlan_enabled(struct net_device *d) {(void)d;return vlan_filtering;}
static int br_vlan_get_pvid_rcu(struct net_device *d,u16 *v) {(void)d;*v=100;return 0;}
static int br_vlan_get_proto(struct net_device *d,u16 *v) {(void)d;*v=ETH_P_8021Q;return 0;}
static int br_vlan_get_info_rcu(struct net_device *d,u16 v,struct bridge_vlan_info *i) {(void)d;(void)v;i->flags=0;return member?0:-1;}
static int __dev_fill_forward_path(struct net_device_path_ctx *c,const u8 *dst,struct net_device_path_stack *s) {
    path_vid=c->num_vlans?c->vlan[0].id:0;path_proto=c->num_vlans?c->vlan[0].proto:0;
    (void)dst;s->num_paths=2;s->path[0].type=DEV_PATH_BRIDGE;s->path[0].dev=&master;s->path[1].dev=&egress;
    c->dev=&egress;c->num_vlans=0;return 0;
}
static bool netif_running(struct net_device *d) {return d->running;}
static bool netif_carrier_ok(struct net_device *d) {return d->carrier;}
static bool br_port_flag_is_set(struct net_device *d,unsigned int f) {return f==BR_ISOLATED?d->isolated:!!(d->flags&f);}
static int airoha_get_dsa_port(struct net_device **d) {(void)d;return -1;}
static void *netdev_priv(struct net_device *d) {return &d->gdm;}
static bool airoha_is_valid_gdm_dev(void *eth,struct airoha_gdm_dev *g) {(void)eth;return g==&egress.gdm;}
static int airoha_ppe_foe_entry_prepare(void *eth,struct airoha_foe_entry *h,struct net_device *d,int type,struct airoha_flow_data *f,int proto,int ds,struct airoha_gdm_dev **g) {
    (void)eth;(void)d;(void)type;(void)f;(void)proto;(void)ds;*g=&egress.gdm;h->prepared=1;prepare_calls++;return 0;
}
