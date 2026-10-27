# XG2010G PHY 预识别复位

本改动仅给 XG2010G MDIO 地址 5、8 的两个 RTL8261BE PHY 增加
`reset-before-id-read;`，启用基线内核已经支持的识别前硬复位流程。
原 GPIO29/GPIO27、低电平有效、200ms assert/deassert、极性和其他板级配置保留。
不替换 PHY 驱动或微码，不改变 CRC 统计，不在运行时主动重置网口。

## 来源与适用范围

对照的实际参考镜像是
`immortalwrt-naoki66-xg2010g-20261027-55dd90d1-airoha-an7581-gemtek_xg2010g-ubi-squashfs-sysupgrade.itb`，
大小 88,110,140 字节，SHA256：
`1661b12447c22547c0db7acdc81dbb6411888038dd38a7b3705288113ca4c70c`。
该镜像的两个 PHY 节点均有此属性。我们已交付的 98470a7 镜像节点没有，
但它的实际内核 Image 已包含相同的预复位支持。

核心实现来自固定基线
[pbs05/ponwrt a57faf9 的 705 补丁](https://github.com/pbs05/ponwrt/blob/a57faf93c6c3638ba3651690228aabaa51d3f235/target/linux/generic/hack-6.18/705-net-phy-reset-PHY-before-reading-its-ID-when-requested.patch)，
SHA256 为 `14261ac1ebeda140e87dbb036c7f2ffccc7c36fdc846b6b16bb6f564d19cef6f`。
安装器核对该文件并拒绝重复实现；不会再次应用这份基线补丁。
核心在读取 PHY ID 之前执行复位，并通过 `reset_state = 0` 避免注册阶段重复复位。

这是启动识别时序的可靠性改进，**尚未证实为 CRC 的根因修复**。
两份实际 Image 都读取相同 CRC 寄存器、累计后导出到 `rx_crc_errors`。
RTL8261BE 所用的 `rtl826x_config_init` 反编译结果相同，
`rtl8261n.bin` / `rtl8264b.bin` 也逐字节一致。
所以不能凭另一版累计 CRC 为 0，推断它修复了 CRC，或推断本版没有 CRC 统计。
本开关只针对 PHY5/8，不声称修复 LAN3 的历史 CRC。

## 验证与限制

- `tests/phy-preid-test.py` 检查只改两个开关、重复执行幂等，
  GPIO/时长冲突、重复核心补丁及未知核心版本均拒绝且不写入部分修改。
- 本地已使用真实板级 DTS 和内核 include 编译 DTB，核对两个节点的开关、GPIO 和时长。
- CI 必须核对准备后的 MDIO 调用顺序、AArch64 对象、实际 FIT 中的 DTB/内核支持及根文件系统元数据，
  导出 `PHY-PRE-ID-RESET-VERIFICATION.json`；整机编译或成品检查失败不得算交付成功。
- 离线验证不等于设备验证。刷入后仍需在相同线缆、对端和业务条件下比较 CRC 增量、
  链路事件及 DHCP，不能把累计值清零或不同观察时长当作修复效果。

审阅原始证据保存在本地 `output/crc-reference-review-20261028/`，
包含实际镜像身份、REA 反编译/汇编、CRC 寄存器表和实际 DTB 对照。
