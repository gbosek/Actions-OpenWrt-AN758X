#!/usr/bin/env python3
"""Audit the shipped FIT/SquashFS, rather than only the build staging tree."""
from pathlib import Path
import argparse,struct,hashlib,json,subprocess,gzip,lzma,shutil,zlib,tempfile,re,os
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--recovered-image',action='store_true');p.add_argument('--build-commit',default=os.environ.get('GITHUB_SHA'));a=p.parse_args();S=a.source.resolve();O=a.output.resolve();O.mkdir(parents=True,exist_ok=True);P=Path(__file__).resolve().parents[1]
images=list((S/'bin/targets/airoha/an7581').glob('*gemtek_xg2010g*squashfs-sysupgrade.itb'));assert len(images)==1,images
image=images[0];d=image.read_bytes();h=struct.unpack('>10I',d[:40]);assert h[0]==0xd00dfeed
pos=h[2];strings=d[h[3]:h[3]+h[8]];stack=[];nodes={}
while True:
 t=struct.unpack_from('>I',d,pos)[0];pos+=4
 if t==1:
  end=d.index(b'\0',pos);stack.append(d[pos:end].decode());pos=(end+4)&~3
 elif t==2:stack.pop()
 elif t==3:
  n,off=struct.unpack_from('>II',d,pos);pos+=8;key=strings[off:strings.index(b'\0',off)].decode();nodes.setdefault('/'.join(stack),{})[key]=d[pos:pos+n];pos=(pos+n+3)&~3
 elif t==4:pass
 elif t==9:break
 else:raise ValueError(t)
def data(props):
 if 'data' in props:return props['data']
 off=int.from_bytes(props['data-position'],'big') if 'data-position' in props else ((h[1]+3)&~3)+int.from_bytes(props['data-offset'],'big')
 return d[off:off+int.from_bytes(props['data-size'],'big')]
blobs={};regions=[]
for name,props in nodes.items():
 typ=props.get('type',b'').rstrip(b'\0').decode()
 if typ not in ['kernel','filesystem','flat_dt']:continue
 blob=data(props);blobs[typ]=blob;checked=[]
 for child,cp in nodes.items():
  if child.rsplit('/',1)[0]!=name or 'algo' not in cp:continue
  algo=cp['algo'].rstrip(b'\0').decode();actual=struct.pack('>I',zlib.crc32(blob)&0xffffffff) if algo=='crc32' else hashlib.new(algo,blob).digest();assert actual==cp['value'],child;checked.append(algo)
 assert checked,name
 regions.append({'name':name,'type':typ,'sha256':hashlib.sha256(blob).hexdigest(),'checked_hashes':checked})
kernel=blobs['kernel'];compression=next(v.get('compression',b'none').rstrip(b'\0').decode() for v in nodes.values() if v.get('type')==b'kernel\0')
kernel=gzip.decompress(kernel) if compression=='gzip' else lzma.decompress(kernel) if compression=='lzma' else kernel
assert b'Linux version 6.18.55 ' in kernel
sq=O/'rootfs.squashfs';sq.write_bytes(blobs['filesystem'])
with tempfile.TemporaryDirectory(prefix='clean-ponwrt-audit-') as folder:
 root=Path(folder)/'root'
 unpack=next((str(x) for x in [S/'staging_dir/host/bin/unsquashfs',S/'staging_dir/host/bin/unsquashfs4'] if x.is_file()),None) or shutil.which('unsquashfs')
 assert unpack,'Install squashfs-tools or build unsquashfs4 before auditing'
 # /dev nodes are irrelevant to this file/module audit, and creating them
 # requires privileges unavailable on an ordinary GitHub-hosted runner.
 # Keep check=True: other extraction errors must still fail the audit.
 subprocess.run([unpack,'-no-progress','-d',str(root),'-excludes',str(sq),'dev'],check=True,stdout=subprocess.DEVNULL)
 required=['usr/libexec/rpcd/luci.airoha_npu','www/luci-static/resources/view/airoha_npu/status.js','www/luci-static/resources/view/status/include/29a_pon.js','etc/init.d/mwan4','lib/mwan4/mwan4.uc','lib/firmware/rtl8261n.bin','lib/modules/6.18.55/realtek.ko','etc/stable-refresh-source.json']
 required += ['etc/uci-defaults/99-stable-refresh']
 hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in required}
 assert json.loads((root/'etc/stable-refresh-source.json').read_text())==json.loads((P/'StableRefresh/source.json').read_text()),'Image component pins differ from expected build source'
 baseline=(root/'etc/uci-defaults/99-stable-refresh').read_text()
 assert 'omcproxy' not in baseline and 'ra-refresh' not in baseline
 view=(root/required[1]).read_text();assert 'require view' in view;assert "if (eth === '00:00:00:00:00:00->00:00:00:00:00:00')" not in view
 assert not (root/'usr/sbin/xg-dns-log-limit').exists()
 assert (root/'www/luci-static/argon').is_dir()
 assert (root/'etc/uci-defaults/99-stable-refresh').is_file()
 # Audit the actual FIT DTB as well as the prepared source.
 dtb=O/'board.dtb';dtb.write_bytes(blobs['flat_dt'])
 dtstext=subprocess.check_output(['dtc','-I','dtb','-O','dts',str(dtb)],text=True,stderr=subprocess.DEVNULL)
 hz=[(int(hi,16)<<32)|int(lo,16) for hi,lo in re.findall(r'opp-hz = <0x([0-9a-f]+) 0x([0-9a-f]+)>',dtstext)]
 assert hz and max(hz)<=1200000000,hz
 dtb.unlink()
 assert not (root/'www/luci-static/resources/view/status/include/15_xg2010g_pon.js').exists()
 for rel in ['usr/libexec/rpcd/luci.airoha_npu','etc/init.d/airoha-npu']:assert (root/rel).stat().st_mode&0o111,rel
 firmware_hash=hashlib.sha256((root/'lib/firmware/rtl8261n.bin').read_bytes()).hexdigest();assert firmware_hash=='ae1963b2a84a17eaa2fb9052591bdb5152838feda045d7313f45a8608b918533'
 module=(root/'lib/modules/6.18.55/realtek.ko').read_bytes();assert b'vermagic=6.18.55 ' in module
 tools=list((S/'staging_dir').glob('toolchain-aarch64*/bin/aarch64-openwrt-linux-musl-objdump'))
 objdump=str(tools[0]) if tools else shutil.which('aarch64-linux-gnu-objdump') or shutil.which('llvm-objdump')
 assert objdump,'AArch64-capable objdump is required'
 args=[objdump,'-dr']+(['--print-imm-hex'] if 'llvm' in objdump else [])
 asm=subprocess.check_output(args+[str(root/'lib/modules/6.18.55/realtek.ko')],text=True)
 fn=asm.split('<rtl826x_config_init>:',1)[1].split('\n\n',1)[0]
 assert re.search(r'mov\s+w0, #0x1e',fn), 'Actual RTL826x module does not contain baseline 30ms delay'
 (O/'rtl826x-config-init.asm').write_text(fn)
 if not a.recovered_image:
  source=(next((S/'build_dir').glob('target-*/linux-airoha_an7581/linux-6.18.55'))/'drivers/net/phy/realtek/realtek_main.c').read_text()
  assert 'rtl826x_config_init' in source
 result={'build_commit':a.build_commit,'recovered_image':a.recovered_image,'max_cpu_opp_hz':max(hz),'image':image.name,'image_sha256':hashlib.sha256(d).hexdigest(),'bytes':len(d),'kernel':'6.18.55','fit_regions':regions,'files_sha256':hashes,'rtl826x_delay_ms':30,'previous_local_feature_patch_sets_inherited':True,'baseline_build_commit':'a6440d4412a7de08d003afbba1501f0a2e28e980','hardware_tested':False,'scope':'Actual FIT hash, kernel banner, extracted SquashFS files and module disassembly; no flash or device stability claim'}
 (O/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
sq.unlink();shutil.copy2(image,O/image.name)
for f in image.parent.glob('*gemtek_xg2010g.manifest'):shutil.copy2(f,O/f.name)
shutil.copy2(P/'StableRefresh/source.json',O/'stable-refresh-source.json')
shutil.copy2(P/'StableRefresh/feed-pins.json',O/'feed-pins.json')
if (S/'.config').is_file():shutil.copy2(S/'.config',O/'build.config')
print(json.dumps(result,indent=2))
