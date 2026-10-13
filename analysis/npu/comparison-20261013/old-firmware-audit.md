# Naoki66 5.4 与用户标注原厂 6.6 样本：补充静态审计

日期：2026-10-13。使用原始配对文件；输入字节未修改。本报告属于独立 Ghidra 分析，非 REA Evidence envelope。

## 原先遗漏与本次补齐

原始自动清单把四个已注册 mailbox 回调识别为 LAB 标签，没有建立函数。本次按初始化赋值、原始 `.data` 指针和指令补齐：

| 样本 | WiFi dispatcher | tunnel dispatcher | 初始化函数 / 表 |
| --- | --- | --- | --- |
| 5.4 | `0x8400619e` | `0x84006188` | `0x84006604` / `0x3e900aa8` |
| 6.6 | `0x84002804` | `0x840027ee` | `0x84002c66` / `0x3e900bd0` |

各 hart 的 callback row 为 80 字节，callback slots 从 row+0x30 开始。5.4 core0 注册 slot0，core7 注册 slot1；6.6 core0 注册 slot0/slot1。其已识别启动路径没有注册当前 6.18 所需 PPE slot5。这个结论只覆盖现有样本；外部主机可以独立操作 PPE。

## 静态命令表

WiFi 首 u32 的低 nibble 为 interface index，高 nibble 为 operation：1 SET_WAIT、2 SET_NOWAIT、3 GET_WAIT、4 GET_NOWAIT。API ID 位于 +4。具体外层主机传输由原厂 `host_notify_npuMbox` 实现，不能仅根据该 payload 还原整个主机协议。

| 样本 | SET_WAIT 范围 / 指针表 | GET_WAIT 范围 / 指针表 | tunnel 指针表 |
| --- | --- | --- | --- |
| 5.4 | 0..27 / `0x3e900024` | 0..7 / `0x3e900000` | `0x3e900098`，7 项 |
| 6.6 | 0..30 / `0x3e900108` | 0..9 / `0x3e9000dc` | `0x3e900080`，8 项 |

静态表项已全部解析到被分析的入口，详见 mailbox-api-ledger.json。NOWAIT 的动态 callback 存于 BSS，具体注册和运行参数仍需要结合调用与主机代码，静态表项清点不代表全部动态语义已验证。

5.4 tunnel 表 7 项分别指向 `0x840088e6`、`0x840088f2`、`0x840088f6`、`0x840088fa`、`0x840088fe`、`0x840088ea`、`0x840088ee`，恢复代码均只返回1。

6.6 tunnel 表：

| ID | 函数地址 | 已恢复行为 |
| ---: | --- | --- |
| 0 | `0x84003fae` | 按 idx 存储50字节 header |
| 1 | `0x84003faa` | 返回1，无其他动作 |
| 2 | `0x84003fdc` | 设置 VXLAN MTU |
| 3 | `0x84004000` | 存储 SRv6 header 和长度，检查 idx<8 |
| 4 | `0x84004074` | 设置16字节本机 IPv6 地址 |
| 5 | `0x840040f0` | 设置 fragment MTU 表项 |
| 6 | `0x84004144` | 调用 bridge debug |
| 7 | `0x84004120` | 设置 map_info_base |

因此可确认这两个具体样本的隧道控制实现存在差异。不能把接口返回1直接解释成动作已经执行。

## 八个 hart 的启动入口

`0x84000104` 在两个样本中根据 hart ID 分发：

| hart | 5.4 入口 | 6.6 入口 |
| ---: | --- | --- |
| 0 | `0x84000202` | `0x8400015a` |
| 1 | `0x84000256` | `0x84000186` |
| 2 | `0x84000266` | `0x84000196` |
| 3 | `0x84000286` | `0x840001b6` |
| 4 | `0x84000296` | `0x840001c6` |
| 5 | `0x840002ba` | `0x840001ea` |
| 6 | `0x840002de` | `0x8400020e` |
| 7 | `0x84000302` | `0x84000232` |

5.4 hart4/5/6 跟到 WiFi TX-done、indirect command ring part2/part1 循环；这些 wrapper 有共享尾部，字符串名称不能代替实际分支分析。hart7 wrapper `0x840042e0` 只打印 finish 后返回。不能把它们说成与1456相同的 PPE 计数核心，也不能把所有核心概括为 idle。

6.6 hart4/5/6 wrapper 在 `0x8400989c/0x840098b0/0x840098c4` 打印 do nothing 后返回。hart7 的 `0x84000232` 实际进入 channel7 bridge dequeue→tunnel处理循环，dequeue入口为 `0x84000396`、handler为 `0x84000896`。正常egress由handler调用 `0x8400047a/0x84000536/0x840005fc`，最终写入 `0x840003f0` 的bridge MMIO。handler返回-1时才调用 `0x84000648`，发送 `0xc2000000` drop/释放命令；不能用这个异常路径证明正常转发。因此这个6.6样本包含实际隧道数据面。

## PPE / 统计边界

当前已识别回调和 MMIO 引用中，没有发现与1456相同的 slot5 HWNAT 初始化/API4/per-FOE carry producer。不能把 WiFi debug counters 当成该 PPE 统计通道，也不能据此断言原厂系统没有硬件 NAT；原厂配置同时启用了 RA_HWNAT、HWNAT_V3、WAN_ACCOUNT 等构建选项，主机侧实现未包含在这两个 raw 文件中。

## 覆盖与保留问题

- 保存了完整当前候选函数、函数实际地址范围和已解码指令清单，以及本次重点回调的汇编/伪代码。
- 5.4 的 FC2 厂商指令用独立 `NPU_OPAQUE_FC2` profile 保留为 opaque userop，未把它改成 NOP，未修改源字节；其硬件副作用尚未实测。
- 部分失败候选落在字符串或浮点常量上，例如5.4的 `0x8401543c`、6.6的 `0x840179fc`。不能把自动候选数当成原厂函数数，也不能把反编译率作为完成率。
- 仍缺少原厂主机 HWNAT/PPE 编码、PON bearer 接口实现、运行时队列参数及同条件流量数据。
- 对当前6.18直接替换没有兼容依据；XG2010G无WiFi，适配只参考有线隧道、初始化和调度逻辑，不使用npu_wifi.ko。
