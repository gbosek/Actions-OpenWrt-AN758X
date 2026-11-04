# 原始 PonWrt 最小增量重编译

用户已确认基线为当前 10 月 18 日固件对应的原始 PonWrt，而非 NAOKI66 整套固件。

## 已核实的来源

- 原始源码：<https://github.com/pbs05/ponwrt/tree/a57faf93c6c3638ba3651690228aabaa51d3f235>。
- 原始源码自身内核为 **6.18.52**；用户已明确选择保留升级到 **6.18.55** 所必需的补丁上下文适配，除此以外不继承旧本地功能补丁。
- 旧交付物：Actions-OpenWrt-AN758X a6440d4412a7de08d003afbba1501f0a2e28e980，镜像 SHA256 `3f4641d2770e6f9dc69e72438c79dcfa1485525ae77b082ad47e01bb9066e1c0`。仅用于辨认旧固件，不将其补丁集合复制到新构建。

## 新构建范围

1. NAOKI66 `luci-app-airoha` 固定提交 `0b1d8a0a250cb2e4a218b1fad5df2b923a0b0e00`。
2. NAOKI66 `OpenWrt_ONU_CONFIG` 的 PON 状态卡片固定提交 `3cb13560459f1d51136dac662baa1f399028b2b4`。不因此整套替换原始 PON 内核驱动。
3. MWAN4 后端 r30 与 LuCI r18 固定到 `components.json` 中核实的上游提交；仅对状态 RPC 添加 `nobatch: true` 以兼容固定的 LuCI，不复制旧后端适配、guard 或路由预设。
4. RTL8261BE 仅评估适用的上游 `76da1ee259c5804e105c3f044fcf94833608b227`：型号匹配、禁用多速率 EEE、软复位后等待 150ms。当前上游固件包仍是 `0cd4abe2` r4。未合并的 PR25926 不自动加入。
5. 用户本次明确要求的 PPE 原始字段显示：不隐藏全零 MAC；保留真实零计数；确实缺失的数据不伪造为零。

## 不继承

不复制旧 kernel-patches、Offload、Maintenance55、Runtime、Boot 或旧 diy-part1/2 整套内容；仅提取明确获准的 6.18.52 到 6.18.55 内核适配和本次 RTL826x 补丁。不加入旧 PPE/桥接回退/NPU 内存/统计改造/CPU 超频/DNS 实验补丁，不加入 DNS 日志定时脚本。保留所选原始仓库自身的原生补丁，不将上游原生补丁误删。

## 当前设备更新状态

NAOKI66 Airoha r903 主视图已与上述上游逐字节核实一致。r904 仅修改 PPE 全零 MAC 隐藏及缺失计数的 N/A 文本，已打包；安装尝试遇到软件源错误，尚未验证安装成功。

随后 192.168.10.1 的 HTTP 标题变为 `TL-7DR7299`。用户已要求不要再改实机，本构建不访问设备，不自动安装或刷机。

驱动更新未安装，未热卸载，未刷机、重启或重拨。
