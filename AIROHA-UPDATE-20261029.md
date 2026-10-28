# Airoha 更新同步与编译

本次以 MWAN4 三项修复提交 61add44 为基线；后端 r29、LuCI r16 保留，首次刷机仍默认停止，不加入 ISP/设备/测速分流预设。

上游固定 d3669ce，已快进同步 gbosek/luci-app-airoha 的实际默认分支 master；审查后的 XG2010G 分支 work/xg2010g-reviewed-20261029 固定 69a1b62。固件使用这个已审查内容的快照，并继续应用共享 CPU 策略和完整 PPE 导出适配。

纳入 NPU 10 秒轮询、成功结果缓存、后台 tmpfs CPU/频率历史和孤儿临时文件清理；纳入 clients 快照/环/历史容量上限、1 秒端口采集、5 秒每设备采样、ACL 与 nlbwmon 回退。nlbwmon 作为实际依赖加入，不强改它的用户配置。

已处理合并差异：上游三参数 index 在当前真实 ucode 中忽略起点，保留单调推进和两个元组上限并优化为后缀定位；保留 DNS seek/read、64 KiB 批量、已读 RAM 日志轮转；新增两路逻辑 WAN 汇总与 IPv6 别名去重，防止漏算第二条 WAN 或重复计算 PPPoE 物理父口。识别结果缓存 30 秒，故显示拓扑改变有延迟。

保持紧凑图表。LAN 统计是不同层次计数器的残差估计，不能当精确二层流量，也不能用它、BND 或 HW_OFFLOAD 条数推断完整硬件卸载率。nlbwmon/conntrack 归属仍有覆盖限制。不自动安装额外 bridge nft 统计链。上游新增 PON 桥卸载开关支持保留，但默认仍关闭，手工启用后的可用性和稳定性没有在本设备验证。

未改内核驱动、PPE 绑定门限、NPU 固件、RCU/PHY/PON 修复；未对在线设备安装、刷机、重启、重拨、清连接或压测。未恢复自动发送、监控或关机。

本地通过真实 ucode 双 WAN/IPv6 别名/断开/回退/AP/计数重置、前端一致性、CPU 历史缩放/采样、缓存命中/失败/过期/时钟回拨测试。32 MiB 限制的 17 类解析、10000 次解析及 DNS 读/轮转回归通过。两个主题 390/1440/3840 像素布局和 hover 测试通过。原 58 组后端、6 类完整迁移链和完整预检通过。最终成品仍须成功编译并核查，不能把本地测试当成整机或实机验收。

精确源码及哈希见 actions/AIROHA-UPDATE-REVIEW.json；运行状态见 build-state.json。证据见 integration-validation.json、clients-memory-regression.json 和 browser-results。
