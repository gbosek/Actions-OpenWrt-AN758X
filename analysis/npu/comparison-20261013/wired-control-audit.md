# 当前6.18有线主机控制复核

日期：2026-10-13。只读源码复核，未执行设备代码或实机流量。源码是主报告中固定OpenWrt提交、补丁栈及931–934队列准备后的Linux6.18.52/6.18.54。以下行号以6.18.54准备树 `drivers/net/ethernet/airoha/` 为准；行号可能随补丁变化。

## 出口编号纠正

`airoha_eth.h:134–145` 定义 `FE_PSE_PORT_GDM4=9`、`FE_PSE_PORT_CDM4=7`。`airoha_ppe.c:472–475` 对port4写GDM4枚举，`:509–512` 保留NBQ。两版源码一致。因此XG2010G LAN3是PSE9/NBQ1、LAN1是PSE9/NBQ0；此前文档与诊断提示中的PSE7错误已修正，驱动枚举原本正确。

## 初始化和统计

`airoha_npu.c:83、:97–103、:136–161` 定义slot5、命令1–4和28字节消息。`:364–379` 对初始化结构先清零，再设PPE type=3、WAN mode=ETHER，没有动态第二个WAN selector。`:170–221` 通过core0 DMA消息等待DONE/成功结果。

`airoha_ppe.c:1753–1775` 先初始化PPE再统计；统计拒绝仅关闭统计能力而保留PPE。`airoha_npu.c:483–495` 将返回零统计地址解释为ENOSPC，避免使用空窗口。1456现有文件确实实现该API，不能因存在回退补丁就说它没有统计。

`airoha_ppe.c:744–800` 对符合条件的路由FOE保存原出口、channel/qid到meter/ACTDP，把出口临时改为PSE6；原PSE1用NBQ6，其他用NBQ5。Native AN7581 L2B、统计不可用/越界等不走此路径。`airoha_ppe_debugfs.c:169–200` 从保存字段解出 `egress_*`，用于区分统计中转与真实物理出口。

## 首包和绑定

`airoha_ppe.c:1433、:1461–1479` 从TC REDIRECT和PPPoE PUSH取得物理出口、SID，再编码FOE。路由模板初始挂入软件bucket，hash=0xffff（`:1195–1212`）；`airoha_eth.c:1082` 收到HIT_UNBIND_RATE_REACHED触发匹配未绑定硬件学习键并提交（PPE `:1128–1170`）。

普通commit为DMA shadow更新和SRAM直接MMIO（PPE `:864–919`）。NPU仍注册mailbox SRAM ops，但当前该驱动目录没有逐流调用者；不能把每次FOE新增描述成NPU mailbox往返。

**错误处理仍有缺口：** SRAM commit等待ACK且可能返回错误（`:864–882`）；一些上层调用（`:1059、:1156`）忽略commit返回值，继续保存hash/完成状态。这个路径必须与硬件BND和真实流量联合判断，TC成功/软件hash不是硬件成功的替代证据。本次是比较资料更新，尚未修改这些调用。

## PON和PPPoE编码

`airoha_ppe.c:365–418` 按EPON LLID或GPON最终服务VID选择bearer；GPON八种P-bit必须得到同一GEM/T-CONT，否则返回EOPNOTSUPP。T-CONT/LLID写channel/NBQ（`:485–518`），GPON GEM写etype、EPON etype为0（`:578–584`）。

PPPoE标志写IB1（`:443`），IPv4 SID写pppoe_id，IPv6写MAC元数据字段（`:552–565`）；普通以太网PPP session用ETH_P_PPP_SES（`:585–586`）。这证明输出封装，不证明SID参与入口学习或模板匹配。

## 桥接和双WAN剩余问题

桥接软件键要求ingress/MAC/单层精确802.1Q VID（`:1316–1349`），skb入口恢复DSA user port（`:1064–1112`），不接受QinQ及PCP/DEI匹配。Native AN7581 L2B保留硬件学习的源/入口信息（`:1031–1038`）；桥接PPP SID和IPTV组播不能据此宣称已经验收。

路由hash和compare主要使用原IP/端口、UDP位（`:661、:847–861`），不比较ingress/VID/SID。`:1143–1159` 可将多个同五元组模板写向同一个学习槽。双WAN重叠地址/相同五元组时存在覆盖风险；各自SID写入输出表不等于入口隔离已实现。现有补丁934只修桥接模板，不能宣称修复该路由歧义。

PON bearer更新时有锁内映射替换及出口清理（ETH `:4123`、PPE `:968–1001`），TC destroy有清理（PPE `:1581–1594`）。没有发现SID改变直接触发失效的闭环；空闲老化不能保证仍活跃的旧会话立即清除。后续应优先处理commit错误传播、路由歧义和会话生命周期，再结合实机双向BND/实际出口、计数、重拨与切线确认。
