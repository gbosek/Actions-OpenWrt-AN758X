# ClankerNPU 源码审计：XG2010G PPE 控制范围与缺口

日期：2026-10-13。方法：普通源码审计；未执行固件、未向设备写寄存器、未把源码阅读描述为 REA 二进制逆向。

## 样本与版本

- 仓库：`https://github.com/gbosek/ClankerNPU.git`。
- 本地：`/workspace/npu-drivers/ClankerNPU`。
- 精确提交：`7ad3c2fbcb95bf0f5c882e046b7a0a9cc16bb892`，合并 AN7581 NOWIFI 配置；本地工作树干净。
- 本次 `git ls-remote origin refs/heads/main refs/heads/master refs/heads/an7581-nowifi-profile` 核对：远端 `main` 仍为该提交；NOWIFI 分支为 `a19ce0946f9f1a8237bb2ecb786facfa61e27f78`。
- 此 checkout 未找到已生成 `.bin`、`.elf`、`.ko` 或 `.map` 文件。本次结论针对该提交的源码，未认定它对应用户之前运行的某个固件二进制，也未使用相邻 LibrANPU / FDK 文件冒充用户样本。
- 审计目标配置：`SOC=AN7581 WIFI=NOWIFI`。`Makefile:97` 的 `an7581-nowifi` 实际调用这一配置；默认 `make` 是 AN7583/MT7996，不能作为 XG2010G 的对应版本。

## 已确认的控制路径

### 启动与 hart 分工

- `link.ld:16`：代码 / rodata 地址 `0x84000000`，初始化数据 `0x3e900000`，后者 64 KiB。
- `crt0.S:26` 设置 GP，`:71` 冷启动清 BSS，`:125` 依次调用 `npu_init`、`core_dispatch`；各 hart 的 main 返回后在 `:135` 进入 debug idle。
- `npu_main.c:554` 初始化 trap / PLIC、UART、timer、mailbox；`:616` 向 MIB31 写 `INIT_COMPLETE`。`npu_regs.h:278` 定义启动标志 `0xcccccccc`。
- AN7581 NOWIFI 的 hart7 执行 tunnel loop（`npu_main.c:357`、`:173`）；该 loop 从对应 bridge channel dequeue，经 tunnel handler 处理后 egress。
- AN7581 NOWIFI 的 hart5 在 `npu_main.c:323` 只打印后返回；hart6 在 `:344` 也只打印后返回。其 idle loop `npu_dbg.c:354` 仅轮询 debug commands 和延时，不消费普通 PPE statistics packets。

通过主机 GCC 的纯预处理（`gcc -E -dM -DAN7581 -DNOWIFI -include npu_config.h -x c /dev/null`）核对配置边界：定义 `AN7581` / `AN758X` / `AN75XX`、`MAX_CORE_NUM=8`、`NPU_TIMER_NUM=4`、`HAS_TUNNEL`、`HAS_AN7581_NOWIFI`；没有 `HAS_WIFI`、`WIFI_KITE`、`WIFI_EAGLE`、`HAS_DBA`、`HAS_TR471`、`HAS_BME`、`HAS_NPU_WIFI_TX`。这里只执行预处理，不编译或运行 firmware。

| AN7581 NOWIFI hart | 实际 main 行为 | 源码起点 |
|---|---|---|
| 0 | `tdma_init` 仅调用 `sram_buf_init`，安装 debug counter ISR59，初始化 bridge buffer，返回后 debug idle；无 WiFi RX/TX ring loops | `npu_main.c:210`，`npu_tdma.c:65` |
| 1 | 所有 WiFi branches 被配置排除，返回后 debug idle | `npu_main.c:255` |
| 2 | 注册 timer ISR18；WiFi branch 被排除，返回后 debug idle | `npu_main.c:269` |
| 3 | 查询芯片 package capability，关闭无许可 USB / PCIe，再返回；WiFi wrapper 为空 | `npu_main.c:279`，`:59`，`npu_wifi.c:174` |
| 4 | 打印，WiFi wrapper 为空，返回后 debug idle | `npu_main.c:308` |
| 5 | DBA 和 WiFi branch 被排除，仅打印、返回后 debug idle | `npu_main.c:323` |
| 6 | 打印，WiFi wrapper 为空，返回后 debug idle | `npu_main.c:337` |
| 7 | bridge channel7 tunnel / fragmentation / reassembly loop；队列空且 ECN enabled 时检查 channels1/2 的 L4S | `npu_main.c:173`，`:357` |

### Mailbox 与 PPE 管理

- NPU mailbox 寄存器块 `0x1ec0c000`，`npu_mbox.c:25` 读取队列地址、字节长度、函数槽与 status。
- `npu_mbox.c:119` 初始化每 hart 的 80 字节 dispatch row；core0 callback slot5 注册 `hwnat_mail_dispatch`（`:160`）。
- PPE 子消息 handler 在 `npu_ppe.c:1044`，地址转换 `(base & 0x3fffffff) | 0x40000000`；仅接受 operation type1，验证消息长度至少8字节且为4字节倍数，再按各命令所需字段长度验证；未验证payload地址对齐。

| 内部命令 ID | 实际实现 | 源码起点 |
|---|---|---|
| 1 | HWNAT 初始化，读取 CDS / xPON HAL / WAN XSI / PPE type / WAN mode / AE WAN selector 等主机参数，配置 PPE | `npu_ppe.c:759`、`:1103` |
| 2 | HWNAT 停止，撤销 QDMA / PPE 控制与 misc 配置 | `npu_ppe.c:801`、`:1107` |
| 3 | SRAM API：向 PPE0 / PPE1 窗口复制表项、按索引执行 table command、清表 | `npu_ppe.c:1008`、`:1111` |
| 4 | 发布并清零 flow stats DRAM 窗口；没有实时 counter producer | `npu_ppe.c:974`、`:1114` |
| 5 | 打印 L4S 不支持后返回成功 | `npu_ppe.c:1117` |

表操作的实参结构在命令3中为 `+8 API ID`、`+12 size`、`+16 data`。API0 / API1 将恰好 80 字节主机数据复制至 PPE1 / PPE0 表窗口；API2 接收 4 字节参数对应索引并发出 table command；API3 按 AN7581 的 `PPE_TB_ENTRIES=0x4000` 清表。详见 `npu_ppe.c:843`、`:870`、`:886`、`:1013`。

完整 callback slot 配置范围：

| Core0 slot | AN7581 NOWIFI handler | 功能边界 |
|---|---|---|
| 0 | `nowifi_mail_dispatch` (`npu_mbox.c:102`) | 仅支持长度至少12字节、低 nibble0、type nibble3、内部 ID10 的 firmware version query，返回 `7<<16 | 8`；没有 WiFi datapath |
| 1 | `tunnel_mail_dispatch` (`npu_tunnel.c:21`) | tunnel 子命令，见下表 |
| 2、3、4、6、7 | NULL | dispatch row 被清零；TR471 slot4 编译排除 |
| 5 | `hwnat_mail_dispatch` | 上表 PPE 子命令1到5 |

每 hart 的 IRQ mailbox row 有8个 callback slots，硬件字段可编码16个；`npu_mbox.c:72` 拒绝 callback slot8到15。raw-data message path 使用同一 dispatch row 的数据 / length 区域（`:60`）；它不同于 PPE callback调用。queue8 的 NPU→host reply 在 `npu_mbox.c:172` 发出。

Tunnel slot1 完整子命令表来自执行数据 `npu_globals.c:334`，不能用 PPE 子命令号与其混淆：

| ID | handler | 实际用途 / 行号 |
|---|---|---|
| 0 | `tunnel_mail_store_hdr` | 存储50字节 tunnel header，`npu_tunnel.c:629` |
| 1 | `tunnel_mail_nop` | 无动作，回复1，`:670` |
| 2 | `tunnel_mail_vxlan_mtu` | 设置 encap MTU，`:676` |
| 3 | `tunnel_mail_store_srv6` | 存储 SRv6 header / header length，`:639` |
| 4 | `tunnel_mail_set_srv6_addr` | 设置本机 SRv6 IPv6 地址，`:658` |
| 5 | `tunnel_mail_frag_mtu` | 设置 `fragment_mtu[idx]`，`:617`；跨源码引用中没有该数组的进一步读取，实际 fragmentation 使用 descriptor MTU (`:423`) |
| 6 | `tunnel_mail_bridge_dbg` | dump / reset bridge counters 或 flush reassembly，`:685`，`npu_bridge.c:99` |
| 7 | `tunnel_mail_map_info` | 设置 MAP info buffer 地址，`:692` |
| 8 | `tunnel_mail_l4s` | ECN enable / debug / queue selector，`:700`，`npu_l4s.c:14` |
| 9 | NULL | 调用返回0 |

Tunnel dispatcher 有 ID 界限检查，但 tunnel 子函数多数忽略传入 `cnt`；其长度验证不能借用 PPE dispatcher 现有的验证来宣称同等完整。源码内 debug block / UART 控制另提供寄存器、内存、CSR、profile 操作，属于调试控制平面，未用于本次设备操作。

该固件不在这些 API 中解码 NAT、PPPoE session、VLAN 或 PON bearer 字段，而是消费主机已准备的完整 80 字节 FOE 内容。因而可确认其存在硬件表传输接口，但不能从该接口推导“每个字段已和当前 Linux 6.18、XG2010G 验证兼容”。

`ppe_tbl_cmd` 在 `npu_ppe.c:860` 最多读取 10 次 bit31；超时无错误返回，调用者仍可返回1。Mailbox 回复成功本身不能作为硬件表已经成功绑定的证明。

FOE 的 commit / delete / invalidation 边界：

- Commit API 是“两次消息”：先 API0/1 填 entry window，再 API2 传 hash/index 发写表命令。当前主机的旧接口实现在 `airoha_npu.c:428`；Clanker 对应处理见上述 API。
- Clanker 没有独立 delete / route invalidate / PPPoE disconnect 指令。单项失效需要主机准备 state INVALID 的 FOE 再覆盖；全局清表使用 API3。硬件老化 / keepalive 配置提供生命周期机制，但不是 mwan failover 控制器。
- **当前准备后的6.18.54 PPE driver 的正常 SRAM commit / flush 已直接走主机 FE MMIO**：`airoha_ppe.c:864` 写80字节窗口 + table command、等待ACK；`:914` 调用该函数；`:1687` flush循环；`:929` 设置 INVALID 后重新 commit。`airoha_npu.c` 仍注册上述 mailbox ops，但全目录检索未找到这两个 ops 的实际调用者。不能把 Clanker 提供 SRAM mailbox API 误写成当前 Linux每次新增流都实际使用它。
- 该主机 direct-MMIO 与 firmware API 是两种访问路径；两者都不应被当作普通 data packet 每包必经的 CPU/NPU控制调用。

### PPE 寄存器配置

- QDMA / 默认 CPU port / WAN selector：`npu_ppe.c:159`。配置为全局主机参数分支，没有根据单条 mwan3 / mwan4 connection mark 选择逻辑 WAN 的固件决策代码。
- EtherType parser：`npu_ppe.c:298` 配置 802.1Q、802.1ad、IPv4、IPv6；`:316` 可根据 CDS / xPON HAL 关闭 IPv6 parsing slot。
- table size / hash / walker：`npu_ppe.c:405`、`:420`。AN7581 源码配置总 16384 entries，PPE1 索引边界 `0x2000`；仅 CHIP_FAMILY14 执行第二 PPE 配置。
- 未绑定 / 已绑定老化、keepalive、bind rate limit：`npu_ppe.c:498`、`:526`。
- `tunnel_init` 在 `npu_ppe.c:568` 设置上述 parser、table、timer、PPE control、egress。具体未知硬件位含义不能仅由注释当作完整逆向证明。

完整 HWNAT_INIT 参数消费表（消息 length28 bytes；`npu_ppe.c:759`）：

| Payload offset | 参数 | 实际消费 |
|---|---|---|
| +8 u8 | `hwnat_cds` | 非零跳过 IPv4/IPv6 EtherType init，并与 xPON flag共同触发 IPv6 parser fixup；`:307`、`:320`、`:661` |
| +9 u8 | `hwnat_xpon_hal_api_ng` | 触发 IPv6 parser fixup，`:320`；不是 GEM/TCONT表接口 |
| +10 u8 | `hwnat_wan_xsi` | QDMA port分支 / 默认 unmatched CPU port，`:170`、`:174`、`:190`、`:210` |
| +11 u8 | `hwnat_ct_joyme4` | 保存但全源码没有读取点；不是已实现的 conntrack policy功能 |
| +12 u8 | `hwnat_max_packet_2000` | 修改 FE packet-size register，`:374` |
| +13..15 | padding | handler不读取 |
| +16 u32 | `hwnat_ppe_type` | 影响旧芯片 misc branch，以及 GDM egress组合，`:473`、`:679` |
| +20 u32 | `hwnat_wan_mode` | 当不等于1并且 WAN XSI/AE selector均0时才改 QDMA1，`:190` |
| +24 u32 | `hwnat_ae_wan_sel` | 仅影响上述 QDMA1判断，`:190` |

`hwnat_ready` 在 init设为1但全源码没有读取点；deinit也没有把它清为0，因而不能把它当可靠的 host-visible readiness handshake。真正需要核对的是 mailbox结果、FE/PPE配置及流绑定。当前主机 `airoha_npu.c:364` 对 init数据先清零，仅显式设置 `ppe_type=PPE_TYPE_L2B_IPV4_IPV6` 和 `wan_mode=QDMA_WAN_ETHER`；这说明不是所有协议标志都已由当前 host动态注入。

## 已查清的关键缺口

### 1. Function4 成功与实时流量统计之间存在缺失

`npu_ppe.c:974` 的执行代码：

1. 读取主机 high counter DMA buffer 地址。
2. 明确把 `counter_producer_registered` 设为0（`:980`）。
3. 将 `NPU_FOE_STATS_ADDR` 写入返回字段（`:988`）。
4. 将该 DRAM 窗口的每个字清零（`:997`）。
5. 设置 `setup_complete=1` 并返回1（`:1002`）。

实际窗口由 `link.ld:94` 定义为 `0x84900000`、大小 `0x10000`。跨该提交全部 C / header / assembly 搜索 `counter_producer_registered`、`NPU_FOE_STATS`、`npu_flow_stats_setup` / `foe_stats`，只发现配置、清零、debug 输出和相关说明；没有增加每条 FOE packets / bytes 或对 host DMA 高字执行 carry 的代码。源码注释 `npu_ppe.c:956` 同样坦率说明尚未实现 producer，但结论来自执行代码和引用检索，不依赖 README 宣称。

不能把这一 setup 回成功或零窗口称为有效硬件统计。也不能把其 WiFi byte counters（`npu_wifi_fwd.c`、`npu_wifi_rx.c`）误认为主机 PPE per-FOE statistics。

### 2. 当前主机的 stats 数据通路与 NOWIFI hart5/6 分工不匹配

当前准备后的 Linux 6.18.54 主机源码：
`/workspace/npu-analysis/sources/linux-6.18.54/drivers/net/ethernet/airoha/airoha_ppe.c:744` 的 `airoha_ppe_foe_flow_stats_update`，保存实际 PSE / NBQ / QoS 后，把符合条件的 routed FOE 改为 PSE6、NBQ5或6（`:792` 到 `:800`）。Native AN7581 L2B 被排除，不能把此路径套给所有 bridge entries。

Clanker AN7581 NOWIFI 的 hart5 / hart6 只运行上述 idle loops；不存在与1456相当的两路统计包处理、counter 更新及原出口恢复转发代码。单看 function4 回复成功，无法建立该主机 stats mode 数据通路兼容性。静态证据足以说明它不能作为当前1456统计通路的等价替代；尚无本次实机数据能将用户先前任何故障归因于这一缺口。

### 3. PPPoE 可见代码范围有限

- `npu_tunnel.c:357` 的 `pppoe_len_patch` 在 tunnel fragmentation / reassembly 中修正 PPPoE payload length；只显式处理无 tag 或一层 0x8100 tag 的 0x8864 session packet。
- `npu_l4s.c:48` 的 `l4s_ecn_mark` 能跳过 VLAN 并识别 PPPoE 中的 IPv4 / IPv6，对 ECN 位做修改。
- 这些执行代码并未建立 PPPoE 会话表，没有两路 PPPoE discovery / session 选择、mwan route / mark 决策，也没有独立的按 WAN / peer / session ID 隔离逻辑。
- 普通 PPPoE routed NAT offload 的 Session ID / encap 字段可由主机放进不透明 FOE 数据后交硬件使用；“本源码未实现会话管理”不能扩大成“硬件绝对不支持 PPPoE”。能否正确工作需核对主机 FOE 编码和两路实际会话 / 出口。

### 4. PON GEM / TCONT 与多 WAN

- `npu_ppe.c:761` 读取 xPON HAL flag，WAN XSI / AE selector 在 QDMA 全局配置中使用。这能证明有相关运行时参数，不能证明 XG2010G 的 PON 与 LAN3 双 PPPoE 拓扑经过验证。
- `npu_dba.c` 确实包含 TCONT DBA mailbox 和调度代码，但全文件在 `HAS_DBA` 条件内（`:10`）；`npu_config.h:63` 只对 AN7583 且非 NOWIFI 定义该条件。它不进入 AN7581 NOWIFI 构建。
- 本配置没有自行分配 / 查找 GEM ID、TCONT，并将其按每条 NAT / PPPoE flow 写入 FOE 的代码。这些 bearer 信息仍依赖主机 / PON 层及80字节表项内容。
- 全局 HWNAT WAN selector 并非 OpenWrt 的两路逻辑 WAN。固件没有 connection policy / failover controller；不能为了“双WAN”擅自将 PON 与 LAN3 映射为未经证实的两个 hardware WAN slots。

## 对用户目标的结论

1. ClankerNPU 的源码可以辅助比对启动、mailbox、PPE register / SRAM table command 等机制；这一部分已审计到具体代码。
2. 不能称“Clanker 已被完整 REA 逆向”。它是开源源码，没有与用户实跑固件哈希对应的二进制样本，本次未做 binary-to-source 一致性验证。
3. 已查明其当前 AN7581 NOWIFI 代码缺少1456相应的 per-flow stats producer，且 hart5 / hart6 统计数据通路未实现。存在 parser / API 函数并不等于各方向 / 双 PPPoE 硬件转发验证完成。
4. 按用户决定，当前 XG2010G 实现继续使用1456固件，参考上传的5.4和烽火6.6原厂样本完善 Linux PPE / PON 主机控制。此次审计未改动两目标仓库，也未让 Clanker 替换目标固件。
5. 所有 firmware code / host ABI / register 结论须与硬件绑定表、计数增量、PPPoE session ID、PON bearer 和实际出接口结果分开报告。没有实机验证前，不能声称 WAN→LAN、LAN→WAN、LAN→LAN、双WAN已全部成功。
