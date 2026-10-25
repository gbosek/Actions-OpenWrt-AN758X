"""Execute unchanged prepared bridge eligibility/revoke bodies with host models.

These are function regressions, not full Linux packet or hardware tests.
"""
from pathlib import Path
import json, subprocess, tempfile

HERE = Path(__file__).resolve().parent

PREPARE_TESTS = r'''
static int cases;
static void reset(void) {
    memset(&init_net,0,sizeof(init_net));memset(&other_net,0,sizeof(other_net));
    master=(struct net_device){.ifindex=1,.net=&init_net};
    ingress=(struct net_device){.ifindex=2,.net=&init_net,.port=true,.running=true,.carrier=true,.state=BR_STATE_FORWARDING};
    egress=ingress;egress.ifindex=3;member=true;vlan_filtering=true;prepare_calls=0;
    in_vlan=(struct net_bridge_vlan){true,BR_STATE_FORWARDING};out_vlan=in_vlan;
    hw_vlan_tag=true;path_vid=path_proto=0;
}
static void run(bool expected) {
    struct ethhdr frame={.h_proto=htons(ETH_P_IP),.h_dest={2,3,4,5,6,7}};
    struct sk_buff skb={.dev=&ingress,.mac=&frame,.tail=(u8*)(&frame+1),.vlan_proto=htons(ETH_P_8021Q)};
    struct airoha_foe_entry hw={0};struct airoha_ppe p={0};struct airoha_bridge_owner owner={0};
    bool actual=airoha_ppe_foe_prepare_bridge_subflow(&p,&skb,&hw,&owner);
    if(actual!=expected || prepare_calls!=(expected?1:0) || rcu_depth) {fprintf(stderr,"%s failed\n",case_name);exit(1);}
    if(actual && (owner.bridge_ifindex!=1 || owner.egress_ifindex!=3 || owner.vid!=(vlan_filtering?100:0) || memcmp(owner.dmac,frame.h_dest,6)))exit(2);
    cases++;
}
static void inline_vlan(unsigned int vid, bool expected) {
    u8 raw[32] __attribute__((aligned(2)))={0};
    struct ethhdr *frame=(struct ethhdr *)(raw+1);
    struct sk_buff skb={.dev=&ingress,.mac=frame,.tail=raw+1+VLAN_ETH_HLEN};
    struct airoha_foe_entry hw={0};struct airoha_ppe p={0};struct airoha_bridge_owner owner={0};
    u16 tci=htons(vid);
    hw_vlan_tag=false;frame->h_dest[0]=2;frame->h_proto=htons(ETH_P_8021Q);
    memcpy(raw+1+ETH_HLEN,&tci,sizeof(tci));
    bool actual=airoha_ppe_foe_prepare_bridge_subflow(&p,&skb,&hw,&owner);
    if(actual!=expected || prepare_calls!=(expected?1:0))exit(3);
    if(actual && (path_vid!=100 || path_proto!=htons(ETH_P_8021Q) || owner.vid!=100))exit(4);
    cases++;
}
int main(void) {
    reset();case_name="ordinary_bridge";run(true);
    reset();init_net.nf.hooks_bridge[2]=&filter_head;case_name="bridge_filter_denies_coarse_binding";run(false);
    reset();init_net.nf.hooks_bridge[2]=&flowtable_head;case_name="flowtable_is_not_filter_permission";run(true);
    reset();in_vlan.state=BR_STATE_BLOCKING;case_name="ingress_mst_blocked";run(false);
    reset();out_vlan.state=BR_STATE_BLOCKING;case_name="egress_mst_blocked";run(false);
    reset();out_vlan.usable=false;case_name="egress_vlan_unusable";run(false);
    reset();ingress.state=BR_STATE_BLOCKING;case_name="whole_port_stp_blocked";run(false);
    reset();egress.state=BR_STATE_BLOCKING;case_name="egress_stp_blocked";run(false);
    reset();ingress.port=false;case_name="missing_ingress_bridge_port";run(false);
    reset();egress.port=false;case_name="missing_egress_bridge_port";run(false);
    reset();member=false;case_name="vlan_not_member";run(false);
    reset();egress.gdm.flags=AIROHA_PRIV_F_PON;case_name="pon_egress";run(false);
    reset();master.net=&other_net;case_name="foreign_namespace";run(false);
    reset();ingress.nf_hooks_ingress=&filter_head;case_name="ingress_filter";run(false);
    reset();egress.nf_hooks_egress=&filter_head;case_name="egress_filter";run(false);
    reset();ingress.tcx_ingress=&ingress;case_name="tc_filter";run(false);
    reset();ingress.flags=BR_PORT_LOCKED;case_name="locked_port";run(false);
    reset();egress.flags=BR_PORT_MAB;case_name="mab_port";run(false);
    reset();vlan_filtering=false;case_name="unfiltered_bridge_fdb_vid_zero";run(true);
    reset();case_name="unaligned_inline_vlan";inline_vlan(100,true);
    reset();case_name="unaligned_inline_vlan_not_admitted";inline_vlan(200,false);
    printf("{\"cases\":%d,\"failed\":0}",cases);return 0;
}
'''

REVOKE_PREFIX = r'''
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
typedef uint32_t u32;typedef uint64_t u64;typedef uint16_t u16;typedef uint8_t u8;
#define AIROHA_FOE_IB1_BIND_STATE 0x30000000u
#define AIROHA_FOE_STATE_INVALID 0
#define FIELD_PREP(m,v) ((v)<<__builtin_ctz(m))
#define FIELD_GET(m,v) (((v)&(m))>>__builtin_ctz(m))
#define READ_ONCE(x) (x)
#define NFPROTO_BRIDGE 7
#define NFPROTO_NETDEV 5
#define NFPROTO_INET 1
#define NF_INET_INGRESS 5
#define NF_HOOK_OP_NFT_FT 3
#define NOTIFY_DONE 0
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
enum {SWITCHDEV_FDB_ADD_TO_DEVICE=1,SWITCHDEV_FDB_DEL_TO_DEVICE,SWITCHDEV_FDB_ADD_TO_BRIDGE,SWITCHDEV_FDB_DEL_TO_BRIDGE,SWITCHDEV_FDB_FLUSH_TO_BRIDGE,SWITCHDEV_PORT_ATTR_SET};
struct notifier_block {int unused;};
struct nf_hook_ops {int hooknum,hook_ops_type;};
struct switchdev_notifier_fdb_info {const u8 *addr;u16 vid;};
struct airoha_foe_entry {u32 ib1;};
struct airoha_bridge_owner {int bridge_ifindex,egress_ifindex;u16 vid;u8 dmac[6];};
struct fake_eth {void *dev;};
struct airoha_ppe {struct fake_eth *eth;void *foe;unsigned long *bridge_fallback;struct airoha_bridge_owner *bridge_owners;u64 bridge_generation;bool bridge_policy_blocked,bridge_fallback_fault;struct notifier_block bridge_nf_nb,bridge_switchdev_nb;};
static int ppe_lock,locks,acks,yields,fail_hash=-1,topology_events;
static void spin_lock_bh(int *p) {(void)p;if(locks++)abort();}
static void spin_unlock_bh(int *p) {(void)p;if(--locks)abort();}
static u32 airoha_ppe_get_total_num_entries(struct airoha_ppe *p) {(void)p;return 8;}
static u32 airoha_ppe_get_total_sram_num_entries(struct airoha_ppe *p) {(void)p;return 4;}
static int test_bit(u32 b,unsigned long *p) {return !!(*p&(1ul<<b));}
static void __clear_bit(u32 b,unsigned long *p) {*p&=~(1ul<<b);}
static bool ether_addr_equal(const u8 *a,const u8 *b) {return !memcmp(a,b,6);}
static int airoha_ppe_foe_commit_sram_entry(struct airoha_ppe *p,u32 h) {(void)p;acks++;return (int)h==fail_hash?-110:0;}
static void cond_resched(void) {if(locks)abort();yields++;}
static int notifier_from_errno(int e) {return e;}
static void airoha_ppe_bridge_topology_event(struct airoha_ppe *p,bool s) {(void)p;(void)s;topology_events++;}
#define for_each_set_bit(b,p,n) for((b)=0;(b)<(n);(b)++) if(test_bit((b),(p)))
#define wmb() do {} while(0)
#define dev_warn_ratelimited(...) do {} while(0)
static int cases;
#define check(x) do {cases++;if(!(x)){fprintf(stderr,"case %d line %d failed\n",cases,__LINE__);exit(1);}}while(0)
'''

REVOKE_TESTS = r'''
int main(void) {
    u8 a[6]={2,1,2,3,4,5},b[6]={2,6,7,8,9,0};
    struct airoha_foe_entry table[8];struct airoha_bridge_owner owners[8]={0};
    for(int i=0;i<8;i++){table[i].ib1=0x20000000;owners[i].vid=100;memcpy(owners[i].dmac,i==2?b:a,6);}
    unsigned long bits=(1ul<<1)|(1ul<<2)|(1ul<<6);struct fake_eth eth={0};
    struct airoha_ppe p={.eth=&eth,.foe=table,.bridge_fallback=&bits,.bridge_owners=owners};
    struct switchdev_notifier_fdb_info fdb={a,100};
    airoha_ppe_bridge_switchdev_event(&p.bridge_switchdev_nb,SWITCHDEV_FDB_ADD_TO_DEVICE,&fdb);
    check(bits==(1ul<<2));check(table[1].ib1==0&&table[6].ib1==0&&table[2].ib1==0x20000000);
    check(acks==1&&yields==0&&p.bridge_generation==1&&!p.bridge_policy_blocked);
    fdb.vid=200;airoha_ppe_bridge_switchdev_event(&p.bridge_switchdev_nb,SWITCHDEV_FDB_DEL_TO_DEVICE,&fdb);
    check(bits==(1ul<<2));
    fdb.vid=100;fdb.addr=b;airoha_ppe_bridge_switchdev_event(&p.bridge_switchdev_nb,SWITCHDEV_FDB_DEL_TO_DEVICE,&fdb);
    check(bits==0&&acks==2);
    bits=6;struct nf_hook_ops ops={0,NF_HOOK_OP_NFT_FT};
    check(airoha_ppe_bridge_nf_event(&p.bridge_nf_nb,NFPROTO_NETDEV,&ops)==0&&bits==6);
    ops.hook_ops_type=1;
    check(airoha_ppe_bridge_nf_event(&p.bridge_nf_nb,NFPROTO_BRIDGE,&ops)==0);
    check(bits==0&&p.bridge_policy_blocked&&yields==2);
    bits=6;fail_hash=1;acks=0;
    check(airoha_ppe_bridge_nf_event(&p.bridge_nf_nb,NFPROTO_BRIDGE,&ops)==-110);
    check(bits==6&&acks==1&&p.bridge_fallback_fault);
    check(locks==0);
    airoha_ppe_bridge_switchdev_event(&p.bridge_switchdev_nb,SWITCHDEV_PORT_ATTR_SET,&fdb);
    check(topology_events==1);
    airoha_ppe_bridge_switchdev_event(&p.bridge_switchdev_nb,SWITCHDEV_FDB_ADD_TO_BRIDGE,&fdb);
    check(topology_events==2);
    airoha_ppe_bridge_switchdev_event(&p.bridge_switchdev_nb,SWITCHDEV_FDB_FLUSH_TO_BRIDGE,&fdb);
    check(topology_events==3);
    printf("{\"cases\":%d,\"failed\":0}",cases);return 0;
}
'''

RX_PREFIX = r'''
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
typedef uint32_t u32;typedef uint64_t u64;typedef uint16_t u16;typedef uint8_t u8;
#define AIROHA_FOE_IB1_BIND_STATE 0x30000000u
#define AIROHA_FOE_STATE_BIND 2
#define AIROHA_FOE_IB1_BIND_PACKET_TYPE 0x000f0000u
#define PPE_PKT_TYPE_BRIDGE 2
#define FLOW_TYPE_L2 1
#define FLOW_TYPE_L2_SUBFLOW 2
#define FIELD_GET(m,v) (((v)&(m))>>__builtin_ctz(m))
#define READ_ONCE(x) (x)
struct ethhdr {u8 dst[6],src[6];};struct sk_buff {struct ethhdr *eth;};
struct airoha_foe_entry {u32 ib1;};struct airoha_foe_bridge {int unused;};
struct airoha_bridge_owner {int bridge_ifindex,egress_ifindex;u16 vid;u8 dmac[6];};
struct hlist_node {int unused;};struct airoha_flow_table_entry {int type;u32 hash;struct airoha_foe_entry data;};
struct airoha_ppe {void *eth;u32 bridge_ft_refs;u64 bridge_generation;bool bridge_boot_ready,bridge_policy_blocked,bridge_topology_blocked,bridge_fallback_fault;unsigned long *bridge_fallback;struct airoha_bridge_owner *bridge_owners;int foe_flow[1],l2_flows;};
static int ppe_lock,locks,prepares,commits,parent_commits,fail_commit,event,local_packet,control_packet,has_parent,cases;
static bool qualifies=true;static struct airoha_foe_entry table;static struct airoha_flow_table_entry parent;
static bool airoha_ppe_foe_skb_is_local(struct sk_buff *s) {(void)s;return local_packet;}
static bool airoha_ppe_foe_bridge_control(struct sk_buff *s) {(void)s;return control_packet;}
static bool airoha_ppe_foe_prepare_bridge_subflow(struct airoha_ppe *p,struct sk_buff *s,struct airoha_foe_entry *h,struct airoha_bridge_owner *o) {(void)p;(void)s;(void)h;prepares++;o->egress_ifindex=3;return qualifies;}
static void spin_lock_bh(int *p) {(void)p;if(locks++)abort();}
static void spin_unlock_bh(int *p) {(void)p;if(--locks)abort();}
static struct airoha_foe_entry *airoha_ppe_foe_get_entry_locked(struct airoha_ppe *p,u32 hash) {
 (void)hash;if(event==1)p->bridge_generation++;if(event==2)p->bridge_policy_blocked=true;if(event==3)p->bridge_topology_blocked=true;if(event==4)p->bridge_boot_ready=false;return &table;
}
static bool airoha_is_7581(void *eth) {(void)eth;return true;}
static u32 airoha_ppe_foe_get_entry_hash(struct airoha_ppe *p,struct airoha_foe_entry *h) {(void)p;(void)h;return 0;}
#define hlist_for_each_entry_safe(e,n,h,member) for((void)(h),(e)=NULL,(n)=NULL;(e)!=NULL&&(n)==NULL;)
static void airoha_ppe_foe_remove_flow(struct airoha_ppe *p,struct airoha_flow_table_entry *e) {(void)p;(void)e;abort();}
static bool airoha_ppe_foe_compare_entry(struct airoha_flow_table_entry *e,struct airoha_foe_entry *h) {(void)e;(void)h;return false;}
static int airoha_ppe_foe_commit_entry(struct airoha_ppe *p,struct airoha_foe_entry *h,u32 hash,bool w) {(void)p;(void)h;(void)hash;(void)w;commits++;return 0;}
static struct ethhdr *eth_hdr(struct sk_buff *s) {return s->eth;}
static void airoha_ppe_foe_set_bridge_addrs(struct airoha_foe_bridge *b,struct ethhdr *e) {(void)b;(void)e;}
static int airoha_l2_flow_table_params;
static struct airoha_flow_table_entry *rhashtable_lookup_fast(int *t,struct airoha_foe_bridge *b,int params) {(void)t;(void)b;(void)params;return has_parent?&parent:NULL;}
static int airoha_ppe_foe_commit_subflow_entry(struct airoha_ppe *p,struct airoha_flow_table_entry *e,u32 hash,bool w) {(void)p;(void)e;(void)hash;(void)w;parent_commits++;return 0;}
static int airoha_ppe_foe_commit_subflow(struct airoha_ppe *p,struct airoha_foe_entry *h,u32 hash,bool w) {(void)p;(void)h;(void)hash;(void)w;commits++;return fail_commit;}
static void __set_bit(u32 b,unsigned long *p) {*p|=1ul<<b;}
#define dev_warn_ratelimited(...) do {} while(0)
#define check(x) do {cases++;if(!(x)){fprintf(stderr,"RX case %d line %d failed\n",cases,__LINE__);exit(1);}}while(0)
'''

RX_TESTS = r'''
static unsigned long bits;static struct airoha_bridge_owner owners[8];static struct airoha_ppe p;
static struct ethhdr eh;static struct sk_buff skb={&eh};
static void reset(void) {
 p=(struct airoha_ppe){.bridge_boot_ready=true,.bridge_ft_refs=1,.bridge_fallback=&bits,.bridge_owners=owners};
 bits=0;table.ib1=(PPE_PKT_TYPE_BRIDGE<<16);prepares=commits=parent_commits=fail_commit=event=local_packet=control_packet=has_parent=0;qualifies=true;
}
int main(void) {
 reset();airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(commits==1&&bits==2&&owners[1].egress_ifindex==3);
 reset();event=1;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==1&&commits==0&&bits==0);
 reset();event=2;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==1&&commits==0);
 reset();event=3;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==1&&commits==0);
 reset();event=4;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==1&&commits==0);
 reset();p.bridge_boot_ready=false;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==0&&commits==0);
 reset();p.bridge_boot_ready=false;has_parent=1;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(parent_commits==1&&commits==0);
 reset();p.bridge_ft_refs=0;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==0&&commits==0);
 reset();p.bridge_policy_blocked=true;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==0&&commits==0);
 reset();p.bridge_topology_blocked=true;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==0&&commits==0);
 reset();p.bridge_fallback_fault=true;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==0&&commits==0);
 reset();qualifies=false;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==1&&commits==0);
 reset();local_packet=1;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==0&&commits==0);
 reset();control_packet=1;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(prepares==0&&commits==0);
 reset();has_parent=1;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(commits==0&&parent_commits==1&&bits==0);
 reset();fail_commit=-110;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(commits==1&&bits==2&&p.bridge_fallback_fault);
 reset();table.ib1|=0x20000000u;airoha_ppe_foe_insert_entry(&p,&skb,1,false);check(commits==0&&bits==0);
 check(locks==0);printf("{\"cases\":%d,\"failed\":0}",cases);return 0;
}
'''

STP_PREFIX = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
typedef uint8_t u8;
#define BR_STATE_DISABLED 0
#define BR_STATE_BLOCKING 4
#define BR_STATE_FORWARDING 3
#define READ_ONCE(x) (x)
static int rcu_depth,cases;
#define RCU_LOCKDEP_WARN(condition,message) do {if(condition)abort();} while(0)
static bool rcu_read_lock_held(void) {return rcu_depth>0;}
struct net_bridge_port {u8 state;};
struct net_device {bool port;struct net_bridge_port *p;};
static struct net_bridge_port *br_port_get_check_rcu(const struct net_device *d) {return d->port?d->p:NULL;}
#define check(x) do {cases++;if(!(x))abort();} while(0)
'''
STP_TESTS = r'''
int main(int argc,char **argv) {
 (void)argv;struct net_bridge_port port={BR_STATE_FORWARDING};struct net_device dev={true,&port};
 if(argc>1) {br_port_get_stp_state_rcu(&dev);return 0;}
 rcu_depth=1;check(br_port_get_stp_state_rcu(&dev)==BR_STATE_FORWARDING);
 port.state=BR_STATE_BLOCKING;check(br_port_get_stp_state_rcu(&dev)==BR_STATE_BLOCKING);
 port.state=BR_STATE_DISABLED;check(br_port_get_stp_state_rcu(&dev)==BR_STATE_DISABLED);
 dev.port=false;check(br_port_get_stp_state_rcu(&dev)==BR_STATE_DISABLED);
 dev.port=true;dev.p=NULL;check(br_port_get_stp_state_rcu(&dev)==BR_STATE_DISABLED);
 rcu_depth--;check(rcu_depth==0);printf("{\"cases\":%d,\"failed\":0}",cases);return 0;
}
'''

def run(code, reject_outside_rcu=False):
    with tempfile.TemporaryDirectory(prefix='bridge-safety-') as d:
        c, binary = Path(d)/'test.c', Path(d)/'test'
        c.write_text(code)
        subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',
                        '-Wno-sign-compare',str(c),'-o',str(binary)],check=True)
        result=json.loads(subprocess.check_output([str(binary)],text=True))
        if reject_outside_rcu:
            rejected=subprocess.run([str(binary),'outside-rcu'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            assert rejected.returncode!=0,'RCU accessor accepted missing read-side lock in the contract fixture'
            result['cases']+=1
        return result

def check(kernel, extract):
    ppe=(kernel/'drivers/net/ethernet/airoha/airoha_ppe.c').read_text()
    vlan=(kernel/'net/bridge/br_vlan.c').read_text()
    stp=extract((kernel/'net/bridge/br_stp.c').read_text(),'br_port_get_stp_state_rcu')
    prepare='\n'.join(extract(ppe,n) for n in ['airoha_ppe_bridge_has_filter',
                       'airoha_ppe_bridge_policy_allows','airoha_ppe_foe_prepare_bridge_subflow'])
    prep=run((HERE/'bridge-fixture.h').read_text()+stp+extract(vlan,'br_vlan_is_forwarding_rcu')+prepare+PREPARE_TESTS)
    stp_read=run(STP_PREFIX+stp+STP_TESTS,reject_outside_rcu=True)
    revoke='\n'.join(extract(ppe,n) for n in ['airoha_ppe_bridge_invalidate_slot',
                     'airoha_ppe_bridge_revoke','airoha_ppe_bridge_nf_event',
                     'airoha_ppe_bridge_switchdev_event'])
    revoked=run(REVOKE_PREFIX+revoke+REVOKE_TESTS)
    insert=extract(ppe,'airoha_ppe_foe_insert_entry')
    rx=run(RX_PREFIX+insert+RX_TESTS)
    gate=run(r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint64_t u64;
struct airoha_ppe {bool bridge_boot_ready,bridge_policy_blocked,bridge_topology_blocked,bridge_fallback_fault;};
static int ppe_lock,locks,revokes,fail_revoke,cases;
#define WRITE_ONCE(x,v) ((x)=(v))
static void spin_lock_bh(int *p){(void)p;if(locks++)abort();}
static void spin_unlock_bh(int *p){(void)p;if(--locks)abort();}
static int airoha_ppe_bridge_revoke(struct airoha_ppe *p,const void *a,int vid,bool block,bool sleepable){
 if(p->bridge_boot_ready||a||vid||block||!sleepable||locks)abort();
 revokes++;return fail_revoke;}
#define check(x) do{cases++;if(!(x))abort();}while(0)
''' + extract(ppe,'airoha_ppe_bridge_boot_gate') + r'''
int main(void){
 struct airoha_ppe p={.bridge_policy_blocked=true,.bridge_topology_blocked=true,.bridge_fallback_fault=true};
 check(!p.bridge_boot_ready);
 check(airoha_ppe_bridge_boot_gate(&p,2)==-EINVAL&&!p.bridge_boot_ready&&revokes==0);
 check(airoha_ppe_bridge_boot_gate(&p,1)==0&&p.bridge_boot_ready&&revokes==0);
 check(p.bridge_policy_blocked&&p.bridge_topology_blocked&&p.bridge_fallback_fault);
 check(airoha_ppe_bridge_boot_gate(&p,0)==0&&!p.bridge_boot_ready&&revokes==1);
 p.bridge_boot_ready=true;fail_revoke=-110;
 check(airoha_ppe_bridge_boot_gate(&p,0)==-110&&!p.bridge_boot_ready&&revokes==2);
 check(locks==0);printf("{\"cases\":%d,\"failed\":0}",cases);return 0;}
''')
    assert 'bridge_generation == ppe->bridge_generation' in insert
    assert '!ppe->bridge_topology_blocked' in insert and '!ppe->bridge_policy_blocked' in insert
    nf=(kernel/'net/netfilter/core.c').read_text()
    hook=nf[nf.index('static int __nf_register_net_hook('):nf.index('static void __nf_unregister_net_hook(')]
    assert hook.index('blocking_notifier_call_chain')<hook.index('rcu_assign_pointer(*pp, new_hooks)')
    worker=extract(ppe,'airoha_ppe_bridge_topology_work')
    assert worker.index('br_offload_state_sync(dev)')<worker.index('ppe->bridge_topology_blocked = false')
    assert 'generation != ppe->bridge_generation' in worker and 'rtnl_trylock()' in worker
    return {'prepare_cases':prep,'revoke_cases':revoked,'rx_gate_cases':rx,'boot_gate_cases':gate,'stp_rcu_cases':stp_read,
            'scope':'Actual prepared eligibility/VLAN/revoke/notifier functions with host kernel models; generation/publication ordering also inspected. Not hardware or complete Linux packet-path validation.'}
