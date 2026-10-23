"""Rebase reviewed bridge fallback onto the retained 6.18.55 driver.

Only writes this Offload directory. Reads the supplied prepared kernel.
"""
from pathlib import Path
import argparse, difflib, hashlib, json

ap = argparse.ArgumentParser()
ap.add_argument('kernel', type=Path)
a = ap.parse_args()
root = Path(__file__).resolve().parents[1]
p = Path('drivers/net/ethernet/airoha/airoha_ppe.c')
before = (a.kernel / p).read_text()
text = before
assert 'Preserve the hardware-learned ingress key' in text
assert 'NPU refused flow stats' in text
assert 'Keep\n\t * the TC template intact' in text
text = text.replace('#include <linux/ip.h>', '#include <linux/etherdevice.h>\n#include <linux/if_bridge.h>\n#include <linux/ip.h>\n#include <linux/udp.h>\n#include <linux/tcp.h>\n#include <net/ip.h>', 1)

# Split the existing subflow function without discarding the native L2B fix.
start = text.index('static int\nairoha_ppe_foe_commit_subflow_entry(')
end = text.index('\nstatic void airoha_ppe_foe_insert_entry(', start)
old = text[start:end]
commit = old.replace('airoha_ppe_foe_commit_subflow_entry', 'airoha_ppe_foe_commit_subflow', 1)
commit = commit.replace('struct airoha_flow_table_entry *e,', 'const struct airoha_foe_entry *bridge,', 1)
commit = commit.replace('\tstruct airoha_flow_table_entry *f;\n', '', 1)
alloc_start = commit.index('\tf = kzalloc(')
alloc_end = commit.index('\tmemcpy(&hwe,', alloc_start)
commit = commit[:alloc_start] + commit[alloc_end:]
commit = commit.replace('e->data.', 'bridge->')
commit = commit.replace('\tairoha_ppe_foe_commit_entry(ppe, &hwe, hash, rx_wlan);\n\n\treturn 0;', '\treturn airoha_ppe_foe_commit_entry(ppe, &hwe, hash, rx_wlan);')
wrapper = r'''
static int
airoha_ppe_foe_commit_subflow_entry(struct airoha_ppe *ppe,
				    struct airoha_flow_table_entry *e,
				    u32 hash, bool rx_wlan)
{
	struct airoha_flow_table_entry *f;

	f = kzalloc(sizeof(*f), GFP_ATOMIC);
	if (!f)
		return -ENOMEM;
	/* Keep cleanup ownership even when hardware writes lack an ACK. */
	hlist_add_head(&f->l2_subflow_node, &e->l2_flows);
	f->type = FLOW_TYPE_L2_SUBFLOW;
	f->hash = hash;
	return airoha_ppe_foe_commit_subflow(ppe, &e->data, hash, rx_wlan);
}

static struct net_device *
airoha_ppe_foe_get_bridge_master_rcu(struct net_device *dev)
{
	struct net_device *master;

	if (netif_is_bridge_master(dev))
		return dev;
	master = netdev_master_upper_dev_get_rcu(dev);
	if (master && netif_is_bridge_master(master))
		return master;
	if (!is_vlan_dev(dev))
		return NULL;
	dev = vlan_dev_real_dev(dev);
	if (!dev)
		return NULL;
	if (netif_is_bridge_master(dev))
		return dev;
	master = netdev_master_upper_dev_get_rcu(dev);
	return master && netif_is_bridge_master(master) ? master : NULL;
}

/* Fail closed for incomplete RX contexts; WED may run before eth_type_trans. */
static bool airoha_ppe_foe_skb_is_local(const struct sk_buff *skb)
{
	const struct ethhdr *eh;
	struct net_device *master;
	bool local;

	if (!skb->dev || !skb_mac_header_was_set(skb))
		return true;
	eh = eth_hdr(skb);
	if ((u8 *)eh < skb->head ||
	    (u8 *)(eh + 1) > skb_tail_pointer(skb))
		return true;
	if (!is_valid_ether_addr(eh->h_source) ||
	    !is_valid_ether_addr(eh->h_dest) ||
	    ether_addr_equal_64bits(eh->h_dest, skb->dev->dev_addr))
		return true;
	rcu_read_lock();
	master = airoha_ppe_foe_get_bridge_master_rcu(skb->dev);
	local = master && ether_addr_equal_64bits(eh->h_dest, master->dev_addr);
	rcu_read_unlock();
	return local;
}

/* The fallback must never capture DHCP/ND/control traffic, including unicast
 * DHCP renewal. A real L4 flowtable match is still allowed before this guard.
 * Unknown, fragmented or non-linear headers use the normal CPU bridge path.
 */
static bool airoha_ppe_foe_bridge_control(const struct sk_buff *skb)
{
	const struct ethhdr *eh = eth_hdr(skb);
	const u8 *pos = (const u8 *)(eh + 1), *end = skb_tail_pointer(skb);
	__be16 proto = eh->h_proto;
	const struct udphdr *udp;
	unsigned int len, depth = 0;

	while (eth_type_vlan(proto)) {
		const struct vlan_hdr *vh = (const struct vlan_hdr *)pos;
		if (++depth > 2 || pos + sizeof(*vh) > end)
			return true;
		proto = vh->h_vlan_encapsulated_proto;
		pos += sizeof(*vh);
	}
	if (proto == htons(ETH_P_IP)) {
		const struct iphdr *ip = (const struct iphdr *)pos;
		if (pos + sizeof(*ip) > end || ip->version != 4 || ip->ihl < 5)
			return true;
		len = ip->ihl * 4;
		if (pos + len > end || ip_is_fragment(ip))
			return true;
		if (ip->protocol != IPPROTO_UDP)
			return ip->protocol != IPPROTO_TCP ||
			       pos + len + sizeof(struct tcphdr) > end;
		pos += len;
	} else if (proto == htons(ETH_P_IPV6)) {
		const struct ipv6hdr *ip6 = (const struct ipv6hdr *)pos;
		if (pos + sizeof(*ip6) > end || ip6->version != 6)
			return true;
		if (ip6->nexthdr != IPPROTO_UDP)
			return ip6->nexthdr != IPPROTO_TCP ||
			       pos + sizeof(*ip6) + sizeof(struct tcphdr) > end;
		pos += sizeof(*ip6);
	} else {
		return true;
	}
	if (pos + sizeof(*udp) > end)
		return true;
	udp = (const struct udphdr *)pos;
	return udp->source == htons(67) || udp->source == htons(68) ||
	       udp->dest == htons(67) || udp->dest == htons(68) ||
	       udp->source == htons(546) || udp->source == htons(547) ||
	       udp->dest == htons(546) || udp->dest == htons(547);
}

static bool
airoha_ppe_foe_prepare_bridge_subflow(struct airoha_ppe *ppe,
				      struct sk_buff *skb,
				      struct airoha_foe_entry *hwe)
{
	struct net_device_path_stack stack;
	struct net_device_path_ctx ctx = {};
	struct bridge_vlan_info ingress_vlan;
	const struct ethhdr *eh = eth_hdr(skb);
	struct airoha_flow_data data = {};
	struct net_device *master, *egress, *real_egress, *ingress;
	struct airoha_gdm_dev *egress_dev;
	const struct vlan_ethhdr *veh;
	u16 vid, proto;
	int err, i;
	bool ready = false;

	if (airoha_ppe_foe_bridge_control(skb))
		return false;
	ether_addr_copy(data.eth.h_dest, eh->h_dest);
	ether_addr_copy(data.eth.h_source, eh->h_source);
	rcu_read_lock();
	master = airoha_ppe_foe_get_bridge_master_rcu(skb->dev);
	if (!master)
		goto out;
	ingress = skb->dev;
	if (is_vlan_dev(ingress))
		ingress = vlan_dev_real_dev(ingress);
	/* A bridge/VLAN upper without an identifiable ingress port cannot
	 * prove STP/isolation eligibility in this early RX hook.
	 */
	if (!netif_is_bridge_port(ingress) ||
	    br_port_get_stp_state(ingress) != BR_STATE_FORWARDING)
		goto out;
	ctx.dev = master;
	if (is_vlan_dev(skb->dev)) {
		vid = vlan_dev_vlan_id(skb->dev);
		if (vid) {
			ctx.vlan[0].id = vid;
			ctx.vlan[0].proto = vlan_dev_vlan_proto(skb->dev);
			ctx.num_vlans = 1;
		}
	} else if (skb_vlan_tag_present(skb)) {
		ctx.vlan[0].id = skb_vlan_tag_get_id(skb);
		ctx.vlan[0].proto = skb->vlan_proto;
		ctx.num_vlans = 1;
	} else if (eth_type_vlan(eh->h_proto) &&
		   (u8 *)eh + VLAN_ETH_HLEN <= skb_tail_pointer(skb)) {
		veh = (const struct vlan_ethhdr *)eh;
		vid = ntohs(veh->h_vlan_TCI) & VLAN_VID_MASK;
		if (vid) {
			ctx.vlan[0].id = vid;
			ctx.vlan[0].proto = veh->h_vlan_proto;
			ctx.num_vlans = 1;
		}
	} else if (br_vlan_enabled(master) &&
		   netif_is_bridge_port(skb->dev) &&
		   !br_vlan_get_pvid_rcu(skb->dev, &vid) && vid &&
		   !br_vlan_get_proto(master, &proto)) {
		ctx.vlan[0].id = vid;
		ctx.vlan[0].proto = htons(proto);
		ctx.num_vlans = 1;
	}
	/* Starting at the bridge master does not perform ingress admission. */
	if (br_vlan_enabled(master) &&
	    (!ctx.num_vlans || !ctx.vlan[0].id ||
	     br_vlan_get_info_rcu(ingress, ctx.vlan[0].id, &ingress_vlan)))
		goto out;
	err = __dev_fill_forward_path(&ctx, eh->h_dest, &stack);
	if (err || stack.num_paths < 2 ||
	    stack.path[0].type != DEV_PATH_BRIDGE ||
	    ctx.num_vlans > ARRAY_SIZE(data.vlan.hdr))
		goto out;
	egress = (struct net_device *)stack.path[1].dev;
	if (!egress || egress == skb->dev || egress == ingress ||
	    !netif_running(egress) ||
	    !netif_carrier_ok(egress) ||
	    airoha_ppe_foe_get_bridge_master_rcu(egress) != master ||
	    br_port_get_stp_state(egress) != BR_STATE_FORWARDING ||
	    (br_port_flag_is_set(ingress, BR_ISOLATED) &&
	     br_port_flag_is_set(egress, BR_ISOLATED)))
		goto out;
	/* PON bearer lookup requires flow_offload_mutex and cannot run in RX.
	 * Ordinary routed/PON flowtable offload retains its existing locked path.
	 */
	real_egress = egress;
	airoha_get_dsa_port(&real_egress);
	egress_dev = netdev_priv(real_egress);
	if (airoha_is_valid_gdm_dev(ppe->eth, egress_dev) &&
	    (READ_ONCE(egress_dev->flags) & AIROHA_PRIV_F_PON))
		goto out;
	data.vlan.num = ctx.num_vlans;
	for (i = 0; i < ctx.num_vlans; i++) {
		data.vlan.hdr[i].id = ctx.vlan[i].id;
		data.vlan.hdr[i].proto = ctx.vlan[i].proto;
	}
	err = airoha_ppe_foe_entry_prepare(ppe->eth, hwe, egress,
					 PPE_PKT_TYPE_BRIDGE, &data, 0, 0,
					 &egress_dev);
	ready = !err;
out:
	rcu_read_unlock();
	return ready;
}
'''
text = text[:start] + commit + wrapper + text[end:]
start = text.index('static void airoha_ppe_foe_insert_entry(')
end = text.index('\nstatic int\nairoha_ppe_foe_l2_flow_commit_entry(', start)
insert = text[start:end]
insert = insert.replace('\tstruct airoha_flow_table_entry *e;', '\tstruct airoha_foe_entry bridge_hwe = {};\n\tstruct airoha_flow_table_entry *e;', 1)
insert = insert.replace('\tbool commit_done = false;', '\tbool commit_done = false, bridge_ready = false;\n\tbool local = airoha_ppe_foe_skb_is_local(skb) ||\n\t\t     airoha_ppe_foe_bridge_control(skb);', 1)
insert = insert.replace('\tspin_lock_bh(&ppe_lock);', '\tif (!local)\n\t\tbridge_ready = airoha_ppe_foe_prepare_bridge_subflow(ppe, skb,\n\t\t\t\t\t\t\t     &bridge_hwe);\n\n\tspin_lock_bh(&ppe_lock);', 1)
insert = insert.replace('\t    PPE_PKT_TYPE_BRIDGE)\n\t\tgoto l2_lookup;', '\t    PPE_PKT_TYPE_BRIDGE) {\n\t\tif (local)\n\t\t\tgoto unlock;\n\t\tgoto l2_lookup;\n\t}', 1)
insert = insert.replace('\t\tif (!airoha_ppe_foe_compare_entry(e, hwe))', '\t\tif ((local && e->type == FLOW_TYPE_L2) ||\n\t\t    !airoha_ppe_foe_compare_entry(e, hwe))', 1)
insert = insert.replace('\tif (commit_done)\n\t\tgoto unlock;', '\tif (commit_done || local)\n\t\tgoto unlock;', 1)
insert = insert.replace('\t\tairoha_ppe_foe_commit_subflow_entry(ppe, e, hash, rx_wlan);', '\t\tairoha_ppe_foe_commit_subflow_entry(ppe, e, hash, rx_wlan);\n\telse if (bridge_ready)\n\t\tairoha_ppe_foe_commit_subflow(ppe, &bridge_hwe, hash, rx_wlan);', 1)
text = text[:start] + insert + text[end:]

# The old 930 patch preserved the native key in the template, but the final
# generic memcpy could overwrite it again. Keep the learned key at commit.
needle = '\tmemcpy(&hwe->d, &e->d, sizeof(*hwe) - sizeof(hwe->ib1));\n\twmb();'
replacement = '''\tif (airoha_is_7581(eth) &&
\t    FIELD_GET(AIROHA_FOE_IB1_BIND_PACKET_TYPE, hwe->ib1) ==
\t    PPE_PKT_TYPE_BRIDGE &&
\t    FIELD_GET(AIROHA_FOE_IB1_BIND_PACKET_TYPE, e->ib1) ==
\t    PPE_PKT_TYPE_BRIDGE) {
\t\tstruct airoha_foe_l2b native_l2 = hwe->l2b;

\t\tmemcpy(&hwe->d, &e->d, sizeof(*hwe) - sizeof(hwe->ib1));
\t\tmemcpy(&hwe->l2b, &native_l2,
\t\t       offsetof(struct airoha_foe_l2b, data));
\t} else {
\t\tmemcpy(&hwe->d, &e->d, sizeof(*hwe) - sizeof(hwe->ib1));
\t}
\twmb();'''
assert text.count(needle) == 1
text = text.replace(needle, replacement, 1)
out = root / 'patches/950-net-airoha-bridge-cache-miss-fallback.patch'
header = ('Subject: net: airoha: port guarded VLAN-aware bridge cache-miss binding\n\n'
          'Based on naoki66 brightspeed 9990/9993/9994 at c15760c70b7ceeb85fd852d081b06c4bcac1cf5c.\n'
          'Retains local 930 native L2B and 931-937 reliability fixes.\n'
          'Local additions: explicit DHCP/control-plane and egress guards.\n'
          'Hardware-block gate and teardown are in the following patch.\n\n')
out.write_text(header + ''.join(difflib.unified_diff(before.splitlines(True), text.splitlines(True), fromfile='a/'+p.as_posix(), tofile='b/'+p.as_posix(), n=3)), newline='\n')
staged = root / 'validation/kernel' / p
staged.parent.mkdir(parents=True, exist_ok=True)
staged.write_text(text, newline='\n')
(root / 'validation/generation.json').write_text(json.dumps({'baseline_file': str(a.kernel/p), 'baseline_sha256': hashlib.sha256(before.encode()).hexdigest(), 'after_sha256': hashlib.sha256(text.encode()).hexdigest(), 'patch_sha256': hashlib.sha256(out.read_bytes()).hexdigest()}, indent=2)+'\n')
print(out)
