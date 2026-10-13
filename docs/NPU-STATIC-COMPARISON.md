# XG2010G 有线 NPU/PPE：样本比较和控制链路

日期：2026-10-13。设备为 AN7581 XG2010G，无 WiFi。目标为 PON＋LAN3 EN8811H 两路 PPPoE，以及 WAN→LAN、LAN→WAN、LAN→LAN 有线硬件卸载。`npu_wifi.ko` 不用于适配，也不参与选择固件的依据。

## 选择结论

**当前 Linux6.18 项目继续使用上传的1456 code/data配对文件。参考原厂6.6和5.4完善主机PPE/PON控制，不直接替换成旧固件或Clanker。**

这是已确认接口和数据通路的比较，不是同条件吞吐、功耗或稳定性的实测排名。

| 样本 | 有线控制与数据通路证据 | 对当前项目的判断 |
| --- | --- | --- |
| official1456 | core0注册PPE slot5；有init/deinit、SRAM API和统计初始化；core5/core6实际计数、恢复出口并继续转发 | 与当前6.18主机ABI和统计通路对应最完整，作为当前基线 |
| 用户标注原厂6.6 | 已注册slot0/slot1，未发现对应PPE slot5；channel7有实际隧道处理循环，8项隧道表中7项有动作、1项为空操作 | 隧道逻辑优于所提供5.4样本，可参考；直接替换缺当前ABI兼容依据 |
| naoki66 5.4 | 已注册core0 slot0/core7 slot1；7项隧道回调均只返回1，未发现相同PPE slot5统计通路 | 保留启动、调度和寄存器参考，不能当成当前1456的等价替换 |
| ClankerNPU AN7581 NOWIFI源码 | 存在slot5控制和SRAM API；统计API清零并发布窗口，没有实时producer；hart5/6返回后idle | 缺当前主机PSE6/NBQ5/6统计转发通路，不作当前固件替代 |

Clanker精确提交为 `7ad3c2fbcb95bf0f5c882e046b7a0a9cc16bb892`，只审计 `SOC=AN7581 WIFI=NOWIFI` 源码。没有与用户历史运行版本对应的二进制，不能把源码结论当成对那份历史二进制的鉴定。默认AN7583构建也不代表XG2010G。

## 查到的1456有线控制接口

代码基址 `0x84000000`、配套数据 `0x3e900000`、GP `0x3e9013a0`。启动入口 `0x8400bfea` 向core0 callback slot5写入dispatcher `0x8400f280`。slot号、其内部func_id、二级SRAM API ID是三个不同字段。

| slot5 func_id | 回调地址 | 行为 |
| ---: | --- | --- |
| 1 | `0x8400f132` | 消费28字节初始化消息，调用 `0x84001362` 配置硬件 |
| 2 | `0x8400f122` | 调用 `0x8400212a` 停止相关硬件路径 |
| 3 | `0x8400f19c` | 分发4个SRAM API：写80字节表窗口、索引命令、清表 |
| 4 | `0x8400ef86` | 设置主机高位计数缓冲区别名，返回低位统计地址 `0x1e85fff0` |

初始化消息在+8..12含CDS、xPON HAL、WAN XSI、Joyme和max-packet标志，+16/+20/+24为PPE type、WAN mode和WAN selector。全局WAN selector不是MWAN的线路数量或连接策略；不能用它代替每流出接口与PPPoE SID。

SRAM二级表位于 `0x3e9001d4`：API0/1写两个80字节PPE窗口（物理地址 `0x1fb51f20` / `0x1fb50f20`）；API2发索引命令，API3循环失效表项。这证明固件存在此控制接口。**当前6.18正常FOE commit/flush使用主机FE MMIO，而不是每次都发送该mailbox命令。**

core5 wrapper `0x84006cb2`、core6 wrapper `0x84006cd8` 都调用 `0x8400af6e`：从相应bridge队列取包，按FOE索引增加bytes/packets，向主机高位缓冲区进位，恢复meter中保存的PSE/NBQ/QoS后继续egress。其字节增量为 `(length-0x20)&0xffff`；与线上字节数的对应关系仍需要实机测量。

当前主机只对符合条件的路由条目走这个统计通路，临时出口为PSE6/NBQ5或6。原生AN7581 L2B不走它；统计范围之外不能假设有有效单流计数。PSE6本身不是最终物理WAN/LAN出口。

## 两条PPPoE线路如何进入PPE

```mermaid
flowchart LR
    I["PON/LAN收包、硬件学习未绑定条目"] --> H["Linux首包：PPPoE、连接跟踪、路由/MWAN选线"]
    H --> F["flowtable或bridger提交TC请求"]
    F --> E["主机编码FOE：NAT、SID、VLAN、物理出口、PON bearer"]
    E --> B["匹配学习键，提交BND"]
    B --> P["后续包PPE转发；符合条件的路由流经NPU计数"]
    P --> O["恢复并到达实际物理出口"]
```

| 物理接口 | 编码需要保留的身份 |
| --- | --- |
| PON | GDM2/PSE2、线路自己的SID和对端MAC、服务VLAN、GEM及T-CONT/LLID |
| LAN3 EN8811H 2.5G | GDM4/NBQ1、PSE9/NBQ1、另一线路的SID和对端MAC及服务VLAN |
| LAN1 | GDM4/NBQ0、PSE9/NBQ0 |
| LAN2 | GDM3/NBQ5、PSE3/NBQ5 |

本次纠正此前报告中的PSE7：两套准备后的6.18源码 `airoha_eth.h` 枚举中 `FE_PSE_PORT_GDM4=9`，`FE_PSE_PORT_CDM4=7`；`airoha_ppe.c` 对port4使用GDM4枚举。已有驱动按枚举写入，错误在文档及只读诊断提示的数字。

固件不负责MWAN连接策略和PPPoE拨号；主机根据已建立连接构造表项。PON bearer变化、旧会话失效、路由变更和重叠五元组的隔离也必须结合主机及硬件学习键处理。只把“PPPoE”或“支持双WAN”写进固件配置无法解决这些问题。

本次主机复核进一步确认：路由模板compare没有按SID/入口区分，多个相同五元组模板可能覆盖同一个学习槽；部分commit调用忽略硬件ACK失败，软件完成状态不能代表BND。PPPoE重拨后旧SID的清理也尚无闭环证据。这些是后续有线控制的明确重点，详见下面的主机审计；934的桥接修复不能当作路由双WAN歧义修复。

已有候选931–934补丁改善统计初始化回退、真实出口、桥接入接口/VLAN区分和诊断。两套内核驱动对象编译通过的记录见主报告；本次追加静态比较没有新增驱动改动，也没有完成全镜像或实机验收。

## 完成范围与证据

- 三组原始RV32 code/data：启动分工、已识别mailbox注册、静态命令表、相关隧道/PPE回调和实际转发循环已补查，导出当前全部候选函数与指令清单。
- 有线相关的32条静态表记录已列出，包括空项和重复指针；不是32个独立函数，也不代表全部动态回调。
- 原厂 `npu.ko` 的8个非导入函数覆盖自身1600字节代码，补齐proc匿名回调和被误分割的入口。实际RAM复制、启动、mailbox及原厂完整HWNAT实现依赖未提供的外部代码。
- REA处理原始ARM64模块；RV32 raw由独立Ghidra12.1.4处理，标记 `direct-ghidra`。当前REA raw profile没有RV32支持，不伪造ELF或Evidence ID。
- 5.4/1456的FC2厂商指令使用单独的 `NPU_OPAQUE_FC2` 分析profile，保留为副作用未知的userop；未改原字节或当作NOP。它有助于恢复控制流，不能充当已验证的缓存模型。
- 自动候选中仍有字符串、浮点/表数据及不可靠边界；保留错误和实际ranges，候选数不等于原厂函数数或逆向完成率。

审计材料：

- [5.4 / 6.6 补充审计](../analysis/npu/comparison-20261013/old-firmware-audit.md)
- [原厂 npu.ko 代码范围与外部依赖](../analysis/npu/comparison-20261013/npu-core-module-audit.md)
- [Clanker NOWIFI 源码审计](../analysis/npu/comparison-20261013/clanker-source-audit.md)
- [6.18主机控制与双WAN剩余问题](../analysis/npu/comparison-20261013/wired-control-audit.md)
- [复现方法与完整导出摘要](../analysis/npu/comparison-20261013/README.md)
- [完整静态分析资料包（约2MB）](../analysis/npu/comparison-20261013/full-static-exports.zip)
- [原始REA证据和驱动编译记录](../analysis/npu/README.md)
- [PPE改动和双WAN实机判据](REA-NPU-PPE-XG2010G.md)

**目前不能称“完整原厂系统已逆向完成”或“所有流量已经硬件卸载”。** 缺少原厂主机HWNAT/PON外部实现与实机数据。PPPoE控制报文、连接首包、广播、CPU本机流量及硬件不支持的匹配仍需Linux；目标是符合条件的数据连接正确绑定，并在双向流量、SID/实际出口、计数和重拨/切线结果上得到证实。
