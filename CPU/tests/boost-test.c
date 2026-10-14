#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
typedef uint32_t u32;
#define __iomem
#define BIT(n) (1u << (n))
#define GENMASK(h,l) ((0xffffffffu >> (31-(h))) & (0xffffffffu << (l)))
#define FIELD_GET(mask,v) (((v) & (mask)) >> __builtin_ctz(mask))
#define FIELD_PREP(mask,v) (((v) << __builtin_ctz(mask)) & (mask))
#define READ_ONCE(v) (v)
#define WRITE_ONCE(v,x) ((v)=(x))
struct mutex { int held; };
struct device { int unused; };
static void mutex_lock(struct mutex *m) { assert(!m->held); m->held=1; }
static void mutex_unlock(struct mutex *m) { assert(m->held); m->held=0; }
static unsigned char pll[0x388], mcu[0x1000];
static int writes, stops, sleeps, errors, inside_stop;
static int fail_stop, fail_1400, corrupt_1400, ignore_1200, ignore_latch, fail_smc_state, lying_smc;
static int trace[100], trace_n;
static u32 readl(const void *addr) { u32 value; memcpy(&value,addr,4); return value; }
static void writel(u32 value, void *addr) {
 writes++;
 if(addr==pll+0x2b8 && ignore_latch) return;
 if(addr==pll+0x2b4) {
  unsigned int pcw=(value>>24)&0x7f;
  if(pcw==28 && fail_1400) { fail_1400--; return; }
  if(pcw==28 && corrupt_1400) { value=(value&~GENMASK(30,24))|(31u<<24); }
  if(pcw==24 && ignore_1200) return;
 }
 memcpy(addr,&value,4);
}
static void udelay(int usec) { assert(inside_stop); assert(usec==20); }
static void msleep(int ms) { assert(!inside_stop); assert(ms==1000); assert(((readl(mcu+0x7c0)>>9)&3)==3); sleeps++; }
static int stop_machine(int (*fn)(void *),void *data,void *cpus) {
 (void)cpus; stops++;
 if(fail_stop) { fail_stop--; return -ENOMEM; }
 assert(!inside_stop); inside_stop=1; int result=fn(data);inside_stop=0;return result;
}
#define dev_dbg(dev,...) ((void)(dev))
#define dev_err(dev,...) do { (void)(dev); errors++; } while(0)
#define XG2010G_BOOST_TEST
#include "xg2010g-cpu-boost.h"
static struct xg2010g_boost b;
static void raw_freq(int mhz) {
 unsigned int div=mhz<1000 ? 1 : 0;
 u32 pcw=(mhz/(div?25:50))<<24, chg=div<<4;
 memcpy(pll+XG_PLL_PCW,&pcw,4);memcpy(pll+XG_PLL_CHG,&chg,4);
}
static int smc_set(unsigned int state) {
 assert(trace_n<100);trace[trace_n++]=state;
 if(b.enabled) { assert(state<=14); assert(xg2010g_pll_mhz(&b)!=1400); }
 if((int)state==fail_smc_state) return -EOPNOTSUPP;
 if(!lying_smc) raw_freq(500+50*state);
 return 0;
}
static void reset(int mhz) {
 memset(pll,0,sizeof pll);memset(mcu,0,sizeof mcu);memset(&b,0,sizeof b);
 b.pll=pll;b.mcu=mcu;b.enabled=true;b.mapped=true;b.capable=true;
 u32 v=0x101;memcpy(pll+XG_CLK_MUX,&v,4);
 v=0x123400;memcpy(pll+XG_PLL_PROTECT,&v,4);
 v=0xdead0000;memcpy(mcu+XG_MCU_UNLOCK,&v,4);
 v=(1u<<9)|0x810000;memcpy(mcu+XG_MCU_SOURCE,&v,4);raw_freq(mhz);
 writes=stops=sleeps=errors=inside_stop=0;trace_n=0;
 fail_stop=fail_1400=corrupt_1400=ignore_1200=ignore_latch=lying_smc=0;fail_smc_state=-1;
}
int main(void) {
 reset(1000); assert(!xg2010g_boost_set_state(&b,0,smc_set));assert(trace_n==1&&trace[0]==0&&stops==0);assert(xg2010g_pll_mhz(&b)==500);
 reset(1000);assert(!xg2010g_boost_set_state(&b,15,smc_set));assert(trace_n==1&&trace[0]==14&&xg2010g_pll_mhz(&b)==1400);assert(stops==2&&sleeps==1&&b.capable);
 int w=writes;assert(!xg2010g_boost_set_state(&b,15,smc_set));assert(writes==w&&trace_n==1&&stops==2&&sleeps==1);
 assert(!xg2010g_boost_set_state(&b,6,smc_set));assert(trace_n==2&&trace[1]==6&&xg2010g_pll_mhz(&b)==800&&stops==4);
 reset(1000);b.capable=false;assert(xg2010g_boost_set_state(&b,15,smc_set)==-EOPNOTSUPP);assert(!trace_n&&!writes);
 reset(1000);assert(xg2010g_boost_set_state(&b,16,smc_set)==-EINVAL);assert(!trace_n&&!writes);
 reset(1000);fail_smc_state=14;assert(xg2010g_boost_set_state(&b,15,smc_set)==-EOPNOTSUPP);assert(!stops&&!writes&&!b.capable&&xg2010g_pll_mhz(&b)==1000);
 reset(1000);lying_smc=1;assert(xg2010g_boost_set_state(&b,15,smc_set)==-EIO);assert(!stops&&!b.capable&&trace_n==2&&trace[1]==10);
 reset(1000);fail_1400=1;assert(xg2010g_boost_set_state(&b,15,smc_set)==-EIO);assert(!b.capable&&stops==3&&trace_n==2&&trace[1]==10&&xg2010g_pll_mhz(&b)==1000);
 reset(1000);corrupt_1400=1;ignore_1200=1;assert(xg2010g_boost_set_state(&b,15,smc_set)==-EIO);assert(!b.capable&&errors>=2&&trace_n==1);assert(xg2010g_pll_mhz(&b)==1550);assert(xg2010g_boost_set_state(&b,10,smc_set)==-EIO&&trace_n==1);
 reset(1000);fail_stop=1;assert(xg2010g_boost_set_state(&b,15,smc_set)==-ENOMEM);assert(!writes&&!b.capable&&trace_n==2&&xg2010g_pll_mhz(&b)==1000);
 reset(1400);ignore_1200=1;assert(xg2010g_boost_set_state(&b,10,smc_set)==-EIO);assert(!b.capable&&trace_n==0&&xg2010g_pll_mhz(&b)==1400);ignore_1200=0;assert(!xg2010g_boost_set_state(&b,10,smc_set));assert(trace_n==1&&xg2010g_pll_mhz(&b)==1000);
 reset(1000);ignore_latch=1;assert(xg2010g_boost_set_state(&b,15,smc_set)==-EIO);assert(!b.capable&&b.parked&&b.unsafe&&trace_n==1&&xg2010g_pll_mhz(&b)==1200);
 reset(1200);u32 mux=readl(pll+XG_CLK_MUX),protect=readl(pll+XG_PLL_PROTECT),unlock=readl(mcu+XG_MCU_UNLOCK),source=readl(mcu+XG_MCU_SOURCE);assert(!xg2010g_pll_switch(&b,1400));assert(readl(pll+XG_CLK_MUX)==mux&&readl(pll+XG_PLL_PROTECT)==protect&&readl(mcu+XG_MCU_UNLOCK)==unlock&&readl(mcu+XG_MCU_SOURCE)==source);
 reset(1200);assert(xg2010g_pll_switch(&b,1600)==-EINVAL&&!writes);
 reset(1400);fail_smc_state=6;assert(xg2010g_boost_set_state(&b,6,smc_set)==-EOPNOTSUPP);assert(xg2010g_pll_mhz(&b)==1200&&b.capable);
 reset(1000);u32 pcw=readl(pll+XG_PLL_PCW)|1;memcpy(pll+XG_PLL_PCW,&pcw,4);assert(!xg2010g_pll_valid(&b)&&!xg2010g_pll_mhz(&b));
 reset(1000);b.enabled=false;assert(!xg2010g_boost_set_state(&b,22,smc_set)&&trace[0]==22&&stops==0);
 puts("PASS: ordinary BL31, enter/exit/repeat boost, state bounds, unavailable backend, SMC failure, lying SMC, write failure, rollback failure, stop_machine failure, exit recovery, saved control registers, invalid encoding and non-XG behavior");
 return 0;
}
