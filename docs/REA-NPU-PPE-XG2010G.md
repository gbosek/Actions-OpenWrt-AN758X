# XG2010G：REA 逆向与 PPE/NPU 卸载改动

日期：2026-10-13。状态：候选驱动与构建集成，两个内核版本的驱动对象编译通过，尚未完成新镜像实机验收。

## 目标与设备拓扑

目标是让硬件能够表达的转发连接进入 PPE：WAN→LAN、LAN→WAN、LAN→LAN 和双 WAN。路由选择、连接建立及异常报文仍经过 Linux。硬件绑定后，同一连接的后续报文由 FE/PPE/NPU/QDMA 转发。

用户确认：XG2010G 使用 PON＋LAN3（EN8811H 2.5G），两路都拨 PPPoE。以下映射来自两套源码中的 `target/linux/airoha/dts/an7581-gemtek-xg2010g.dts` 和 Airoha 驱动，须与设备诊断输出核对。

| 物理接口 | 硬件连接 | PPE 的实际出口 | PPPoE 出口需要的内容 |
| --- | --- | --- | --- |
| PON / pon0 | GDM2 | PSE2；NBQ/CHANNEL 为 T-CONT 或 LLID | 独立 SID、对端 MAC、服务 VLAN、GEM/T-CONT |
| LAN3 / EN8811H | GDM4、NBQ1、USB PCS、2500BASE-X | PSE7、NBQ1 | 独立 SID、对端 MAC、服务 VLAN |
| LAN1 | GDM4、NBQ0 | PSE7、NBQ0 | 普通 LAN 转发 |
| LAN2 | GDM3、NBQ5 | PSE3、NBQ5 | 普通 LAN 转发 |

LAN3 的逻辑 WAN 身份由 PPPoE、路由和 MWAN4 决定。芯片的 WAN selector 与 OpenWrt 的 WAN 接口数量没有一一对应关系。当前候选改动保留实际 GDM/NBQ 出口；没有引入尚未证实的第二个全局 WAN selector。

## 样本与分析工具

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| naoki66_5.4_npu_rv32.bin | 88596 | `5140747f2ce176ac6622522184651403594d4f5624bf2238543136a0f3bfe7b8` |
| naoki66_5.4_npu_data.bin | 2724 | `d59db24e7d97453a689144a94d3b10cfb873197dfcbea0cb1d279d38cced87b1` |
| official1456_en7581_npu_rv32.bin | 120272 | `6e7b9cb9769398d5c0a603d758626719ee83610e0dd2a5bc0b66258e2ad1057f` |
| official1456_en7581_npu_data.bin | 3100 | `0e742e7bef0d8f4c1537d7c17de9b601274e42b18660dfde6deba81ac395c761` |
| 6.6 ZIP 内 npu_rv32.bin | 98260 | `d74aa2f81214fda24725529a6000bb05c22c2da6f40dfd63f0c20ef067db08af` |
| 6.6 ZIP 内 npu_data.bin | 2940 | `11013d492120f406586413bad2689305f2713da2f0ebdde21feaf03fc93b0e3a` |
| 6.6 ZIP 内 npu.ko | 10968 | `1f8f2e2a7eab33197b24204e4c4ea45aa952cabf10f331337bb6c8bc237a079d` |

`npu.ko` 是原始 arm64 ELF ET_REL 模块，vermagic 为 6.6.23，已通过 REA 的 Ghidra provider 处理。证据文件位于 [analysis/npu](../analysis/npu)。

| REA 操作 | Evidence ID |
| --- | --- |
| overview | `ev_96a2d5820cf24eb2730ff966d0ad71220dd3ee7210fc72d27a4f40061f8930aa` |
| function init_module | `ev_64f4a67e83a07cd7d57711735856d382857229253ce245d6a480e1973617a4d7` |
| function fileCopyToSram | `ev_6019a052f843dbc7e965379288acd4c4215f734dc6d01770106c4496b12f6086` |

REA 当前 raw profile 没有 RV32 支持。因此三个原始固件由独立 Ghidra 12.1.4 分析，结果明确标记为 `direct-ghidra`，没有伪造 ELF 头或 REA Evidence ID。映射：代码 `0x84000000`，数据 `0x3e900000`。GP 从启动代码求得，5.4/6.6/1456 分别为 `0x3e901258`、`0x3e901328`、`0x3e9013a0`。

Ghidra 对部分指令和候选函数有解码警告，自动函数边界也有局限；本报告列出的关键地址已结合调用、数据表和 Linux 协议定义核对。`FUN_...` 名称来自分析器，不是原厂符号。

## 控制链路已经查到哪些内容

### 原厂 6.6 Linux 模块

REA 映射中的 `init_module` 为 `0x1002b8`，`fileCopyToSram` 为 `0x100144`。这些是分析器的模块重定位地址，不是光猫运行地址。

模块加载 `/userfs/npu_rv32.bin`（上限 2 MiB）和 `/userfs/npu_data.bin`（上限 64 KiB，传入地址 `0xbe900000`），随后调用 `set_npu_needed_info`、`boot_npu_all_cores`、WiFi 初始化及 proc 诊断入口。真正的 RAM 复制、启动和 mailbox 通知函数由外部符号导入。这个小模块不足以还原完整原厂 HWNAT 主机驱动，且不能直接加载到 6.18。

### 1456 的 PPE mailbox

NPU mailbox 寄存器在 `0x1ec0c000` 区域。Linux 使用功能 slot 5，发送 28 字节 `ppe_mbox_data`：`func_type=1` 表示 SET，`func_id` 选择下面的命令。

| func_id | 固件回调地址 | 已核对的职责 |
| ---: | --- | --- |
| 1 | `0x8400f132` | 读取初始化字段，调用 HWNAT 初始化 |
| 2 | `0x8400f122` | HWNAT 反初始化 |
| 3 | `0x8400f19c` | 二级 API 分发，配合主机的 SRAM FOE 提交 |
| 4 | `0x8400ef86` | 设置计数缓冲区，返回 NPU 计数地址 |

分发函数在 `0x8400f280`；回调表起点为 `0x3e9001e4`，按 `func_id * 4` 取指针。启动函数 `0x8400bfea` 把该分发器写入 core0 的 slot 5 字段 `0x3e900d78`。

当前主机的普通 PPE 提交直接操作 `REG_PPE_RAM_CTRL` 和 `REG_PPE_RAM_ENTRY`，DRAM 条目由 DMA 内存承载。NPU 同时提供 slot 5/API 3 的 SRAM 提交接口。这两种接口需要分别对照；不能据此推断每一笔普通 FOE 更新都经过 mailbox。

统计回调把主机高位缓冲区地址转换为 NPU 别名，写回固定地址 `0x1e85fff0`，返回成功。计数生产函数 `0x8400af6e` 由 core5/core6 的 wrapper 调用：根据 FOE 索引更新低 32 位 bytes/packets，进位累加到主机缓冲区。字节增量使用 `(length - 0x20) & 0xffff`，与线速字节数的对应关系仍需实测。

**上传的 1456 样本包含统计命令。** 931 补丁的作用是兼容统计初始化错误或其他固件返回空地址；目前没有证据把正在使用的 1456 判断成“不支持统计”。

主机为计数而把部分路由 FOE 指向 PSE6/NBQ5 或 NBQ6，原始出口保存在 meter 的 `AIROHA_FOE_TUNNEL_MTU` 字段中。因此日志中的 PSE6 可以表示统计路径。933 补丁解出 `egress_pse_port` 和 `egress_nbq`，用于判断最终出口。

### 5.4 与原厂 6.6 固件的差异

| 样本 | 已识别的 mailbox 初始化 | core0 中观察到的功能注册 |
| --- | --- | --- |
| 5.4 | `0x84006604`；表起点 `0x3e900aa8` | slot 0；另有 core7 slot 1 写入 |
| 6.6 | `0x84002c66`；表起点 `0x3e900bd0` | slot 0、slot 1 |
| 1456 | `0x8400bfea`；表起点 `0x3e900d34` | slot 0、slot 4、slot 5；另有 core7 slot 1 写入 |

5.4/6.6 的已识别启动函数没有注册 PPE slot 5，当前反编译函数清单中也未找到对应字段赋值。这个结论限定于现有样本和覆盖范围，不能证明所有间接路径均不存在 HWNAT。

当前 6.18 驱动明确调用 slot 5。继续借鉴旧固件的调度和初始化逻辑需要完整原厂 HWNAT 主机实现；直接替换两个文件尚无 ABI 兼容依据。候选构建沿用已核对的 1456 二进制，不引入 ClankerNPU。

## 报文怎样进入硬件转发

```mermaid
flowchart LR
    IN["PON 或 LAN 收包"] --> LEARN["PPE 学习未绑定 FOE"]
    LEARN --> CPU["Linux 首包：PPPoE、conntrack、MWAN 路由"]
    CPU --> TC["nf_flowtable 或 bridger 提交 TC flower"]
    TC --> BUILD["Airoha 构造 NAT、VLAN、SID、GDM/NBQ、GEM/T-CONT"]
    BUILD --> BIND["硬件学习键匹配并提交 BND"]
    BIND --> FAST["后续报文由 PPE 转发；部分路径经 NPU 计数"]
    FAST --> OUT["正确的物理出口"]
```

已有内核的 PON FOE 构造会查询 GEM/T-CONT 映射，并在 O5 恢复或 bearer 改变时移除相关出口的旧条目。若各 PCP 对应不同 bearer，当前实现返回 `EOPNOTSUPP`，继续按包进行软件分类。候选改动保留这个条件。

PPPoE 数据连接在 FOE 中保留会话和封装信息。Discovery、LCP、ARP、广播、连接建立、CPU 本机业务及暂不支持的匹配仍需要软件处理。`bridger` 使用硬件 TC flower 请求处理桥接单播，没有据此证明 IPTV 组播卸载。

## 本次代码改动

两个项目使用相同的 931–934 队列：

| 补丁 | 内容 | 依据与限制 |
| --- | --- | --- |
| 931 | 统计初始化失败时保留 PPE；检查返回地址 | Actions 分支已有上游补丁，本次同步到 CI |
| 932 | 物理 GDM2 存在时使用实际出口 | 适配上游 `8e0a754b0836d996802713bbebc87bc1cc17925c`；保留端口 NBQ |
| 933 | 初始化错误、TC 成功/失败次数、每个 netdev 的 GDM/NBQ/QDMA；解码实际出口、SID、channel/qid | TC 成功只表示请求接受；统计地址范围外、native L2B 等显示 unavailable |
| 934 | 桥接模板键增加准确入接口、802.1Q VID/TPID；保留单 VLAN 并处理 pop/push | 修复 MAC 对相同而接口/VLAN 不同的模板冲突；DSA 输入按 metadata 找实际 user port；QinQ、PCP/DEI 匹配、输出叠标签暂不接受 |

934 修改软件模板查找，不改芯片已经学习的原生 L2B 键。标签输出与普通 IPv4/IPv6/ARP 桥接仍须实机核对，不能把编译通过当作线速转发证明。

构建集成增加 `bridger`、`tc-full` 和诊断命令，CI 另补齐 `ethtool-full`、NPU 固件和 flowtable 包。安装脚本先检查完整补丁队列和编号冲突，再写入目标树；仅接受 AN7581/6.18。

发布前检查最终 manifest、准备后的实际内核 `.config` 和驱动标记，同时校验安装 rootfs 中两个 NPU 文件的 SHA-256。依赖缺失、旧内核缓存、固件变更会阻止上传为成功固件，要求重新核对。

## 两套现有云端镜像核对

| 项目 | 已下载核对的 tag | 内核 | 原镜像状态 |
| --- | --- | --- | --- |
| Actions-OpenWrt-AN758X | `ponwrt-an7581-gemtek_xg2010g-mwan3-nft-master` | 6.18.52 | NPU 两个文件与上传的 1456 完全一致，manifest 无 bridger |
| OpenWRT-CI | `AIROHA-VIKINGYFY-owrt-26.10.10-09.48.04` | 6.18.54 | NPU 两个文件与上传的 1456 完全一致，manifest 无 bridger |

原镜像 SHA-256 分别为 `92e7adf99710cce891f4bafce14b08f707773c693009a3048eb94e7e65e84f71`、`dae758cbaaa1b308ce859e31a16ed8d6ae03a4751c0744b43f62e8a2fa6be697`。这些原镜像不包含本次候选补丁。

## 编译与部署边界

- PonWrt 源码提交：`a57faf93c6c3638ba3651690228aabaa51d3f235`，内核 6.18.52。
- VIKINGYFY/immortalwrt：`a38520034ee4bdd25dd6e88c4c59261f289ee17e`，内核 6.18.54。
- 分别应用对应 generic/Airoha 补丁栈，再应用本次队列，`patch --fuzz=0` 成功；允许行号偏移。
- AArch64 GCC 14.4.0，`CONFIG_NET_AIROHA=m`、`CONFIG_NET_AIROHA_NPU=m`、`CONFIG_NET_AIROHA_FLOW_STATS=y`、`CONFIG_DEBUG_FS=y`、`CONFIG_WERROR=y`，驱动对象以 `W=1` 编译。日志保存于 analysis/npu。
- 编译范围为 Airoha Ethernet/PPE/NPU 对象，未编译完整新固件镜像，也没有进行设备刷写、流量或故障切换操作。

## 实机如何核对 PON＋LAN3 双 PPPoE

新镜像包含只读命令：

```sh
xg2010g-ppe-report 3 2 > /tmp/ppe-report.txt
```

在对应连接有持续流量时采集。命令不挂载 debugfs，不修改网络、路由、firewall 或 conntrack。debugfs 未挂载/权限不足时会明确报告缺少证据。报告包含接口与策略路由、绑定表、可用的计数、端口 MIB、TC 状态和 NPU 文件哈希。

| 场景 | 需要观察的结果 |
| --- | --- |
| LAN→PON PPPoE | BND、`pppoe=1`、该线路 SID；实际 PSE2；GEM/T-CONT 与服务映射一致 |
| LAN→LAN3 PPPoE | BND、`pppoe=1`、另一线路 SID；实际 PSE7/NBQ1 |
| 两条 WAN 的回程 | 对应原连接的反方向 BND，实际出口指向客户端 LAN；NAT 与会话信息对应 |
| LAN1↔LAN2 等桥接单播 | bridger 请求进入硬件，实际流为 BND；端口 MIB 增长，VLAN 输出正确；native L2B 单流计数为 unavailable |
| 两路同时使用 | 两组连接保留各自 SID 和出口；不能依据 MWAN 权重百分比推断实时硬件吞吐 |
| PPPoE 重拨、WAN 切换 | 新连接使用新 SID/正确出口，旧会话和旧 PON bearer 条目失效；这一步尚未验证 |

硬件计数路径中的 PSE6 应与 `egress_*` 组合解释。PON 的 `etype` 在当前驱动中携带 GEM Port-ID；`channel` 携带 T-CONT/LLID。`pppoe_sid=-1` 表示该条目的 SID 布局未知。零计数、CPU 降低或 TC 成功都不足以单独证明卸载。

下一阶段还需要核对：双 WAN 出现重叠地址/相同五元组时的入接口与会话区分、PPPoE 重拨后的旧 FOE 清理、MTU/分片、桥接标签及策略变更后的连接行为。现有路由模板比较主要使用 IP 五元组，这些情况仍需要驱动和硬件学习键的进一步对照。
