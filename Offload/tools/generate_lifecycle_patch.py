"""Generate the bounded flowtable lifecycle addition after patch 950."""
from pathlib import Path
import argparse, difflib
p = argparse.ArgumentParser(); p.add_argument('kernel', type=Path)
root = p.parse_args().kernel
repo = Path(__file__).resolve().parents[1]
changes = {}

path = Path('drivers/net/ethernet/airoha/airoha_eth.h')
before = (root/path).read_text(); after = before
after = after.replace('\tbool flow_stats_cap;', '''\tbool flow_stats_cap;
\tu32 bridge_ft_refs;
\tbool bridge_fallback_fault;
\tunsigned long *bridge_fallback;''', 1)
needle = 'int airoha_ppe_init(struct airoha_eth *eth);'
assert after.count(needle) == 1
after = after.replace(needle, needle+'\nvoid airoha_ppe_flowtable_ref(struct airoha_ppe *ppe, bool bind);', 1)
changes[path] = (before, after)

path = Path('drivers/net/ethernet/airoha/airoha_eth.c')
before = (root/path).read_text(); after = before
needle = 'static int airoha_dev_setup_tc_block(struct net_device *dev,\n\t\t\t\t     struct flow_block_offload *f)'
assert after.count(needle) == 1
after = after.replace(needle, needle[:-1]+',\n\t\t\t\t     bool flowtable)', 1)
start = after.index('static int airoha_dev_setup_tc_block(struct net_device *dev,')
end = after.index('\nstatic void airoha_tc_remove_htb_queue', start)
body = after[start:end]
body = body.replace('\tstruct flow_block_cb *block_cb;', '\tstruct flow_block_cb *block_cb;\n\tstruct airoha_gdm_dev *gdm = netdev_priv(dev);', 1)
body = body.replace('\t\t\treturn 0;\n\t\t}', '\t\t\tgoto bound;\n\t\t}', 1)
needle = '\t\tlist_add_tail(&block_cb->driver_list, &block_cb_list);\n\t\treturn 0;'
assert body.count(needle) == 1
body = body.replace(needle, '''\t\tlist_add_tail(&block_cb->driver_list, &block_cb_list);
bound:
\t\tif (flowtable)
\t\t\tairoha_ppe_flowtable_ref(gdm->eth->ppe, true);
\t\treturn 0;''', 1)
needle = '\t\t\tlist_del(&block_cb->driver_list);\n\t\t}\n\t\treturn 0;'
assert body.count(needle) == 1
body = body.replace(needle, '''\t\t\tlist_del(&block_cb->driver_list);
\t\t}
\t\tif (flowtable)
\t\t\tairoha_ppe_flowtable_ref(gdm->eth->ppe, false);
\t\treturn 0;''', 1)
after = after[:start]+body+after[end:]
needle = 'return airoha_dev_setup_tc_block(dev, type_data);'
assert after.count(needle) == 1
after = after.replace(needle, 'return airoha_dev_setup_tc_block(dev, type_data,\n\t\t\t\t\t type == TC_SETUP_FT);', 1)
changes[path] = (before, after)

path = Path('drivers/net/ethernet/airoha/airoha_ppe.c')
before = (root/path).read_text(); after = before
after = after.replace('#include <linux/airoha-eth.h>', '#include <linux/airoha-eth.h>\n#include <linux/bitmap.h>', 1)
needle = '\tint err = 0;\n\n\tif (airoha_is_7581(eth) &&'
assert after.count(needle) == 1
after = after.replace(needle, '''\tint err = 0;

\t/* Normal L4/cache commits take ownership when a slot is reused. */
\t__clear_bit(hash, ppe->bridge_fallback);
\tif (airoha_is_7581(eth) &&''', 1)
start = after.index('static void airoha_ppe_foe_insert_entry(')
end = after.index('\nstatic int\nairoha_ppe_foe_l2_flow_commit_entry(', start)
body = after[start:end]
body = body.replace('\tif (!local)\n', '\tif (!local && READ_ONCE(ppe->bridge_ft_refs) &&\n\t    !READ_ONCE(ppe->bridge_fallback_fault))\n', 1)
needle = '\telse if (bridge_ready)\n\t\tairoha_ppe_foe_commit_subflow(ppe, &bridge_hwe, hash, rx_wlan);'
assert body.count(needle) == 1
body = body.replace(needle, '''\telse if (bridge_ready && ppe->bridge_ft_refs &&
\t\t !ppe->bridge_fallback_fault) {
\t\tint err;

\t\terr = airoha_ppe_foe_commit_subflow(ppe, &bridge_hwe, hash, rx_wlan);
\t\t/* An ACK failure may still have written hardware: track it too. */
\t\t__set_bit(hash, ppe->bridge_fallback);
\t\tif (err) {
\t\t\tppe->bridge_fallback_fault = true;
\t\t\tdev_warn_ratelimited(ppe->eth->dev,
\t\t\t\t"bridge fallback commit failed (%d); further fallback disabled\\n", err);
\t\t}
\t}''', 1)
after = after[:start]+body+after[end:]
needle = 'int airoha_ppe_init(struct airoha_eth *eth)'
assert after.count(needle) == 1
lifecycle = '''/* Only TC_SETUP_FT counts: TC flower/QoS blocks cannot activate this path.
 * Called in process context by netdev flowtable bind/unbind. RX rechecks the
 * reference under ppe_lock before committing, closing the last-unbind race.
 */
void airoha_ppe_flowtable_ref(struct airoha_ppe *ppe, bool bind)
{
\tu32 hash, count = airoha_ppe_get_total_num_entries(ppe);
\tu32 sram_count = airoha_ppe_get_total_sram_num_entries(ppe);

\tspin_lock_bh(&ppe_lock);
\tif (bind) {
\t\tppe->bridge_ft_refs++;
\t\tspin_unlock_bh(&ppe_lock);
\t\treturn;
\t}
\tif (!ppe->bridge_ft_refs || --ppe->bridge_ft_refs) {
\t\tspin_unlock_bh(&ppe_lock);
\t\treturn;
\t}
\tspin_unlock_bh(&ppe_lock);

\tfor_each_set_bit(hash, ppe->bridge_fallback, count) {
\t\tstruct airoha_foe_entry *hwe;
\t\tint err = 0;

\t\tspin_lock_bh(&ppe_lock);
\t\tif (ppe->bridge_ft_refs) {
\t\t\tspin_unlock_bh(&ppe_lock);
\t\t\treturn;
\t\t}
\t\tif (!test_bit(hash, ppe->bridge_fallback)) {
\t\t\tspin_unlock_bh(&ppe_lock);
\t\t\tcontinue;
\t\t}
\t\thwe = ppe->foe + hash * sizeof(*hwe);
\t\thwe->ib1 &= ~AIROHA_FOE_IB1_BIND_STATE;
\t\thwe->ib1 |= FIELD_PREP(AIROHA_FOE_IB1_BIND_STATE,
\t\t\t\t      AIROHA_FOE_STATE_INVALID);
\t\twmb();
\t\tif (hash < sram_count)
\t\t\terr = airoha_ppe_foe_commit_sram_entry(ppe, hash);
\t\tif (!err)
\t\t\t__clear_bit(hash, ppe->bridge_fallback);
\t\telse
\t\t\tppe->bridge_fallback_fault = true;
\t\tspin_unlock_bh(&ppe_lock);
\t\tif (err) {
\t\t\t/* Abort at the first timeout, not once per remaining SRAM slot. */
\t\t\tdev_warn(ppe->eth->dev,
\t\t\t\t "bridge fallback cleanup failed (%d); hardware state unconfirmed\\n", err);
\t\t\treturn;
\t\t}
\t\tcond_resched();
\t}
}

'''
after = after.replace(needle, lifecycle+needle, 1)
needle = '\tppe_num_entries = airoha_ppe_get_total_num_entries(ppe);\n\tfoe_size ='
assert after.count(needle) == 1
after = after.replace(needle, '''\tppe_num_entries = airoha_ppe_get_total_num_entries(ppe);
\tppe->bridge_fallback = devm_bitmap_zalloc(eth->dev, ppe_num_entries,
\t\t\t\t\t\tGFP_KERNEL);
\tif (!ppe->bridge_fallback)
\t\treturn -ENOMEM;
\tfoe_size =''', 1)
changes[path] = (before, after)
text = '''Subject: net: airoha: gate bridge fallback on hardware flowtable lifetime

Count only successful TC_SETUP_FT bindings, not flower or QoS blocks. Recheck
under the PPE lock before fallback commits. Track fallback-owned slots, clear
ownership on ordinary slot reuse, and invalidate them at the last unbind.
Teardown yields between slots and stops at the first failed hardware ACK.
It does not pretend that a failed ACK confirms the hardware stopped.
---
'''
for path, (before, after) in changes.items():
    assert after != before
    text += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/'+path.as_posix(), tofile='b/'+path.as_posix()))
    dest = repo/'validation/gated'/path
    dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(after)
(repo/'patches/951-net-airoha-track-bridge-fallback-lifetime.patch').write_text(text)
print('951 generated')
