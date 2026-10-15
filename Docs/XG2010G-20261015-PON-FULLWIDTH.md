# XG2010G PON 卡片第二轮修复

范围：Actions-OpenWrt-AN758X 的 work/xg2010g-1456-ppe-20261014 分支，naoki/luanmuc 两份 1456 PPE 超频固件。

用户确认 Aurora 主题、顶部已经显示 PON，仍看到小卡片。下载并核对两份发布镜像的 SHA-256，提取 rootfs 后确认原 15_pon.js 与仓库一致。原主题默认样式下的离线页面未完整复现用户设备状态，因此不能把旧缓存或某条 CSS 直接断言为现场唯一根因。Aurora 的窄屏通用规则会对匹配的行内 grid 强制两列，原卡片也复用了主题通用头部、正文类；本次移除这些依赖。

改动：

- PON 专用 section/article 和样式，外层容器及卡片明确占满可用宽度；使用 flex 纵向排列，避开 Aurora 的通用 grid/ifacebox 规则。
- 正常字号和标签/读数分栏；桌面将读数、速率分区，手机自动换行。保留所有光学读数、实际速率、TCP/UDP 和硬件卸载计数。
- 名称仍为 PON，实际接口仍为 pon0，不改光模块参数、拨号或数据采样。
- 模块改名为 15_xg2010g_pon.js，删除旧 15_pon.js；luci-app-pon-status 升至 r7，浏览器资源缓存版本纳入新文件散列。
- 写入 /etc/pon-status-layout.json 并发布 PON-STATUS-LAYOUT.json，便于核对实际布局版本和文件 SHA。
- 概览仅对声明 fullwidth 的卡片明确设置外层宽度，保留独立加载及收起/展开。

验证：使用发布固件内的 Aurora/Argon CSS、实际概览和 PON 渲染代码，在 Chromium 检查 1440/390 像素、行内样式空格变化、刷新、收起/展开及深色模式。原代码在 Aurora 390px、紧凑行内样式时宽度比可用区域少173px，回归检查能够捕获；新代码八项均通过。数据为浏览器测试快照，宽度相对整个概览 section 的内部宽度校验，不再只相对孤立的内层容器。CI 在编译后使用实际 staged rootfs 再跑这些浏览器检查，失败则不发布，并上传截图。

保留全部原方案：1456-62 NPU 配对固件、PPE 931/932/933、MWAN4 与 LuCI、原生四核 CPU 使用率、四项温度、WOL、Argon 壁纸配置、默认 LAN 192.168.10.1、500–1400MHz 动态超频。本次不修改内核、NPU 固件、CPU 驱动及网络默认策略。
