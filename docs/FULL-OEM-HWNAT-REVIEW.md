# 原厂完整备份恢复与主机绑定审查

日期：2026-10-14。分析对象为用户上传的 XG2010G 5.4 原厂备份和 5585F CT 6.6 备份；后者属于参考设备，不能直接替换 XG2010G 驱动、设备树或光模块校准。

## 恢复与样本

9 个 RAR5 分卷齐全，官方 unrar 恢复两套内部归档均返回 All OK。恢复的 ZIP 为 89902740 字节，RAR 为 70818074 字节；每卷及原始归档摘要见 volume-manifest.json。ZIP 的 11 个分区已提取。5.4 备份已提取 tclinux 主备镜像、日志及所需文件，未提取 327155712 字节的 system.bin；这不妨碍已完成的内核和根文件系统分析。

| 样本 | 内核 | HWNAT模块字节数 | 已确认情况 |
|---|---|---:|---|
| XG2010G 原厂 | 5.4.55 | 819392 | 主备 FIT 内的内核、DT 和根文件系统载荷相同 |
| 5585F CT A | 6.6.23 | 943344 | 已提取并列出符号，尚未进行本轮函数反编译 |
| 5585F CT B | 6.6.23 | 951496 | 与 A 的内核、HWNAT 不同，NPU 模块及固件相同 |

两套备份中的 NPU RV32/data 分别逐字节匹配此前上传的 naoki66_5.4 和原厂6.6样本。因此已有固件分析可复用，新增价值是完整的 hw_nat、QDMA、PON 主机代码及其调用环境。完整文件摘要见 full-oem-selected-artifacts.json。

XG2010G 根文件系统实际包含 etc/lddla/A60993.elf.pm 和 .dm；此前 Markdown 报告关于缺少 MD32 PM/DM 的说法不适用于这份备份。校准、密码及设备配置未放入交付目录。

## REA 已确认的绑定控制链

对原生 ARM64 ELF hw_nat.ko 使用实际 REA/Ghidra。5.4 与 CT B 各审查六个函数：PpeSetBindThreshold、PpeSetEntryBind、ppe_check_start_to_bind、PpeTxHandler、PpeFillInL2Info、GetPppoeSid。会话均已关闭。函数地址、证据 ID 和反编译见 function-index.json、对应 .c 及 rea-native-evidence.zip。反编译不是原始源码，未知类型、全局重叠和间接 hook 仍存在。

1. PpeTxHandler 从报文 FOE 元数据取得硬件条目，经过起始 hook 与绑定资格判断，再解析 L2/L3/L4，填写 MAC/VLAN/PPPoE，选择出口及扩展接口，最后写 BND 和硬件条目。解析、字段或出口失败会中止绑定。CT B 还存在 hwnat_enable_status、SRv6/SOE 等条件。
2. ppe_check_start_to_bind 的普通路径接受 reason 0x0f，或 ppeCheckFastRuleBind 返回成功；开启 prebind 时，0x0f 只标记预绑定，reason 0x1a 才进入后续资格路径。这是原厂逻辑，尚未证明当前 OpenWrt 配置启用了同样模式。AGE_PREBIND 位只是老化控制，不能据此认定模式开启。
3. PpeSetEntryBind 更新时间戳并编码 BND 状态 0x20000000，调用 ecnt_ppe_set_entry_bind_hook 后写字段。CT B 有额外条件检查及提前返回。该函数本身不证明硬件已经确认提交。
4. GetPppoeSid 检查 PPPoE version/type 字节 0x11 并读取 SID。双 PPPoE 必须保持会话与实际出口对应；这个函数不负责拨号或 MWAN4 策略。5.4 与 6.6 的 skb 偏移不同，模块不能直接用于 6.18。
5. PpeSetBindThreshold 更新两路 PPE（第二路受硬件型号条件控制）的 L4 与 L2 门槛。SDK 的 30 pps 默认值属于源码配置证据，不能替代当前设备寄存器或运行配置读取。反编译的 vendor 寄存器访问器参数不能当作可直接写入的 ARM 地址。
6. 原厂代码中 dualEntry 分支不能仅凭名字解释为双 WAN 支持；仍需追踪关联字段及生命周期。未绕过路由、防火墙或报文检查来强制绑定。

## 对当前低绑定现象的含义

A/B 使用相同 NPU 固件却使用不同 HWNAT，说明不能只比较固件版本来判断完善程度。当前应保留 1456 作为现有集成基线，借助原厂主机代码完善和核验出口、SID、建表及老化处理；本轮没有得出哪个版本实机性能最好。

截图中的 BND/总表项不是报文命中率；CDM2 的 95.8% 是累计计数口径，也不是两条 WAN 的实时命中率。没有当前设备按 SID/实际出口采样的报告，因此不能把任何静态差异直接定为低绑定根因。

当前 6.18 源码已发现的独立审查点仍需修复评审：flow_entry_update 回写完整 ib1 可能把软件 BND 模板污染为硬件 UNB 状态；部分 SRAM 提交返回值被忽略；flush_sram 的内部 err 遮蔽外层错误；同五元组多模板选择未充分区分 ingress/VLAN/SID。以上未在本轮修改驱动，也未确认在设备上触发。

## 范围与后续

完整备份提供了可继续追踪 PpeSetForcePortInfo、PpeSetExtIfNum、GEM 与 QDMA 的原生样本。本轮完成归档恢复、样本提取及 12 个关键函数审查，未声称完整逆向所有模块。npu_wifi.ko 未纳入提取和适配。Airoha_Doc.7z 仍未取得可读取分卷。本轮未执行目标代码、运行测试、完整固件构建或刷机。
