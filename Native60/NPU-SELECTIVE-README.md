# XG2010G 6.18.60：仅选择性移植 NAOKI NPU/PPE

基线：本仓库完整成功构建提交 `910fa39f41fe4bbafb756b18fa99613dfb447d8c`，原厂 CPU 频率、pbs05 R68、原板级/PHY/SerDes、MWAN4 r30 与中文 LuCI r19、完整插件集。不是 naoki 整机固件重编，不使用另一个 ImmortalWrt fork 基线。

上游来源：`naoki66/ImmortalWrt-for-Gemtek-brightspeed` 的固定公开提交 `9a70b25731dc64822dcb24cf9a7dbe7a84ed1ba1`。对应输入和本地补丁完整哈希记录于 `npu-selective-source.json`。公开源码尚未准确对应作者 5e152df9 成品；不能以文件名冒充源码复现。

## 本轮新增

1. **962 VLAN/PPPoE 编码**：提取 9995 的 VPM/TPID 修正与双标签 PPPoE 动作接收。VPM 表示外层标签类型，不是标签数量；保留本基线路径的 outer-last 顺序，拒绝硬件不能重现的内层 S-tag/未知 TPID。保持原有 PON PCP/GEM 准入。通用 flowtable 两层封装限制没有改变，不宣称普通 QinQ+PPPoE 全部打通。
2. **963 PPPoE 真实出口**：提取 9996 的 PPP 逻辑出口补全思路，重新适配成本基线的三参数 `dev_fill_forward_path()`。仅沿该 PPPoE 会话解析下层，核对 SID、对端 MAC、VLAN 顺序/协议/VID，并按正常 GDM/PON 验证路径提交。绝不扫描所有 PON 再选择第一个映射；断开的会话、桥接或不明确路径保留软件转发。
3. **964 统计队列保护**：提取 9999-14 的局部映射判空；在 stats 未映射时避免 CDM3 统计队列重定向，并保护 reset/read。保留已有 `flow_stats_cap` 失败保护。这是额外防御，不说明基线完全没有保护。

## 明确不带入

不引入 naoki 的无父流桥接回退、PON P-bit 放宽、绑定阈值/老化扫描/限额寄存器变化、其他微码、bridger、板级/PHY/SerDes 更换、新 ONU 后端、PON 故障恢复、无线、风扇、OTA、其他用户空间/feeds。原生 L2B、PON 元数据等已存在对应实现的部分不重复追加。

新旧准备源码比较了 Airoha 驱动、Realtek PHY、Airoha 公共头、netfilter、bridge 共 336 个 C/H 文件，唯一变化为 `drivers/net/ethernet/airoha/airoha_ppe.c`。设备树/分区/上游 feeds/软件包输入没有更新。固件版本标识改为 `2026.11.16-native60-npu-mwan4`，用于区分成品。

## 检查与局限

- 官方干净 6.18.60 归档：原 630 + 新 3 = **633 份补丁**正向零 fuzz 重放通过；原 630 份哈希和顺序完全保留。
- PPE ARM64 对象 `KCFLAGS=-Werror` 编译通过；来源与干净重放的文件哈希相同。
- **32 项**实际辅助函数测试通过，覆盖 VLAN TPID、同一会话、PON/外部以太网出口、SID/对端/VLAN 不匹配、断连/不支持路径、设备引用和 RCU 出入。路径发现由 host fixture 模拟，并非真实网络/竞态测试。
- 既有 PPE 实际函数 **16 项**、TRTCM **7 项**继续通过。完整包闭包、原厂 CPU 和个人路由无内置预设检查通过。
- CI保留精确源码/补丁/包输入门禁，重跑新函数测试，再检查实际编译对象与 FIT/SquashFS 成品。每次只构建 MWAN4 版本。

以上不是整机编译成功或实机验收。本轮未连接现机。没有证据证明修复了此前 naoki 的万兆失联，也不能保证新固件绝无网口问题；需在完整成品通过后实机验证真实双 WAN、转发计数、CPU、双万兆稳定性。不会通过 UI、假计数或阈值调整增加 BND。
