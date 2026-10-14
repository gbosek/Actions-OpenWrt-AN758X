# XG2010G 1400MHz 动态调频兼容补丁

这是根据用户提供的说明和已核对的 PLL 寄存器代码重新实现的补丁，不是原私有构建的源码。适配这次选定的 PonWrt Linux 6.18.52 和 ImmortalWrt Linux 6.18.54 基线。

## 调频方式

- 普通 500–1200MHz、状态 0–14 使用原有 BL31 SMC 接口。
- 1400MHz 是 turbo OPP、状态 15。先经 BL31 到 1200MHz，再通过内核兼容路径将整数 PCW 从 24 改为 28、POSDIV 设为 0；退出时先回到 1200MHz，再调用普通 SMC。
- 仅在 XG2010G 且设备树显式启用时操作 PLL。检查寄存器地址、编码、时钟源并回读；失败尝试回滚、记录错误并关闭 boost。若回滚也失败，拒绝不安全的普通 SMC 降频。失败处理不能保证硬件一定恢复。
- 两次短 stop_machine 操作之间，在可睡眠上下文等待约一秒稳定，其他 CPU 在此期间运行于 PLL2；没有在 stop_machine 中睡眠。转换期间 clk_get 报告上一次完成的 OPP，`boost_transitioning` 为 1，不把它当作即时测得的频率。
- 默认 ondemand，最小 500MHz、最高 1400MHz；并非固定 1400MHz。能力不可用或故障时，服务将配置和策略上限改为 1200MHz。属性 `boost_capable`、`boost_backend`、`boost_transitioning` 可在 CPU 平台设备目录读取。
- 不改 BL31/U-Boot，不调整电压，不调用未公开的 BL31 boost 查询 ABI。本实现只有 `kernel-pll` 和 `unavailable` 后端，原文档的原生 BL31 boost 查询尚未实现。

## 安装

仓库脚本 `scripts/apply-compatible-boost.py`（OpenWRT-CI 为 `Scripts/`）需要完整的 OpenWrt 源码目录。它把 kernel-patches 中的 999 补丁装入 AN7581 的 patches-6.18，应用 source-patches 中的板级 DTS 补丁，并安装 CPU/runtime 的 cpufreq 服务。脚本拒绝混用旧 936/937 直接 PLL 补丁。

naoki 和 luanmuc NPU 插件各编一份。选包脚本与 CPU 适配器把 CPU 控制交给同一服务，移除了 luanmuc 的直接 PLL 写寄存器路径；包版本增加 `.1` 以区分这些本地修改。两套插件均保留各自的 NPU 页面。

## 验证与限制

执行 `python3 CPU/tests/run.py`，测试直接从交付的补丁提取 helper，覆盖正常/重复进入退出、不可用后端、SMC/寄存器写入/回滚/暂停失败以及策略持久化。模拟验证不能证明实机频率、电气或温度稳定性，也不能保证挂死时能回滚。

构建后必须通过 check-compatible-boost.py：检查配置、实际编译的 CPU 驱动对象、FIT 中四核共享 OPP/状态映射、实际 rootfs 服务及补丁校验值；PPE 和插件检查另行执行。未经这些检查不发布固件。

此补丁尚未经过 XG2010G 实机验证。首次刷入后先确认 backend、dmesg、温度和实际调频，进行稳定性测试；如出现异常，将最高频率设为 1200MHz 或回退原固件。

内核/运行时新增代码使用 GPL-2.0。补丁 SHA-256 与来源信息见 CPU-BOOST-SOURCE.json。
