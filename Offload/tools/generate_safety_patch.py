#!/usr/bin/env python3
"""Harden the 949/950/951 result without replacing board or PHY code."""
from pathlib import Path
import argparse, difflib

ap = argparse.ArgumentParser()
ap.add_argument('kernel', type=Path)
args = ap.parse_args()
repo = Path(__file__).resolve().parents[1]
changes = {}

def edit(name, callback):
    before = (args.kernel/name).read_text()
    after = callback(before)
    assert after != before, name
    changes[name] = (before, after)

def replace(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new, 1)

def bridge_header(s):
    s = replace(s, 'u8 br_port_get_stp_state(const struct net_device *dev);',
                'u8 br_port_get_stp_state(const struct net_device *dev);\n'
                'void br_offload_state_sync(const struct net_device *dev);')
    s = replace(s, 'static inline u8 br_port_get_stp_state(const struct net_device *dev)',
                'static inline void br_offload_state_sync(const struct net_device *dev) {}\n\n'
                'static inline u8 br_port_get_stp_state(const struct net_device *dev)')
    s = replace(s, 'bool br_mst_enabled(const struct net_device *dev);',
                'bool br_vlan_is_forwarding_rcu(const struct net_device *dev, u16 vid);\n'
                'bool br_mst_enabled(const struct net_device *dev);')
    return replace(s, 'static inline bool br_mst_enabled(const struct net_device *dev)',
                   'static inline bool br_vlan_is_forwarding_rcu(const struct net_device *dev, u16 vid)\n'
                   '{\n\treturn false;\n}\n\n'
                   'static inline bool br_mst_enabled(const struct net_device *dev)')

def bridge_vlan(s):
    return replace(s, 'EXPORT_SYMBOL_GPL(br_vlan_get_info_rcu);', '''EXPORT_SYMBOL_GPL(br_vlan_get_info_rcu);

/* The caller holds RCU. Membership alone does not establish MST eligibility. */
bool br_vlan_is_forwarding_rcu(const struct net_device *dev, u16 vid)
{
	struct net_bridge_port *p = br_port_get_check_rcu(dev);
	struct net_bridge_vlan *v;

	if (!p)
		return false;
	v = br_vlan_find(nbp_vlan_group_rcu(p), vid);
	return v && br_vlan_should_use(v) &&
	       br_vlan_get_state(v) == BR_STATE_FORWARDING;
}
EXPORT_SYMBOL_GPL(br_vlan_is_forwarding_rcu);''')

def bridge_if(s):
    return s + '''
/* The caller holds RTNL. Pair with atomic STP changes under br->lock. */
void br_offload_state_sync(const struct net_device *dev)
{
	struct net_bridge *br;

	if (!netif_is_bridge_master(dev))
		return;
	br = netdev_priv(dev);
	spin_lock_bh(&br->lock);
	spin_unlock_bh(&br->lock);
	spin_lock_bh(&br->hash_lock);
	spin_unlock_bh(&br->hash_lock);
}
EXPORT_SYMBOL_GPL(br_offload_state_sync);
'''

def nf_header(s):
    return replace(s, '/* Function to register/unregister hook points. */', '''/* Observers may revoke coarse L2 offloads before a filtering hook is published.
 * Registration callbacks run in process context under nf_hook_mutex. They must
 * not register another netfilter hook. A failed revoke vetoes publication.
 */
struct notifier_block;
int nf_register_hook_observer(struct notifier_block *nb);
int nf_unregister_hook_observer(struct notifier_block *nb);

/* Function to register/unregister hook points. */''')

def nf_core(s):
    s = replace(s, 'static DEFINE_MUTEX(nf_hook_mutex);', '''static DEFINE_MUTEX(nf_hook_mutex);
static BLOCKING_NOTIFIER_HEAD(nf_hook_observers);

int nf_register_hook_observer(struct notifier_block *nb)
{
	return blocking_notifier_chain_register(&nf_hook_observers, nb);
}
EXPORT_SYMBOL_GPL(nf_register_hook_observer);

int nf_unregister_hook_observer(struct notifier_block *nb)
{
	return blocking_notifier_chain_unregister(&nf_hook_observers, nb);
}
EXPORT_SYMBOL_GPL(nf_unregister_hook_observer);''')
    s = replace(s, '#include <linux/netfilter.h>', '#include <linux/netfilter.h>\n#include <linux/notifier.h>')
    return replace(s, '\tmutex_lock(&nf_hook_mutex);\n\n\tp = nf_entry_dereference(*pp);\n\tnew_hooks = nf_hook_entries_grow(p, reg);', '''	mutex_lock(&nf_hook_mutex);
	err = notifier_to_errno(blocking_notifier_call_chain(&nf_hook_observers,
							    pf, (void *)reg));
	if (err) {
		mutex_unlock(&nf_hook_mutex);
		return err;
	}

	p = nf_entry_dereference(*pp);
	new_hooks = nf_hook_entries_grow(p, reg);''')

def eth_header(s):
    # Slots retain no net_device pointers, so unregister cannot leave a UAF.
    s = replace(s, 'struct airoha_ppe {', '''struct airoha_bridge_owner {
	int bridge_ifindex;
	int egress_ifindex;
	u16 vid;
	u8 dmac[ETH_ALEN];
};

struct airoha_ppe {''')
    return replace(s, '\tunsigned long *bridge_fallback;', '''	unsigned long *bridge_fallback;
	struct airoha_bridge_owner *bridge_owners;
	u64 bridge_generation;
	bool bridge_policy_blocked;
	bool bridge_topology_blocked;
	struct delayed_work bridge_topology_work;
	struct notifier_block bridge_nf_nb;
	struct notifier_block bridge_netdev_nb;
	struct notifier_block bridge_switchdev_nb;
	struct notifier_block bridge_switchdev_blocking_nb;''')

POLICY = r'''
/* A coarse L2 key cannot implement per-flow ACLs. Only unfiltered bridge paths
 * are eligible; an nft flowtable hook itself is not a filtering rule.
 */
static bool airoha_ppe_bridge_has_filter(const struct nf_hook_entries *head)
{
	struct nf_hook_ops **ops;
	unsigned int i;

	if (!head)
		return false;
	ops = nf_hook_entries_get_hook_ops(head);
	for (i = 0; i < head->num_hook_entries; i++)
		if (ops[i]->hook_ops_type != NF_HOOK_OP_NFT_FT)
			return true;
	return false;
}

static bool airoha_ppe_bridge_policy_allows(struct net_device *master,
					   struct net_device *ingress,
					   struct net_device *egress)
{
	struct net *net = dev_net(master);
	unsigned int i;

	/* The on-chip PPE is shared; do not infer namespace ownership. */
	if (!net_eq(net, &init_net))
		return false;
#ifdef CONFIG_NET_XGRESS
	if (rcu_access_pointer(ingress->tcx_ingress) ||
	    rcu_access_pointer(ingress->tcx_egress) ||
	    rcu_access_pointer(egress->tcx_ingress) ||
	    rcu_access_pointer(egress->tcx_egress))
		return false;
#endif
#ifdef CONFIG_NETFILTER_FAMILY_BRIDGE
	for (i = 0; i < ARRAY_SIZE(net->nf.hooks_bridge); i++)
		if (airoha_ppe_bridge_has_filter(rcu_dereference(net->nf.hooks_bridge[i])))
			return false;
#endif
#ifdef CONFIG_NETFILTER_INGRESS
	if (airoha_ppe_bridge_has_filter(rcu_dereference(ingress->nf_hooks_ingress)) ||
	    airoha_ppe_bridge_has_filter(rcu_dereference(egress->nf_hooks_ingress)))
		return false;
#endif
#ifdef CONFIG_NETFILTER_EGRESS
	if (airoha_ppe_bridge_has_filter(rcu_dereference(ingress->nf_hooks_egress)) ||
	    airoha_ppe_bridge_has_filter(rcu_dereference(egress->nf_hooks_egress)))
		return false;
#endif
	return true;
}
'''

LIFECYCLE = r'''
/* Called with ppe_lock held. A failed ACK remains owned and faults new fallback. */
static int airoha_ppe_bridge_invalidate_slot(struct airoha_ppe *ppe, u32 hash)
{
	struct airoha_foe_entry *hwe = ppe->foe + hash * sizeof(*hwe);
	int err = 0;

	hwe->ib1 &= ~AIROHA_FOE_IB1_BIND_STATE;
	hwe->ib1 |= FIELD_PREP(AIROHA_FOE_IB1_BIND_STATE, AIROHA_FOE_STATE_INVALID);
	wmb();
	if (hash < airoha_ppe_get_total_sram_num_entries(ppe))
		err = airoha_ppe_foe_commit_sram_entry(ppe, hash);
	if (err)
		ppe->bridge_fallback_fault = true;
	else
		__clear_bit(hash, ppe->bridge_fallback);
	return err;
}

static int airoha_ppe_bridge_revoke(struct airoha_ppe *ppe, const u8 *addr,
				   u16 vid, bool block, bool sleepable)
{
	u32 hash, count = airoha_ppe_get_total_num_entries(ppe);
	int err = 0;

	spin_lock_bh(&ppe_lock);
	ppe->bridge_generation++;
	if (block)
		ppe->bridge_policy_blocked = true;
	spin_unlock_bh(&ppe_lock);
	for_each_set_bit(hash, ppe->bridge_fallback, count) {
		struct airoha_bridge_owner *owner = &ppe->bridge_owners[hash];

		spin_lock_bh(&ppe_lock);
		if (test_bit(hash, ppe->bridge_fallback) &&
		    (!addr || (owner->vid == vid && ether_addr_equal(owner->dmac, addr))))
			err = airoha_ppe_bridge_invalidate_slot(ppe, hash);
		spin_unlock_bh(&ppe_lock);
		if (err) {
			dev_warn_ratelimited(ppe->eth->dev,
				"bridge revoke ACK failed (%d); fallback disabled\n", err);
			return err;
		}
		if (sleepable)
			cond_resched();
	}
	return 0;
}

static int airoha_ppe_bridge_nf_event(struct notifier_block *nb,
				     unsigned long family, void *ptr)
{
	struct airoha_ppe *ppe = container_of(nb, struct airoha_ppe, bridge_nf_nb);
	const struct nf_hook_ops *ops = ptr;

	if ((family != NFPROTO_BRIDGE && family != NFPROTO_NETDEV &&
	     !(family == NFPROTO_INET && ops->hooknum == NF_INET_INGRESS)) ||
	    ops->hook_ops_type == NF_HOOK_OP_NFT_FT)
		return NOTIFY_DONE;
	return notifier_from_errno(airoha_ppe_bridge_revoke(ppe, NULL, 0, true, true));
}

static void airoha_ppe_bridge_topology_work(struct work_struct *work)
{
	struct airoha_ppe *ppe = container_of(to_delayed_work(work),
					     struct airoha_ppe, bridge_topology_work);
	struct net_device *dev;
	u64 generation;
	bool retry;

	/* Never block module teardown which may itself own RTNL. */
	if (!rtnl_trylock()) {
		mod_delayed_work(system_wq, &ppe->bridge_topology_work,
				 msecs_to_jiffies(20));
		return;
	}
	spin_lock_bh(&ppe_lock);
	generation = ppe->bridge_generation;
	spin_unlock_bh(&ppe_lock);
	for_each_netdev(&init_net, dev)
		if (netif_is_bridge_master(dev))
			br_offload_state_sync(dev);
	spin_lock_bh(&ppe_lock);
	retry = generation != ppe->bridge_generation;
	if (!retry)
		ppe->bridge_topology_blocked = false;
	spin_unlock_bh(&ppe_lock);
	rtnl_unlock();
	if (retry)
		mod_delayed_work(system_wq, &ppe->bridge_topology_work,
				 msecs_to_jiffies(20));
}

static void airoha_ppe_bridge_topology_event(struct airoha_ppe *ppe, bool sleepable)
{
	spin_lock_bh(&ppe_lock);
	ppe->bridge_topology_blocked = true;
	spin_unlock_bh(&ppe_lock);
	airoha_ppe_bridge_revoke(ppe, NULL, 0, false, sleepable);
	mod_delayed_work(system_wq, &ppe->bridge_topology_work, 0);
}

static int airoha_ppe_bridge_netdev_event(struct notifier_block *nb,
					 unsigned long event, void *ptr)
{
	struct airoha_ppe *ppe = container_of(nb, struct airoha_ppe, bridge_netdev_nb);
	struct net_device *dev = netdev_notifier_info_to_dev(ptr);

	if (!netif_is_bridge_port(dev) && !netif_is_bridge_master(dev))
		return NOTIFY_DONE;
	switch (event) {
	case NETDEV_GOING_DOWN:
	case NETDEV_DOWN:
	case NETDEV_UNREGISTER:
	case NETDEV_CHANGE:
	case NETDEV_CHANGEADDR:
	case NETDEV_CHANGEMTU:
	case NETDEV_PRECHANGEUPPER:
	case NETDEV_CHANGEUPPER:
		/* Resume only after RTNL and bridge state writers have quiesced. */
		airoha_ppe_bridge_topology_event(ppe, false);
		break;
	}
	return NOTIFY_DONE;
}

static int airoha_ppe_bridge_switchdev_event(struct notifier_block *nb,
					    unsigned long event, void *ptr)
{
	struct airoha_ppe *ppe = container_of(nb, struct airoha_ppe, bridge_switchdev_nb);
	struct switchdev_notifier_fdb_info *fdb = ptr;

	switch (event) {
	case SWITCHDEV_FDB_ADD_TO_DEVICE:
	case SWITCHDEV_FDB_DEL_TO_DEVICE:
		/* FDB notifications follow the update. Generation fencing rejects
		 * preparations which resolved the previous destination port.
		 */
		airoha_ppe_bridge_revoke(ppe, fdb->addr, fdb->vid, false, false);
		break;
	case SWITCHDEV_FDB_ADD_TO_BRIDGE:
	case SWITCHDEV_FDB_DEL_TO_BRIDGE:
	case SWITCHDEV_FDB_FLUSH_TO_BRIDGE:
	case SWITCHDEV_PORT_ATTR_SET:
		/* External FDB notifications can precede the bridge's update. */
		airoha_ppe_bridge_topology_event(ppe, false);
		break;
	}
	return NOTIFY_DONE;
}

static int airoha_ppe_bridge_switchdev_blocking_event(struct notifier_block *nb,
						     unsigned long event, void *ptr)
{
	struct airoha_ppe *ppe = container_of(nb, struct airoha_ppe,
					     bridge_switchdev_blocking_nb);

	switch (event) {
	case SWITCHDEV_PORT_ATTR_SET:
	case SWITCHDEV_PORT_OBJ_ADD:
	case SWITCHDEV_PORT_OBJ_DEL:
		airoha_ppe_bridge_topology_event(ppe, true);
		break;
	}
	return NOTIFY_DONE;
}

static int airoha_ppe_bridge_observers_register(struct airoha_ppe *ppe)
{
	int err;

	INIT_DELAYED_WORK(&ppe->bridge_topology_work, airoha_ppe_bridge_topology_work);
	ppe->bridge_nf_nb.notifier_call = airoha_ppe_bridge_nf_event;
	ppe->bridge_netdev_nb.notifier_call = airoha_ppe_bridge_netdev_event;
	ppe->bridge_switchdev_nb.notifier_call = airoha_ppe_bridge_switchdev_event;
	ppe->bridge_switchdev_blocking_nb.notifier_call = airoha_ppe_bridge_switchdev_blocking_event;
	err = nf_register_hook_observer(&ppe->bridge_nf_nb);
	if (err)
		return err;
	err = register_netdevice_notifier(&ppe->bridge_netdev_nb);
	if (err)
		goto unregister_nf;
	err = register_switchdev_notifier(&ppe->bridge_switchdev_nb);
	if (err)
		goto unregister_netdev;
	err = register_switchdev_blocking_notifier(&ppe->bridge_switchdev_blocking_nb);
	if (!err)
		return 0;
	unregister_switchdev_notifier(&ppe->bridge_switchdev_nb);
unregister_netdev:
	unregister_netdevice_notifier(&ppe->bridge_netdev_nb);
unregister_nf:
	nf_unregister_hook_observer(&ppe->bridge_nf_nb);
	cancel_delayed_work_sync(&ppe->bridge_topology_work);
	return err;
}

static void airoha_ppe_bridge_observers_unregister(struct airoha_ppe *ppe)
{
	unregister_switchdev_blocking_notifier(&ppe->bridge_switchdev_blocking_nb);
	unregister_switchdev_notifier(&ppe->bridge_switchdev_nb);
	unregister_netdevice_notifier(&ppe->bridge_netdev_nb);
	nf_unregister_hook_observer(&ppe->bridge_nf_nb);
	cancel_delayed_work_sync(&ppe->bridge_topology_work);
}
'''

def ppe_source(s):
    s = replace(s, '\tconst struct vlan_ethhdr *veh;', '\t__be16 vlan_tci;')
    s = replace(s, '\t\tveh = (const struct vlan_ethhdr *)eh;\n\t\tvid = ntohs(veh->h_vlan_TCI) & VLAN_VID_MASK;',
                '\t\t/* skb MAC headers need not satisfy vlan_ethhdr alignment. */\n'
                '\t\tmemcpy(&vlan_tci, (const u8 *)eh + ETH_HLEN, sizeof(vlan_tci));\n'
                '\t\tvid = ntohs(vlan_tci) & VLAN_VID_MASK;')
    s = replace(s, '\t\t\tctx.vlan[0].proto = veh->h_vlan_proto;',
                '\t\t\tctx.vlan[0].proto = eh->h_proto;')
    s = replace(s, '#include <linux/if_bridge.h>', '#include <linux/if_bridge.h>\n#include <linux/netfilter.h>\n#include <linux/rtnetlink.h>\n#include <net/net_namespace.h>\n#include <net/switchdev.h>')
    s = replace(s, 'static bool\nairoha_ppe_foe_prepare_bridge_subflow', POLICY+'\nstatic bool\nairoha_ppe_foe_prepare_bridge_subflow')
    s = replace(s, '\t\t\t\t      struct airoha_foe_entry *hwe)\n{\n\tstruct net_device_path_stack stack;',
                '\t\t\t\t      struct airoha_foe_entry *hwe,\n'
                '\t\t\t\t      struct airoha_bridge_owner *owner)\n{\n\tstruct net_device_path_stack stack;')
    s = replace(s, '\tu16 vid, proto;\n\tint err, i;', '\tu16 vid = 0, proto, ingress_vid;\n\tint err, i;')
    s = replace(s, '\terr = __dev_fill_forward_path(&ctx, eh->h_dest, &stack);', '''	ingress_vid = ctx.num_vlans ? ctx.vlan[0].id : 0;
	if (br_vlan_enabled(master) &&
	    !br_vlan_is_forwarding_rcu(ingress, ingress_vid))
		goto out;
	err = __dev_fill_forward_path(&ctx, eh->h_dest, &stack);''')
    s = replace(s, '\t/* PON bearer lookup requires flow_offload_mutex and cannot run in RX.', '''	if ((br_vlan_enabled(master) &&
	     !br_vlan_is_forwarding_rcu(egress, ingress_vid)) ||
	    br_port_flag_is_set(ingress, BR_PORT_LOCKED | BR_PORT_MAB) ||
	    br_port_flag_is_set(egress, BR_PORT_LOCKED | BR_PORT_MAB) ||
	    !airoha_ppe_bridge_policy_allows(master, ingress, egress))
		goto out;
	owner->bridge_ifindex = master->ifindex;
	owner->egress_ifindex = egress->ifindex;
	owner->vid = br_vlan_enabled(master) ? ingress_vid : 0;
	ether_addr_copy(owner->dmac, eh->h_dest);
	/* PON bearer lookup requires flow_offload_mutex and cannot run in RX.''')
    s = replace(s, '\tstruct airoha_foe_entry bridge_hwe = {};', '''	struct airoha_foe_entry bridge_hwe = {};
	struct airoha_bridge_owner bridge_owner = {};
	u64 bridge_generation = READ_ONCE(ppe->bridge_generation);''')
    s = replace(s, '\t    !READ_ONCE(ppe->bridge_fallback_fault))', '\t    !READ_ONCE(ppe->bridge_fallback_fault) &&\n\t    !READ_ONCE(ppe->bridge_policy_blocked) &&\n\t    !READ_ONCE(ppe->bridge_topology_blocked))')
    s = replace(s, '\t\t\t\t\t\t     &bridge_hwe);', '\t\t\t\t\t\t     &bridge_hwe, &bridge_owner);')
    s = replace(s, '\telse if (bridge_ready && ppe->bridge_ft_refs &&\n\t\t !ppe->bridge_fallback_fault) {', '''	else if (bridge_ready && ppe->bridge_ft_refs &&
		 !ppe->bridge_fallback_fault && !ppe->bridge_policy_blocked &&
		 !ppe->bridge_topology_blocked &&
		 bridge_generation == ppe->bridge_generation) {''')
    s = replace(s, '\t\terr = airoha_ppe_foe_commit_subflow(ppe, &bridge_hwe, hash, rx_wlan);',
                '\t\tppe->bridge_owners[hash] = bridge_owner;\n'
                '\t\terr = airoha_ppe_foe_commit_subflow(ppe, &bridge_hwe, hash, rx_wlan);')
    s = replace(s, '\tspin_unlock_bh(&ppe_lock);\n\n\tfor_each_set_bit(hash, ppe->bridge_fallback, count) {',
                '\tppe->bridge_generation++;\n\tspin_unlock_bh(&ppe_lock);\n\n\tfor_each_set_bit(hash, ppe->bridge_fallback, count) {')
    s = replace(s, '/* Only TC_SETUP_FT counts:', LIFECYCLE+'\n/* Only TC_SETUP_FT counts:')
    s = replace(s, '\tif (!ppe->bridge_fallback)\n\t\treturn -ENOMEM;', '''	if (!ppe->bridge_fallback)
		return -ENOMEM;
	ppe->bridge_owners = devm_kcalloc(eth->dev, ppe_num_entries,
					 sizeof(*ppe->bridge_owners), GFP_KERNEL);
	if (!ppe->bridge_owners)
		return -ENOMEM;''')
    s = replace(s, '\terr = airoha_ppe_debugfs_init(ppe);\n\tif (err)\n\t\tgoto error_l2_flow_table_destroy;\n\n\treturn 0;', '''	err = airoha_ppe_debugfs_init(ppe);
	if (err)
		goto error_l2_flow_table_destroy;
	err = airoha_ppe_bridge_observers_register(ppe);
	if (err) {
		debugfs_remove(ppe->debugfs_dir);
		goto error_l2_flow_table_destroy;
	}

	return 0;''')
    return replace(s, 'void airoha_ppe_deinit(struct airoha_eth *eth)\n{\n\tstruct airoha_npu *npu;\n',
                   'void airoha_ppe_deinit(struct airoha_eth *eth)\n{\n\tstruct airoha_npu *npu;\n\n'
                   '\tairoha_ppe_bridge_observers_unregister(eth->ppe);\n')

edit('include/linux/if_bridge.h', bridge_header)
edit('net/bridge/br_vlan.c', bridge_vlan)
edit('net/bridge/br_if.c', bridge_if)
edit('include/linux/netfilter.h', nf_header)
edit('net/netfilter/core.c', nf_core)
edit('drivers/net/ethernet/airoha/airoha_eth.h', eth_header)
edit('drivers/net/ethernet/airoha/airoha_ppe.c', ppe_source)
text = '''Subject: net: airoha: constrain coarse fallback and revoke topology-stale flows

Only plain unfiltered bridge paths may create parentless L2 bindings. Revoke
before publishing filtering hooks, track FDB ownership, fence topology changes
and stale RX preparations, and query the bridge core's effective VLAN state.
Existing board/PHY/DHCP and parent-owned/routed paths remain unchanged.
---
'''
for name, (before, after) in changes.items():
    text += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='a/'+name, tofile='b/'+name))
    dest = repo/'validation/hardened'/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(after)
(repo/'patches/952-net-airoha-constrain-bridge-fallback-policy.patch').write_text(text)
print('952 generated: '+', '.join(changes))
