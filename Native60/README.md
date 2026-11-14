# XG2010G 原厂频率 Linux 6.18.60 双版本（2026-11-14）

用户授权在 gbosek/Actions-OpenWrt-AN758X 编译两份相同基础的固件，分别带 MWAN4 和 mossdef-org PBR 1.2.4。准确状态在工作目录上一级 build-state.json；CI 为 native60-dual.yml。只构建 XG2010G，不操作在线设备。

## 基线与边界

继承最新完整构建 4ba2d790ffb7d8b9faacb97b9fec93e659dfa267，Actions 42635081048 已在线核实 success。其功能基线为原完整 a6440d4，保留原磁盘/文件系统工具、IPTV/omcproxy、WOL、Aurora、PON、NPU1456、PPE/QDMA/PHY/LED、中文界面等；不使用旧精简 040208a 镜像作功能基线。不重新引入后来已被完整基线替代的 949–954 BND 实验分支。

Linux 使用官方 6.18.60，SHA256 为 3c2f44ef6acc021a7ad444d9a2e6ec1ef488ff09368793d0004a6080f69d621e。完全移除自定义 CPU 超频注入；设备树只保留 500–1200MHz 原厂 OPP，首启设置最高 1200MHz，不改 ATF/U-Boot。

## 更新选择

- 加入 EN7581 温度 IRQ 在 thermal zone 注册之后申请的修复 402-08，避免重新绑定时 IRQ 使用尚未注册的 zone；不能据此断言先前重启就是该错误。
- 保留并迁移已审查的 955–958、960、961：桥 FDB 移动撤销、VLAN 匹配及 VID、flowtable 优先级、PON PPPoE 额外8字节 MTU、ETS 统计回绕/通道基线、完整转发路径失败传播。
- 保留完整基线的 939/959 双万兆 RTL826x 型号识别、150ms 复位等待、匹配前释放复位，以及既有 SerDes/板级配置。
- 纳入旧 6.18.60 已验证的 DNSmasq 安全/ubus、odhcp6c 重连、PPP 参数引用、FullCone 范围/flags、musl regex 修复。
- naoki66/luci-app-airoha 的 main 最新确认为 9263b4a64c5a76e51e9cafc88b5df432feec5ed4，完整基线已经同步；保留整套最新界面，补入原设备树 NPU 内存读取和空发现不永久缓存的修复。本地包 release901 用于区别上游 r9。
- 新 ADC 第二温区不是本次必需：当前板级单温区 DTS 没有使用 sensor1，不为显示第二个数值整体迁移多传感器架构。SMC eFuse 暂无当前 DTS 消费者；外置 SFP ONU、禁用的 PCIe PHY、WiFi/USB模组等不加入。保留与网口 PCS 实际相关的 PHY 依赖。
- 未整套替换 GDM/LRO、fw4/netifd/ucode、PON r69 或自动 PON watchdog；保持已验证的基线接口与 PON R68。
- MT7530/cgroup 回移文件的上游删除对应修复分别已经进入稳定内核 .57/.59，.60 原生保留，不重复加入。

## 两套策略路由与冲突处理

MWAN4 版固定已配套验证的后端 0.1.1-r30、LuCI/中文 r19。PBR 版固定 mossdef-org/pbr f6c88015144c429a43d14ce1b51fea3a40ed9cc5 与 luci-app-pbr e49120a76b18b405bea795cccb1082628183dc02，版本均为1.2.4-r2，三处兼容编号为38。PBR带已有简体中文译文；新版本新增词条可能回退英文。

每份镜像只选择自身后端和前端，明确排除另一套及旧 mwan3/vpn-policy-routing。PBR 默认 fw_mask=00ff0000 包含旧 cn_split 的0x400000位，存在真实规则覆盖风险；因此两版共同移除内置个人 cn_split、测速/旁路由预设及其专用热插拔/guard。保留普通 LAN/DHCP/防火墙及原板级设置。策略服务首次启动默认禁用，刷入后按实际双WAN设置。PBR主要负责策略分流，不承诺与MWAN4相同的线路检测/负载均衡能力。

PBR 文件清单与完整基线实际 rootfs 对照，没有其他插件文件覆盖；两个版本各自 make defconfig 后核对完整基线软件包闭包。所有关键软件包输入逐文件固定在 package-inputs.json，拒绝静默更新。内核与包未更改 BND 阈值、老化或计数。

## 编译前结果与成品门禁

- 630个完整内核补丁：官方干净归档、严格正向、fuzz=0；重复或已原生补丁不能自动反向通过。另在通用队列完成后执行ARM64 headers_install。
- 12个修改路径相关 ARM64 对象编译通过，含以太网/PPE/NPU/PHY/thermal/flowtable/bridge/LED。
- TRTCM实际函数7例、PPE实际函数16例、PHY复位8例/匹配15例/延迟探测2例通过；NPU二进制DT及缓存回归通过。
- 两套包闭包、PBR前后端RPC兼容、JS/脚本语法通过。PBR10个ucode模块由真实host编译器编译；MWAN4的16个模块因host缺uci/ubus扩展，导入替身只用于语法检查，不宣称运行时API已验证。
- 本地源码准备树缺host openssl/libdeflate工具，不能完成本地全包构建，不能将该尝试算通过；CI完整安装工具后编译所有包。
- CI编译前重做精确补丁重放和源/包哈希检查，编译后核查实际FIT各区哈希、6.18.60内核、真实SquashFS/APK数据库、版本/完整包集、DT原厂频率、实际PHY模块、PON及NPU身份，并分别产出两份成品及诊断记录。

这些检查不等于刷机验收，不证明没有bug、此前重启根因已修复、BND增加或万兆稳定性。没有进行刷机、重启、重拨、网络设置修改、压测、监控恢复或关机。
