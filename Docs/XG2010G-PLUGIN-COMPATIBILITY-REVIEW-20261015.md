# XG2010G 插件与代码兼容性审查，2026-10-15

比较范围：Actions-OpenWrt-AN758X 当前 XG2010G 构建分支的近期 MWAN4/UI/RPS/超频和驱动修复，以及 OpenWRT-CI 相对于 4be6dc4 成功超频基线的新增集成。两个项目保留各自源码和网络方案。

## 已复现并修复

1. **P1：naoki ONU PPPoE 卸载配套补丁遗漏。** 固定 ONU 源码 35e2d67 的 internet-apply 把物理上联通过 WAN zone 的 `list device` 锚定；两个项目原 firewall4 仅从 `zone.network` 推导 flowtable。PPPoE 的 l3_device 无法递归到 pon0，因而启用 ONU 的 PPPoE 上网页时，即使驱动已带 PPE 回退补丁，PON 设备仍可能不在 flowtable 中。现在仅 naoki ONU 变体安装其仓库配套的 010 firewall4 补丁；luanmuc 保留原防火墙。原补丁第一段与原有 FullCone helper 的上下文不匹配，已调整到共同模块入口，新增功能代码不变。来源、原/本地补丁 SHA 和本地包 release 写入 PON-SOURCE.json。保留原 FullCone 和桥接 flowtable 补丁；固件检查要求实际 rootfs 存在两处卸载调用和新 firewall4 release。

2. **P2：共享 CPU 调频脚本遗漏原 cpufreq LuCI 的 ondemand 参数。** 新脚本此前应用 governor/min/max，却未应用页面保存的 sdfactor0 和 upthreshold0，造成页面保存成功但内核参数不变。现在在 ondemand 下恢复 sampling_down_factor/up_threshold，兼容全局和 per-policy sysfs 路径并校验原页面支持的取值。cpufreq 本地 release 升至 5，发布前按实际 rootfs 字节核对公共脚本。两个 NPU 界面仍使用同一个调频控制入口，保持 500–1400MHz 动态范围。

## 已检查且未发现直接冲突

- naoki/luanmuc 两个同包名 NPU 插件互斥；保留原来源快照，仅由适配脚本把 CPU 写操作统一到内核 cpufreq，去除用户态直接写 CPU PLL 的路径。
- MWAN4 后端与对应 LuCI 配对；配置和清单排除 MWAN3，CI 禁用 pbr。原生启动 IP rules 和 LuCI 停止确认逻辑一致；RPS 平台 hook 调用原 packet_steering 入口，非四核模式和关闭开关回到原实现；守护进程使用单实例锁。
- PPE 931 与新增 QDMA/NPU watchdog/RX31 修复的驱动文件功能已检查、ARM64 对象已编译。6.18.54 保留原生 RX31 修复，不重复应用。Actions 保留 932/933 候选，CI 保留原有 931 方案。
- PON 满宽卡片使用独立模块与类，移除旧模块；CPU 使用率继续用原生 helper，温度脚本覆盖路径已核对。概览独立加载，PON 读取保留接口 pon0；ONU 配置页替代原 PON/IPTV 页，PON 状态卡保留。
- Aurora/Argon 分开安装；WOL、磁盘管理、分区扩容、ttyd、定时重启没有共用上述网络控制脚本。LAN 默认 192.168.10.1，保留配置升级不强改已有地址、拨号密码或策略。

## 验证和边界

实际 firewall4 b6e51575 源码分别叠加两个项目全部原补丁，再以 fuzz=0 应用本次配套补丁。使用准备后真实 ucode 函数执行每项目 8 项场景：VLAN/桥接上联、双 WAN 去重、忽略反向/通配设备、软件模式、硬件拒绝回退、关闭卸载和原 network 行为；全部通过。换回旧函数时同一测试能够复现 PON 缺失。CPU 回归同样先确认旧 helper 无法应用保存参数，再验证新脚本；另覆盖 governor 切换、无效阈值、全局/per-policy 参数、超频故障回退和包安装路径。原 NPU 互斥、RPS、PON 安装/概览、三项驱动和默认网络回归均通过，工作流语法无误。

这是源码、构建叠加和离线行为审查。当前已启用组合未发现其它直接冲突，不代表全部可选插件、所有旧配置或实机双 WAN/PPE/超频稳定性已验收。尤其第三方手工策略路由、代理 mark 规则及额外 PLL/RPS 脚本未在当前选包中启用，不能据此承诺其共存行为。
