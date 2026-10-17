#!/usr/bin/env python3
"""Check the useful 059895c backports in the final prepared Airoha driver."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from check_ppe_functions import function


def verify(kernel, report=None):
    driver = kernel / 'drivers/net/ethernet/airoha'
    source = {name: (driver / name).read_text() for name in
              ('airoha_eth.c', 'airoha_eth.h', 'airoha_ppe.c', 'airoha_regs.h')}
    eth, ppe = source['airoha_eth.c'], source['airoha_ppe.c']
    flush = function(ppe, 'airoha_ppe_flush_sram_entries')
    assert 'return err;' in flush and 'return 0;' in flush
    assert 'break;' not in flush and 'int i, err' not in flush, 'SRAM failure swallowed'
    retry = function(eth, 'airoha_qdma_set_trtcm_param')
    assert 'TRTCM_CONFIG_RETRY_MAX' in retry and 'data == val' in retry
    assert 'airoha_qdma_get_trtcm_param' in retry
    cleanup = function(eth, 'airoha_qdma_tx_cleanup')
    assert 'q->flushing = true' in cleanup and 'netdev_tx_completed_queue' in cleanup
    assert 'netdev_tx_reset_subqueue' not in function(eth, 'airoha_dev_stop')
    assert 'skb_frag_dma_map' in eth and 'AIROHA_DMA_MAP_PAGE' in eth
    mac = function(eth, 'airoha_fe_maccr_init')
    assert re.search(r'FIELD_PREP\(GDM_LONG_LEN_MASK,\s*AIROHA_MAX_RX_SIZE\)', mac)
    assert 'VLAN_ETH_HLEN' in ppe and 'VLAN_ETH_HLEN' in eth
    assert re.search(r'REG_PPE_MTU\(_m, _n\).*\(_n\) / 2', source['airoha_regs.h'])
    assert 'mib_prev' in eth and 'mib_prev' in source['airoha_eth.h']
    assert re.search(r'\(u32\)\(val - dev->stats.mib_prev\.', eth)
    assert 'rt_tos2priority(dsfield)' in ppe and 'FIELD_PREP(AIROHA_FOE_QID, priority)' in ppe
    assert 'if (!ppe->flow_stats_cap)' in ppe, 'PPE NPU-stats refusal fallback missing'
    result = {
        'openwrt_commit': '059895c014bdc4ecb24487b7983c528f1e97822a',
        'kernel': kernel.name,
        'sram_error_return': True, 'trtcm_retry_readback': True,
        'shared_tx_bql': True, 'fragment_page_dma': True,
        'rx_limit_and_ppe_l2_mtu': True, 'lossless_mib': True,
        'flowtable_qos_dscp': True, 'ppe_stats_refusal_fallback': True,
        'source_sha256': {name: hashlib.sha256((driver / name).read_bytes()).hexdigest() for name in source},
        'scope': 'Actual prepared driver source; binary build and hardware checks recorded separately',
    }
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--kernel', type=Path)
    group.add_argument('--build-dir', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    kernel = args.kernel
    if kernel is None:
        found = [p for p in args.build_dir.glob('target-*/linux-*/linux-6.18.*')
                 if (p / 'drivers/net/ethernet/airoha/airoha_eth.c').is_file()]
        assert len(found) == 1, 'Expected one prepared Airoha kernel'
        kernel = found[0]
    verify(kernel, args.report)
