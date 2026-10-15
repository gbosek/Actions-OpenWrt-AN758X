# AN7581 上游驱动修复，2026-10-15

适用范围：Gemtek XG2010G；两个项目各编译 naoki、luanmuc NPU LuCI 一份，沿用 MWAN4 与 500–1400MHz 动态超频方案。

| 修复 | Actions-OpenWrt-AN758X，6.18.52 | OpenWRT-CI，6.18.54 | 实际作用 |
| --- | --- | --- | --- |
| 934 QDMA TRTCM 配置重试 | 回移 | 回移 | 写配置后等待完成并回读；失败最多尝试两次，仍不一致则返回 -EBUSY，减少限速/队列设置偶发失败 |
| 935 NPU 看门狗清理顺序 | 回移 | 回移 | 将工作项纳入设备托管清理，先释放中断再取消工作，避免晚到中断重新排队和访问已释放资源 |
| 936 RX 队列31中断 | 回移 | 原生内核已包含，跳过重复补丁 | 将 RX_IRQ1_BANK_PIN_MASK 改为 0xffe00000，补齐队列31接收完成中断 |

精确上游提交、补丁 SHA-256 和两个项目的内核/源码基线见 AN7581-DRIVER-FIXES-SOURCE.json。安装脚本拒绝未经检查的内核基线和同编号冲突补丁。实际固件安装 /etc/an7581-driver-fixes.json，发布时提供同内容的来源附件。

验证使用两个项目的完整固定源码：先应用 OpenWrt 原有 generic/target 补丁，再叠加项目 PPE 补丁和本轮修复。实际 airoha_eth.o、airoha_npu.o、airoha_ppe.o 均通过 ARM64 交叉编译，启用 WERROR。提取准备后驱动中的实际 TRTCM 函数进行七组故障注入：首次成功、超时后恢复、读取失败后恢复、值不一致后恢复，以及连续超时/读取失败/值不一致返回 -EBUSY；全部通过。另核对 RX31 位掩码、看门狗托管顺序和 ARM64 ELF 对象。离线结果见 AN7581-DRIVER-FIXES-VALIDATION.json。

CI 在 target/linux/prepare 后检查实际源码，固件编译后再次检查实际 ARM64 驱动对象、软件包清单和 staged rootfs；验证报告随固件发布。检查失败则不发布固件。现有 PPE 回退、CPU 原生四核使用率、CPU/PON/LAN1/LAN2 温度、RPS 修复、MWAN4 停止反馈、PON fullwidth-v2、WOL、Argon 壁纸配置和默认 LAN 192.168.10.1 保留。OpenWRT-CI 同步此前已准备好的 PON/概览独立加载、MWAN4 和 RPS 修复，并在发布前用实际 rootfs 的 Aurora/Argon 样式进行浏览器检查。

保留各项目现有 PPE 叠加方案：Actions 使用 931/932/933 与 1456-62 配对固件，OpenWRT-CI 保留其原有 931 方案。三项上游修复不改变 NPU 固件、CPU 电压/启动固件、用户拨号密码或已有网络配置。以上为源码、对象和离线验证，双 WAN 硬件卸载、设备重启和超频稳定性仍需刷机后确认。
