"""Compare final FIT kernels with their exact normal/per-rootfs build inputs."""
from pathlib import Path
import gzip, hashlib, importlib.util, lzma, zlib

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def extract(image):
    repo=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('fit_reader',repo/'scripts/check-compatible-boost.py')
    fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
    raw=image.read_bytes();nodes,total=fit.fdt(raw);kernels=[]
    for node,props in nodes.items():
        if not node.startswith('/images/') or node.count('/')!=2 or props.get('type')!=b'kernel\0':
            continue
        if 'data' in props:
            data=props['data']
        else:
            size=fit.cells(props['data-size'])[0]
            start=fit.cells(props['data-position'])[0] if 'data-position' in props else ((total+3)&~3)+fit.cells(props['data-offset'])[0]
            assert 0<=start<=start+size<=len(raw),'FIT kernel outside artifact'
            data=raw[start:start+size]
        hashes=0
        for child,values in nodes.items():
            if not child.startswith(node+'/') or 'algo' not in values:
                continue
            algo=values['algo'].rstrip(b'\0').decode()
            value=(zlib.crc32(data)&0xffffffff).to_bytes(4,'big') if algo=='crc32' else hashlib.new(algo,data).digest()
            assert value==values['value'],'Final FIT kernel integrity failure'
            hashes+=1
        assert hashes,'Final FIT has no kernel integrity hash'
        comp=props.get('compression',b'none\0').rstrip(b'\0')
        assert comp in (b'gzip',b'lzma',b'none'),comp
        kernel=gzip.decompress(data) if comp==b'gzip' else lzma.decompress(data) if comp==b'lzma' else data
        assert b'Linux version 6.18.55 ' in kernel,'Wrong packaged Linux version'
        kernels.append(kernel)
    assert len(kernels)==1,'Expected exactly one kernel in final FIT'
    return kernels[0]

def check(kdir, image_dir):
    upgrades=list(image_dir.glob('*gemtek_xg2010g-squashfs-sysupgrade.itb'))
    recoveries=list(image_dir.glob('*gemtek_xg2010g-initramfs-recovery.itb'))
    assert len(upgrades)==len(recoveries)==1,'Expected exact XG2010G sysupgrade and recovery'
    normal=kdir/'Image'
    assert normal.is_file(),'Normal KDIR/Image input missing'
    kernel=extract(upgrades[0]);digest=sha(normal.read_bytes())
    assert digest==sha(kernel),'Final sysupgrade kernel differs from KDIR/Image input'
    recovery_kernel=extract(recoveries[0])
    roots=[path for path in kdir.glob('Image-initramfs.*') if path.is_file() and sha(path.read_bytes())==sha(recovery_kernel)]
    assert len(roots)==1,'Recovery does not match exactly one per-rootfs Image-initramfs input'
    return {
        'sysupgrade':{'image':upgrades[0].name,'image_sha256':sha(upgrades[0].read_bytes()),
                      'input_role':'KDIR/Image','input_sha256':digest,'decompressed_kernel_sha256':sha(kernel)},
        'recovery':{'image':recoveries[0].name,'image_sha256':sha(recoveries[0].read_bytes()),
                    'input_role':roots[0].name,'input_sha256':sha(roots[0].read_bytes()),
                    'decompressed_kernel_sha256':sha(recovery_kernel)},
        'all_match':True,
    }
