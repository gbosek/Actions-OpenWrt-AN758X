#!/usr/bin/env python3
"""Exercise actual PON MTU functions; no packets sent or target code executed."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path

repo=Path(__file__).resolve().parents[1]

def function(text,name):
    match=re.search(r'(?:static\s+)?void\s+'+re.escape(name)+r'\([^;{}]*\)\s*\{',text)
    assert match,'Missing function '+name
    end=match.end();depth=1
    while depth:
        assert end<len(text),'Unclosed function '+name
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[match.start():end]

PREFIX=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define AIROHA_PRIV_F_PON 1
#define AIROHA_GDM4_IDX 3
#define VLAN_ETH_HLEN 18
#define PPPOE_SES_HLEN 8
#define ARRAY_SIZE(x) ((int)(sizeof(x)/sizeof((x)[0])))
#define max_t(t,a,b) ((t)(a)>(t)(b)?(t)(a):(t)(b))
#define REG_WAN_MTU0 0x2300
#define WAN_MTU0_MASK 0x3fffU
#define FP_EGRESS_MTU_MASK(i) (0x3fffU<<(((i)%2)*16))
#define REG_PPE_MTU(p,i) (0x4000U+(p)*0x100U+((i)/2)*4U)
#define FIELD_PREP(m,v) (((u32)(v)<<__builtin_ctz(m))&(m))
#define __field_prep(m,v) FIELD_PREP(m,v)
struct airoha_qdma {int unused;};
struct airoha_eth {struct airoha_qdma qdma[2];bool ppe1;};
struct airoha_gdm_dev;
struct net_device {u32 mtu;bool running;struct airoha_gdm_dev *priv;};
struct airoha_gdm_port {struct airoha_gdm_dev *devs[4];int id;};
struct airoha_gdm_dev {u32 flags;bool lan;int qdma_id;struct airoha_eth *eth;struct airoha_gdm_port *port;struct net_device netdev;};
struct write {u32 reg,mask,len;};
static struct write writes[4];static int nwrites,cases;
static void *netdev_priv(struct net_device *n){return n->priv;}
static struct net_device *netdev_from_priv(struct airoha_gdm_dev *d){return &d->netdev;}
static struct airoha_qdma *airoha_qdma_deref(struct airoha_gdm_dev *d){return &d->eth->qdma[d->qdma_id];}
static bool netif_running(struct net_device *n){return n->running;}
static bool airoha_is_lan_gdm_dev(struct airoha_gdm_dev *d){return d->lan;}
static bool airoha_ppe_is_enabled(struct airoha_eth *e,int id){assert(id==1);return e->ppe1;}
static void airoha_fe_rmw(struct airoha_eth *e,u32 reg,u32 mask,u32 value){
 (void)e;assert(nwrites<4);assert(!(value&~mask));
 writes[nwrites++]=(struct write){reg,mask,(value&mask)>>__builtin_ctz(mask)};
}
'''

TESTS=r'''
int main(void){
 struct airoha_eth eth={.ppe1=true};struct airoha_gdm_port port={.id=1};
 struct airoha_gdm_dev pon={.flags=AIROHA_PRIV_F_PON,.eth=&eth,.port=&port};
 struct airoha_gdm_dev lan={.lan=true,.eth=&eth,.port=&port};
 struct airoha_gdm_dev wanb={.eth=&eth,.port=&port};
 struct airoha_gdm_dev other={.lan=true,.qdma_id=1,.eth=&eth,.port=&port};
 pon.netdev.priv=&pon;lan.netdev.priv=&lan;wanb.netdev.priv=&wanb;other.netdev.priv=&other;
 for(int mtu=1280;mtu<=1500;mtu+=1){
  if(mtu!=1280&&mtu!=1492&&mtu!=1500)continue;
  for(int role=0;role<3;role++){
   struct airoha_gdm_dev *d=role==1?&pon:role==2?&wanb:&lan;
   memset(port.devs,0,sizeof(port.devs));port.devs[0]=d;
   d->netdev.mtu=mtu;d->netdev.running=true;nwrites=0;
   airoha_dev_set_mtu(&d->netdev);
   assert(nwrites==(d->lan?1:2));
   assert(writes[0].len==(u32)(mtu+18+(role==1?8:0)));
   if(!d->lan){assert(writes[1].reg==REG_WAN_MTU0);assert(writes[1].len==(u32)(mtu+18+(role==1?8:0)));}
   assert(d->netdev.mtu==(u32)mtu);cases++;
  }
 }
 /* Per-device flags matter: outer call may be LAN or PON. */
 port.devs[0]=&pon;port.devs[1]=&lan;port.devs[2]=&other;port.devs[3]=NULL;
 pon.netdev=(struct net_device){1492,true,&pon};
 lan.netdev=(struct net_device){1500,true,&lan};
 other.netdev=(struct net_device){9000,true,&other};
 for(int outer=0;outer<2;outer++){
  nwrites=0;airoha_ppe_set_mtu(outer?&pon:&lan);
  assert(nwrites==1&&writes[0].len==1518);cases++;
 }
 pon.netdev.mtu=1500;
 for(int outer=0;outer<2;outer++){
  nwrites=0;airoha_ppe_set_mtu(outer?&pon:&lan);
  assert(writes[0].len==1526);cases++;
 }
 pon.netdev.running=false;nwrites=0;airoha_ppe_set_mtu(&lan);
 assert(writes[0].len==1518);cases++;
 pon.netdev.running=true;lan.netdev.running=false;nwrites=0;airoha_ppe_set_mtu(&pon);
 assert(writes[0].len==1526);cases++;
 pon.netdev.running=false;nwrites=0;airoha_ppe_set_mtu(&pon);
 assert(writes[0].len==0);cases++;
 /* Preserve bank/index mapping including GDM4->index7, and range headroom. */
 for(int enabled=0;enabled<2;enabled++)for(int role=0;role<3;role++){
  struct airoha_gdm_dev *d=role==1?&pon:role==2?&wanb:&lan;
  port.devs[0]=d;port.devs[1]=port.devs[2]=NULL;port.id=AIROHA_GDM4_IDX;
  d->netdev.running=true;d->netdev.mtu=9220;eth.ppe1=enabled;nwrites=0;
  airoha_dev_set_mtu(&d->netdev);
  assert(writes[0].reg==REG_PPE_MTU(!d->lan&&enabled,7));
  assert(writes[0].mask==FP_EGRESS_MTU_MASK(7));
  assert(writes[0].len==(u32)(9238+(role==1?8:0)));
  assert(nwrites==(d->lan?1:2));assert(d->netdev.mtu==9220);cases++;
 }
 printf("%d\n",cases);return 0;
}
'''

def verify(kernel,compiled=False):
    meta=json.loads((repo/'Upstream/SOURCE.json').read_text())['pon_pppoe_mtu']
    source={n:(kernel/n).read_text() for n in meta['expected_prepared_sources']}
    hashes={n:hashlib.sha256((kernel/n).read_bytes()).hexdigest() for n in source}
    assert hashes==meta['expected_prepared_sources'],'Unexpected prepared MTU source'
    assert all('#include <linux/if_pppox.h>' in text for text in source.values())
    ppe=source['drivers/net/ethernet/airoha/airoha_ppe.c']
    eth=source['drivers/net/ethernet/airoha/airoha_eth.c']
    code=PREFIX+function(ppe,'airoha_ppe_set_mtu')+'\n'+function(eth,'airoha_dev_set_mtu')+TESTS
    with tempfile.TemporaryDirectory(prefix='pon-pppoe-mtu-') as directory:
        root=Path(directory);c=root/'test.c';binary=root/'test';c.write_text(code)
        subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True)
        cases=int(subprocess.check_output([str(binary)],text=True).strip())
    objects={}
    if compiled:
        for name in source:
            obj=kernel/Path(name).with_suffix('.o');raw=obj.read_bytes()
            assert raw[:5]==b'\x7fELF\x02' and raw[18:20]==b'\xb7\0','Not an AArch64 object'
            objects[str(obj.relative_to(kernel))]=hashlib.sha256(raw).hexdigest()
    return {'upstream_commit':meta['commit'],'cases':cases,'failures':0,
            'source_sha256':hashes,'compiled_arm64':compiled,'objects_sha256':objects,
            'scope':'Actual prepared MTU function bodies with mocked register/netdevice/QDMA state. No hardware, packet or throughput validation.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--kernel',type=Path);group.add_argument('--build-dir',type=Path)
    parser.add_argument('--compiled',action='store_true');parser.add_argument('--report',type=Path)
    args=parser.parse_args();kernel=args.kernel
    if kernel is None:
        kernels=[p for p in args.build_dir.glob('target-*/linux-*/linux-6.18.55') if (p/'drivers/net/ethernet/airoha/airoha_eth.c').is_file()]
        assert len(kernels)==1,'Expected one prepared 6.18.55 kernel';kernel=kernels[0]
    result=verify(kernel,args.compiled)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
