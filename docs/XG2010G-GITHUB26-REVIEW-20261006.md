# XG2010G GitHub #26 固件审查
日期：2026-10-06。Gemtek XG2010G / AN7581 / NOWIFI。

## 构建结果与下载

[GitHub #26](https://github.com/gbosek/Actions-OpenWrt-AN758X/actions/runs/37403794369) 已完成，conclusion=success，2026-10-06 11:25（北京时间）上传固件。
固件源码提交：`12f877f2140658f26f3292066cd9d4652f107a74`，分支 `multiwan-ppe-experimental`。

artifact：`OpenWrt_firmware_ponwrt-an7581-gemtek_xg2010g_202610061125`，ID 11388207204；下载时未过期。
ZIP SHA256：`649c55ee975a20e2c11c2595842cd3517fb13ca080e7da2d587673ea923fe077`，与 GitHub artifact digest 完全一致。

[下载好的 GitHub 固件](C:/Users/40777/Downloads/XG2010G-GitHub26-1400-20261006-1125/ponwrt-airoha-an7581-gemtek_xg2010g-squashfs-sysupgrade.itb)

ITB 大小：19,087,618 字节。
ITB SHA256：`ea72ce15dc5cb0dd57a92769f9a14d69a073dd24787d6e0d691431a200608720`。

本地 1022 版本与云端构建环境、配置/打包结果不同，ITB 哈希不同；均各自检查，不把本地验证结果冒充云端结果。

## 实际镜像检查通过

- ZIP CRC、GitHub ZIP 哈希、包内校验和、FIT 内核/DTB/rootfs 哈希及 Gemtek XG2010G 板型。
- 实际 DTB 四核 OPP：最低 500 MHz，最高 1400 MHz。LuCI 同为最高 1400 MHz，无 1600 档。
- powersave 启动保护；默认 ondemand、上限 1400，先写限制再切 governor。
- 1456.62 NPU 两个文件与已核验基线逐字节一致，未替换 NPU 驱动。
- 58 个必要包全部安装；304 个已安装包的依赖名称/提供者均可解析。该检查不等于完整 APK 版本求解器或运行测试。
- 119 个模块均为 AArch64 ELF，vermagic 一致：`6.18.52 SMP mod_unload aarch64`；TC/eBPF、PON、PHY、WireGuard 模块齐全。
- WOL、中文包及 etherwake；没有 Watchcat、SQM 服务、Turbo ACC。
- 系统菜单、PON 光模块卡片、浮点 CPU 使用率、Statistics 每核统计、vnStat2、MTR、WireGuard 工具均在镜像内。
- WAN1 helper、热插拔与启动脚本字节/执行权限及 S19 链接检查；保留动态角色、锁、失败冷却、VLAN/桥接边界和共享接口恢复处理。
- 保留 938 GDM2 出口修复及 939 WAN1 MTU 独立字段修复；代码路径与回归检查通过。
- 本轮 11 份专项回归检查、15 个补丁格式检查、工作流 YAML 与 shell 步骤语法检查通过。没有发现新的固件运行代码缺陷；审查不保证不存在其他 bug。

## 本轮新发现并修复：构建依赖冲突

#26 构建日志存在 Kconfig recursive dependency 错误，涉及 67 个不同包名，来自未使用的图形/音视频菜单。Kconfig 报错后 `make defconfig` 仍返回成功，因此单看 GitHub success 无法发现这一问题。

逐一对照实际安装清单：这些包均未安装进 #26 固件，没有证据表明该冲突破坏了本次 WAN/PON/插件安装。

用固定版本 feeds 在独立目录复现：
- 全部 feed 元数据：68 条循环错误。
- 仅排除 video：仍有 MPD、Squeezelite 两条错误。
- 排除 video 的安装链接及 MPD/Squeezelite 两个音频服务源链接：零循环错误。
- 本地与 GitHub 的配置分别复验，选中的 349 个包集合均保持完全一致。

源码已增加仅针对 XG2010G 的 feed 链接范围处理及严格 defconfig 日志检查：
1. 只移除未使用媒体源的 package/feeds 链接和生成索引，保留 feed 源码。
2. 若配置选择被排除包、遇到异常链接或真实目录，立即拒绝修改。
3. 其他机型流程不变；重复运行安全。
4. Kconfig 即使返回 0，出现依赖循环/错误也阻止后续编译。
5. 临时目录实测、真实固定 feed 索引与 64 个媒体安装链接检查通过。

这项修正发生在 #26 完成后的源码审查中，只影响以后构建流程，不修改已下载的 ITB 或内核/NPU。没有重新触发全量固件构建。XG2010G 配置以后如需要桌面视频/MPD/Squeezelite 软件，需先解决这些 feed 的元数据兼容问题再启用。

## 尚需实机验收与限制

- 新镜像尚未做实机冷启动、长时间运行、WOL 唤醒及双 WAN 的 FOE BIND/HW_OFFLOAD/PPE/QDMA/物理出口计数验收。
- 单外部硬件 WAN1 slot；PON WAN0 + 一个符合条件的动态 LAN WAN1，不等于任意三/四 WAN 全部硬件卸载。
- LAN 与 WAN 共享同一物理桥接父口时 helper 会拒绝切角色；需符合驱动和端口拓扑条件。
- CPU 使用率可能真实低于显示精度；浮点计算已修复，不能用 CPU 低或下载快替代硬件卸载证据。
- 1456.62 NPU 的完整厂商协议、所有 PPE/PON 边界无法仅靠固件静态审查证明。
- 未自动刷机，未修改当前路由器配置，未安排关机。

证据目录：`C:/Users/40777/Desktop/XG2010G/output/whole-code-review-20261006`。
关键文件：`github-image/inspection.json`、`github-image/dependency-inspection.json`、`feed-kconfig-investigation.json`、`feed-kconfig-*.log`、`checks.log`。
