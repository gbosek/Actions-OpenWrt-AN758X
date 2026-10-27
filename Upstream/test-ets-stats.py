#!/usr/bin/env python3
"""Exercise actual ETS stats arithmetic across channels, wrap and wide sums."""
import argparse, hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
from check_ppe_functions import function, find_kernel

PREFIX=r'''
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
typedef uint64_t u64;
#define AIROHA_NUM_QOS_CHANNELS 4
#define REG_CNTR_VAL(x) (x)
struct airoha_qdma {u32 counters[8];};
struct airoha_gdm_dev {
 struct airoha_qdma *qdma;
 struct {u32 cpu_tx_packets, fwd_tx_packets;} qos_stats[4];
 /* Old fields only permit the local negative regression against old source. */
 u64 cpu_tx_packets, fwd_tx_packets;
};
struct net_device {struct airoha_gdm_dev *priv;};
struct tc_ets_qopt_offload {struct {u64 *bstats;} stats;};
static struct airoha_gdm_dev *netdev_priv(struct net_device *d) {return d->priv;}
static struct airoha_qdma *airoha_qdma_deref(struct airoha_gdm_dev *d) {return d->qdma;}
static u32 airoha_qdma_rr(struct airoha_qdma *q,int r) {return q->counters[r];}
static void _bstats_update(u64 *out,int bytes,u64 packets) {(void)bytes;*out+=packets;}
'''
CASES=r'''
static int cases;
static int check(struct net_device *n,int channel,u64 expected) {
 u64 delta=0;struct tc_ets_qopt_offload opt={.stats={&delta}};
 int result=airoha_qdma_get_tx_ets_stats(n,channel,&opt);cases++;
 if(result || delta!=expected) {
  printf("FAIL case=%d channel=%d expected=%llu actual=%llu\n",cases,channel,
         (unsigned long long)expected,(unsigned long long)delta);return 1;
 }
 return 0;
}
int main(void) {
 struct airoha_qdma q={.counters={100,200,7,9,31,47,0,1}};
 struct airoha_gdm_dev d={.qdma=&q};struct net_device n={&d};
 u64 expected[]={300,16,78,1};
 for(int i=0;i<4;i++)if(check(&n,i,expected[i]))return 1;
 for(int i=0;i<4;i++)if(check(&n,i,0))return 1;
 q.counters[0]+=10;q.counters[1]+=20;
 if(check(&n,0,30) || check(&n,1,0))return 1;
 d.qos_stats[2].cpu_tx_packets=0xfffffff0u;
 d.qos_stats[2].fwd_tx_packets=0xfffffff8u;
 q.counters[4]=16;q.counters[5]=8;
 if(check(&n,2,48))return 1;
 d.qos_stats[3].cpu_tx_packets=0xffffffffu;
 d.qos_stats[3].fwd_tx_packets=0xffffffffu;
 q.counters[6]=0xfffffffeu;q.counters[7]=0xfffffffeu;
 if(check(&n,3,8589934590ull))return 1;
 printf("{\"cases\":%d,\"failures\":0}\n",cases);return 0;
}
'''

def verify(kernel):
 meta=json.loads((REPO/'Upstream/SOURCE.json').read_text())['ets_stats_review']
 hashes={n:hashlib.sha256((kernel/n).read_bytes()).hexdigest() for n in meta['new_source_sha256']}
 assert hashes==meta['new_source_sha256'],'Unexpected ETS source; review exact prepared files'
 source=(kernel/'drivers/net/ethernet/airoha/airoha_eth.c').read_text()
 header=(kernel/'drivers/net/ethernet/airoha/airoha_eth.h').read_text()
 body=function(source,'airoha_qdma_get_tx_ets_stats')
 assert 'airoha_qdma_deref(dev)' in body,'Retained QDMA lifetime accessor missing'
 assert 'dev->cpu_tx_packets' not in body and 'dev->fwd_tx_packets' not in body
 assert re.search(r'u32 cpu_tx_packets;\s*u32 fwd_tx_packets;\s*} qos_stats\[AIROHA_NUM_QOS_CHANNELS\]',header)
 with tempfile.TemporaryDirectory(prefix='airoha-ets-stats-') as td:
  root=Path(td);c=root/'test.c';exe=root/'test';c.write_text(PREFIX+body+CASES)
  subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
  result=json.loads(subprocess.check_output([str(exe)],text=True))
 assert result=={'cases':12,'failures':0},result
 return dict(result,source_sha256=hashes,hardware_tested=False,
             scope='Actual function with register/bstats models; independent channels and modulo-u32 deltas added in u64; no PPE/UI/binding or physical validation')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--kernel',type=Path);g.add_argument('--build-dir',type=Path);p.add_argument('--report',type=Path)
 a=p.parse_args();result=verify(a.kernel or find_kernel(a.build_dir))
 if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
