# 新增原厂资料：对XG2010G有线PPE/NPU的价值

日期：2026-10-13。设备无WiFi，PON＋LAN3 EN8811H双PPPoE。这里是已读取资料的源码审计，不是新REA二进制结果，也没有执行SDK程序、写寄存器或修改校准区。

## 接收范围

| 资料 | 实际读取情况 | 对当前目标的价值 |
| --- | --- | --- |
| airoha_sdk.rar | 已下载16754574字节、完整解出2391个普通文件，共85536181字节 | 高：HWNAT、ARM64 NPU主机、QDMA、PON及EN7572代码 |
| XG2010G-原厂固件逆向报告-NPU与PON校准.md | 已全文读取28876字节 | 作为文件和符号索引；有地址、加载主体与核数等错误须纠正 |
| Airoha_Doc.7z | 下载工具拒绝：超过32MiB，字节未进入工作区 | 尚不能评估其具体内容 |
| 6.6内核的5585F CT.zip | 同上，未列目录、未解包 | 尚不能当作已经核对的原厂6.6实现 |
| XG2010G_origin_bak.rar | 同上，未列目录、未解包 | 用户确认是5.4原厂备份，但本次未读取其原始内容 |

上传成功不等于执行环境已经取得文件。当前下载接口只提供整文件读取，没有远端分卷或range读取。没有生成上述三个大文件的分卷。各输入及重点文件摘要见vendor-sdk-review-manifest.json，SDK原始源码保留在工作区，未随仓库提交。

## 最关键的补充：找到ARM64主机函数本体

源码位置为SDK的 `linux/arch/arm64/mach-econet/ecnt_npu.c`，不在private模块目录或普通linux/drivers目录。最初只检查这些目录时看到外部声明；全目录交叉引用进一步找到了以下实际定义：

| 函数 / 行号 | 已确认职责 |
| --- | --- |
| boot_npu_all_cores / 298 | 每核写启动地址，按NPU_CODE_IN_SRAM分支选择SRAM或reserved physical address，再写enable/trigger |
| copy_file_to_ram / 485 | code选择SRAM或reserved virtual mapping；data使用Regbase，读文件并在DRAM code路径执行cache维护 |
| set_npu_needed_info / 716 | 向MIB10/11/12/21提供测试区、L2 SRAM大小、FPGA和UART配置 |
| host_notify_npuMbox / 940 | 每core锁串行发送physical address/length/argument和触发序号，轮询done/ret_status，处理超时 |

这是此前仅有小npu.ko无法恢复的重要主机实现。SDK源码可以补控制链路解释，但尚未证明它与上传5.4/6.6/1456的特定构建逐字节对应；宏分支和实际DTS仍要对照。

SDK旧mailbox头的显式枚举为WiFi、tunnel、notify、DBA、TR471；实际host函数按MAX_MBOX_FUNC处理。不能由枚举没有命名HWNAT就断言硬件槽5不可编码，也不能直接宣称此SDK的运行固件已经注册了1456的PPE槽5。

## 对低绑定问题直接有用的材料

1. `private/hw_nat/Kconfig:19` 将binding threshold描述为packets/second，默认30；`hwnat_ioctl.c:2782` 实际写两PPE的L4/L2门槛。当前6.18也写0x1e，但设备时标、实际寄存器及已运行配置仍需读取核对。不能把降低门槛当成已证实的修复。
2. Kconfig:276/283和frame_engine.h:500说明UNB寿命及最低packet-count参数；hwnat_ioctl.c:2800附近还有按表占用量限制单位时间新建条目的接口。这能用于区分学习门槛、建表限制和无软件模板，而不是把所有UNB归咎于固件。
3. `ra_nat_entry.c:290、:1774、:2887` 有PPPoE解析、SID和VLAN封装的实际代码；`:6738` 有根据时间戳及出口信息转成BIND的逻辑；`:3100` 有GEM改变后删旧表项的控制。
4. `foe_fdb.h:48` 明确选择EN7581头；其定义GDM4=9、NPU=6、PPE1/2=4/8，与当前6.18的GDM4/PSE9一致，也提供NBQ、channel、SID等字段。
5. SDK含多个SoC、位域及table布局。`foe_fdb_7581_64Byte.h` 的文件名不能代替最终布局核对；源码还含128字节兼容常量，现代驱动使用80字节FOE。应逐字段比较偏移和宏条件，不整份替换当前结构。
6. 原厂HWNAT直接沿skb/hardware-index路径解析并绑定，与现代nf_flowtable/TC的软件模板路径不同。SDK可用于找现代驱动缺失的控制条件，不能据有旧API就保证所有方向/双WAN已成功。

当前6.18源码还存在独立的模板状态问题：统计读回时将整个硬件IB1覆盖软件绑定模板。若硬件已老化为UNB，软件模板可能随之被污染，之后提交也不是预期BND。此路径与ACK错误及会话生命周期应优先修复/诊断；目前不能说已由实机数据证实为本次低绑定根因。

## 上传报告需要纠正的结论

- 模块init中的filp_open/vfs_read是内核代码，不能同时描述成“不是内核加载，而是用户态写SRAM”。
- ARM64路径不按fileCopyToSram的legacy base_addr搬运：private/npu/host/npu_rv32.c:155委托三参数copy_file_to_ram，实际由ecnt_npu选择映射。data不是简单的code_base+0x10000。
- 报告给出的第二reg资源 `0x1e900000 + 0x313000` 结束于 `0x1ec13000`，已经覆盖 `0x1ec0c000` mailbox/bridge区域；据此断言DT漏了该窗口是算术错误。SDKprobe:1393–1402和NPU_MBOX_BASE偏移也支持该映射。
- 5.4原始code头16字节实际为8条RISC-V c.nop，不是四个核的入口表；现有固件启动代码按8个hart分发，不能用出现的几个core字符串推断只有4核。
- 从日志中内核虚拟地址直接减固定常量推物理地址不可靠；memremap/ioremap和PHYS_OFFSET必须核对实际映射及DTS。
- 邮箱缓冲区0x120是288字节，不能同时称120字节/0x78；外层传输参数和内层payload也不能混成一个结构。
- 校准章节自带修正注记却保留“错位4字节”等旧结论。当前用户PON已有流量，这不能解释成已经证明的“光不通”根因；不按该报告把另一份conf写到本机factory。

## PON校准材料的适用范围

SDK的 `private/lddla/en7572_init.c:186、:477` 有PM/DM/BOB文件读取及CopyTxDDMI：特定4字节校准项为擦除值时，从+256的对应A2位置复制。它不证明整个A0区错位、不证明另一台设备的512字节conf适合本机。不同宏分支的文件路径也不同。

校准源码用于解释已有读取/回退机制及核对本机数据；本轮有线绑定工作不改校准、激光或factory分区。

## 已运行镜像的核对

用户截图对应OpenWRT-CI release `AIROHA-VIKINGYFY-MOSSDEF-MWAN4-owrt-26.10.12-21.18.28`。精确镜像已下载并读rootfs：内核6.18.54，源码a385200，两个NPU文件仍与上传1456配对完全一致；LuCI为2.0.0-r9，manifest未列bridger/tc-full。

`6/74`是表项比例，CDM2的95.8%来自累计低32位计数，二者不是同一种命中率。页面还混用了不同读取的BND/UNB/总数；不能仅凭截图判定1456转发命中低或确定是哪条WAN。两个WAN均有流量已由用户确认，仍需要分SID/实际出口的运行态证据。

## 后续使用顺序

先对照SDK中的学习/建表、门槛与老化、字段布局、SID/GEM生命周期，修当前主机的确定错误及统计口径；再对原厂5.4/6.6二进制做源码对应核验。三个大附件还受传输接口限制，获取之前不填写其分析结论或宣称已经分卷。
