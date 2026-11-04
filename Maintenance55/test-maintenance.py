#!/usr/bin/env python3
"""Exercise actual init fragments and the provider's registration error path."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile,threading

R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path);p.add_argument('--report',type=Path)
a=p.parse_args();S=a.source.resolve()
m=json.loads((R/'Maintenance55/SOURCE.json').read_text())
checks=[]
init=S/'package/network/services/dnsmasq/files/dnsmasq.init'
t=init.read_text()
subprocess.run(['sh','-n',str(init)],check=True)
helper=t[t.index('dnsmasq_resolvconf_link()'):t.index('\ndnsmasq_start()')]
begin=t.index('\t[ "$localuse" -gt 0 ] && {',t.index('dnsmasq_start()'))
end=t.index('\n\tconfig_list_foreach "$cfg" addnmount',begin)
start_block=t[begin:end]
stop_block=t[t.index('dnsmasq_stop()'):t.index('\nnftables_clear()')]
with tempfile.TemporaryDirectory(prefix='dnsmasq-atomic-resolv-') as d:
    d=Path(d);confdir=d/'resolv.conf.d';confdir.mkdir()
    conf=d/'resolv.conf';target=confdir/'resolv.conf';auto=confdir/'resolv.conf.auto'
    upstream='nameserver 192.0.2.53\n';auto.write_text(upstream)
    # Only filesystem roots are sandboxed. Execute the actual shipped functions.
    body=(helper+'\nstart_for_test() {\nlocal DNS_SERVERS="$DNS_SERVERS"\n'+start_block+'\n:\n}\n'+stop_block)
    body=body.replace('/tmp/resolv.conf.d',str(confdir)).replace('/tmp/resolv.conf',str(conf))
    script=d/'exercise.sh'
    script.write_text('''#!/bin/sh
set -eu
config_get_bool() {
    case "$3" in
        noresolv) eval "$1=0" ;;
        localuse) eval "$1=$TEST_LOCALUSE" ;;
        *) exit 99 ;;
    esac
}
config_get() { eval "$1=\\\"$resolvfile\\\""; }
'''+body+'''
case "$1" in
    start) start_for_test ;;
    stop) dnsmasq_stop "$cfg" ;;
    cycle) i=0; while [ "$i" -lt 60 ]; do start_for_test; dnsmasq_stop "$cfg"; i=$((i+1)); done ;;
esac
''')
    env=os.environ|{'RESOLVCONF':str(target),'BASEDHCPSTAMPFILE':str(d/'stamp'),
        'cfg':'main','localuse':'1','TEST_LOCALUSE':'1','ADD_LOCAL_DOMAIN':'1','DOMAIN':'lan',
        'DNS_SERVERS':'192.0.2.54','resolvfile':str(auto)}
    def run(action,**changes):
        if 'localuse' in changes:changes['TEST_LOCALUSE']=changes['localuse']
        subprocess.run(['sh',str(script),action],env=env|changes,check=True)
    # Upgrades from an existing auto symlink and a legacy regular file.
    conf.symlink_to(auto);run('start')
    expected=conf.read_text();assert expected.startswith('search lan\n')
    assert 'nameserver 192.0.2.54\n' in expected and 'nameserver 127.0.0.1\n' in expected
    assert conf.is_symlink() and os.readlink(conf)==str(target)
    run('stop');assert target.is_symlink() and os.readlink(target)=='resolv.conf.auto'
    assert conf.read_text()==upstream
    conf.unlink();conf.write_text('legacy\n');run('start');assert conf.read_text()==expected
    checks.append('auto symlink and legacy resolver migration; stop restores relative auto link')
    run('start',cfg='second');assert conf.read_text()==expected
    assert not list(confdir.glob('resolv.conf.*main')) and not list(confdir.glob('resolv.conf.*second'))
    checks.append('multiple instance names leave no unfinished temporary configuration')
    before=conf.read_bytes()
    run('start',localuse='0');run('stop',localuse='0');assert conf.read_bytes()==before
    checks.append('localuse=0 preserves resolver ownership')
    run('start',ADD_LOCAL_DOMAIN='0',DNS_SERVERS='')
    assert 'search ' not in conf.read_text() and conf.read_text().startswith('nameserver 127.0.0.1\n')
    run('start')
    allowed={expected,upstream};errors=[];reads=[0];stop=threading.Event()
    def reader():
        while not stop.is_set():
            try:
                value=conf.read_text()
                if value not in allowed:errors.append(repr(value))
                reads[0]+=1
            except FileNotFoundError:errors.append('resolver temporarily missing')
    worker=threading.Thread(target=reader);worker.start()
    try:run('cycle')
    finally:stop.set();worker.join()
    assert reads[0]>100 and not errors,(reads,errors[:4])
    assert auto.read_text()==upstream
    checks.append(f'60 real start/stop fragment cycles, {reads[0]} concurrent reads: no missing/partial resolver; ISP auto file unchanged')
    guard=(R/'Runtime/root/usr/bin/mwan4-rule-guard.sh').read_text()
    assert '/tmp/resolv.conf.d/resolv.conf.auto' in guard
    assert 'procd_set_param capabilities' not in t,'Unreviewed ujail/procd dependency imported'
    checks.append('MWAN4 DNS guard input unchanged; no jail capability migration')

provider=S/'target/linux/generic/pending-6.18/456-nvmem-implement-block-NVMEM-provider.patch'
lines=provider.read_text().splitlines(True);i=lines.index('+++ b/drivers/nvmem/block.c\n')+2
assert all(line.startswith('+') for line in lines[i:])
block=''.join(line[1:] for line in lines[i:])
assert hashlib.sha256(block.encode()).hexdigest()==m['prepared_sources']['drivers/nvmem/block.c']
register=block[block.index('static int blk_nvmem_register('):block.index('\nstatic void blk_nvmem_unregister(')]
stub=r'''
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
struct device_node { int unused; };
struct device { void *fwnode; };
struct disk { unsigned flags; };
struct block_device { struct disk *bd_disk; struct device bd_device; };
struct list_head { int unused; };
struct nvmem_device { int unused; };
struct blk_nvmem { struct nvmem_device *nvmem; struct device *dev; struct list_head list; };
struct nvmem_config { int id; struct device *dev; const char *name; void *owner,*priv;
    int (*reg_read)(void*,unsigned,void*,size_t); size_t size; int word_size,stride,read_only,root_only,ignore_wp;
    struct device_node *of_node; };
static int node_ok=1,layout_ok=1,alloc_ok=1,register_ok=0,added;
static size_t device_size=128;
static void *last_alloc;
static struct disk disk={1}; static struct block_device fixture_bdev={&disk};
static struct device_node node; static struct nvmem_device provider;
static struct list_head nvmem_devices; static int devices_mutex;
#define NVMEM_DEVID_NONE 0
#define GENHD_FL_NVMEM 1
#define GFP_KERNEL 0
#define THIS_MODULE NULL
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((intptr_t)(p))
#define dev_to_bdev(dev) (&fixture_bdev)
#define dev_of_node(dev) (node_ok?&node:NULL)
#define of_get_child_by_name(np,name) (layout_ok?&node:NULL)
#define bdev_nr_bytes(dev) (device_size)
#define dev_name(dev) "fixture"
#define to_of_node(p) (&node)
#define dev_err_probe(...) ((void)0)
#define mutex_lock(p) ((void)0)
#define mutex_unlock(p) ((void)0)
#define list_add_tail(p,q) (added=1)
#define kfree(p) free(p)
static void *kzalloc(size_t n,int flags) { return last_alloc=alloc_ok?calloc(1,n):NULL; }
static int blk_nvmem_reg_read(void*a,unsigned b,void*c,size_t d) { return 0; }
static struct nvmem_device *nvmem_register(struct nvmem_config *c) {
    return register_ok?&provider:(struct nvmem_device*)(intptr_t)-EINVAL;
}
'''
main=r'''
int main(void) {
    struct device dev={0};
    node_ok=0;assert(blk_nvmem_register(&dev)==0);node_ok=1;
    layout_ok=0;assert(blk_nvmem_register(&dev)==0);layout_ok=1;
    disk.flags=0;assert(blk_nvmem_register(&dev)==0);disk.flags=1;
    device_size=(size_t)INT_MAX+1;assert(blk_nvmem_register(&dev)==-EFBIG);device_size=128;
    alloc_ok=0;assert(blk_nvmem_register(&dev)==-ENOMEM);alloc_ok=1;
    assert(blk_nvmem_register(&dev)==-EINVAL);
    register_ok=1;assert(blk_nvmem_register(&dev)==0 && added);free(last_alloc);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='nvmem-error-path-') as d:
    d=Path(d);fixed=d/'fixed.c';fixed.write_text(stub+register+main)
    old=register.replace('\t\terr = PTR_ERR(bnv->nvmem);\n','').replace('\t\treturn err;','\t\treturn PTR_ERR(bnv->nvmem);')
    assert old!=register
    control=d/'old.c';control.write_text(stub+old+main)
    env=os.environ|{'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1'}
    for c in [fixed,control]:
        subprocess.run(['gcc','-O0','-g','-fsanitize=address',str(c),'-o',str(c.with_suffix(''))],check=True)
        result=subprocess.run([str(c.with_suffix(''))],env=env,text=True,capture_output=True)
        if c==fixed:assert result.returncode==0,result.stderr
        else:assert result.returncode!=0 and 'heap-use-after-free' in result.stderr,result.stderr
checks.append('actual blk_nvmem_register: seven success/error gates pass ASan; unpatched negative control detects heap-use-after-free')
out={'status':'passed','checks':checks,'firmware_built':False,'hardware_tested':False}
if a.report:a.report.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
