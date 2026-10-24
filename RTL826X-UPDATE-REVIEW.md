# XG2010G NPU LuCI 与万兆 PHY 更新复核（2026-10-24）

本轮基于原 PonWrt a57faf93c6c3638ba3651690228aabaa51d3f235 / Linux 6.18.55，不替换整套板级或 PCS 驱动。

## 纳入内容

- naoki66/luci-app-airoha master 已核对至 78059e072919c830aaff0575d6f010bab4f23d35；合并至 gbosek/luci-app-airoha e839a0a26bbc43d62356b6c8a7da05cc1df933f7。保留上游祖先关系，固件使用独立修订 r905。
- 纳入 GDM 丢包计数、PSE 每端口队列、CDM TX 区间占比、驱动定义对应的 LAN/WAN 标签、EIP93 计数摘要和显式全零 L2 诊断。
- 保留完整 PPE 导出、分页、64 位计数字符串、旧驱动缺字段处理、IRQ 只累加 CPU 列、算法引用不冒充活动会话。CDM 区间占比不是 NPU 利用率；PPE bank 统计不冒充 CDM 流量归属。
- 回移 OpenWrt 76da1ee259c5804e105c3f044fcf94833608b227 的 RTL826x 功能修改，补丁 939：BE/N 要求 PKG_MODEL 0x8261、多速率 EEE 禁用、MMD30 内部复位释放后等待 150ms。保留已有 SerDes 有界恢复、in-band、PMA 低功耗策略及原 PHY 固件。
- 修复上一次 a465ede7 / 40049908690 的实际失败：宿主机实际函数测试在 -Werror 下发现 packed ethhdr 到对齐 vlan_ethhdr 的强制转换。生产代码改为 memcpy 解析 inline VLAN TCI，保留编译告警；新增奇数地址 VLAN100 允许和 VLAN200 拒绝两个用例。

## 冲突、重复与保留范围

独立重放固定 Linux、PonWrt 和现有补丁；新 939、949–952 要求 fuzz=0，产出精确源哈希。安装器检测同编号异内容补丁和等效 RTL826x 重复补丁，重复安装幂等。LuCI 的两处合并冲突已解决并用实际 RPC/JS 函数复核。

原 Boot/DTS、网口映射、GPIO reset/polarity、DHCP/netifd、PON R68、CPU 500–1400MHz、MWAN4 默认关闭、原 930–938 补丁不变。949/950/951 不变，952 仅在本次增加对齐安全解析，其既有 ACL/FDB/VLAN/解绑限制保留。不调整 BND 门槛、老化或统计以制造更多绑定。

未整套导入 PCS v18：其接口和现有 SCU/PCIe/PON 适配不同，直接替换有回退风险。未加入其他 C/D/CE PHY 硅片专用支持，未替换 BE 使用的 rtl8261n.bin。两份 PHY 固件的精确哈希继续纳入成品验收。

## 已完成验证

- 8 个 PPE/网络核心相关 AArch64 对象已重编译；30 个基础断言、16 个保留回归、18 个 eligibility 场景、14 个撤销断言和 15 个 RX gate 断言通过。
- 4 个 Realtek PHY AArch64 对象已编译；实际源码函数的 8 个复位/错误/重试场景和 13 个型号匹配场景通过。
- 14 组既有 CPU、网络默认值、PON、RPS、运行时、路由、完整导出、feeds 和包兼容性回归通过。
- 实际 CDM JS 的首样本、区间、重置、空闲、独立端口处理通过；实际 GDM/CDM RPC 寄存器偏移及读失败输出检查通过。
- LuCI 兼容性、翻译 po2lmo、JS、shell、Python、工作流 YAML 和 git whitespace 检查通过。
- Git 的实际 LF checkout 字节已重新核对；952 精确哈希为 c7b6c2e4ed483cae058b15787270665f476e2f479a384369dcb52610085ec1b7，不能使用 Windows CRLF 文件哈希作为 CI 门禁。

## 成品验收要求与限制

CI 增加准备阶段精确 PHY 源核对和构建后对象/实际 rootfs realtek.ko 哈希记录；交付验收需核对真实 FIT/SquashFS、Image 角色、实际 PHY 模块、NPU1456、CPU OPP 和原运行时配置。

以上是离线源码与对象验证，不等于整机编译完成或实机无 bug。原固件没有观察到 10G DHCP 故障；另一 naoki66 固件已经含有 150ms 等修改，因此这些改动不能据此证明解决了它的未知失联根因。BND 是否增加和长期稳定性均未做实机验证。本轮未修改路由器，未刷机、重启、重拨或恢复任何监控；自动消息和关机仍取消。

## 来源

- https://github.com/naoki66/luci-app-airoha/commit/78059e072919c830aaff0575d6f010bab4f23d35
- https://github.com/gbosek/luci-app-airoha/commit/e839a0a26bbc43d62356b6c8a7da05cc1df933f7
- https://github.com/openwrt/openwrt/commit/76da1ee259c5804e105c3f044fcf94833608b227
