# XG2010G 不超频构建

两个项目各编 naoki 和 luanmuc NPU LuCI 一份，保留 MWAN4、PPE v2、原生四核使用率、CPU/PON/LAN1/LAN2 温度、RPS 修复和原有其他软件包。

使用未修改的上游 BL31 CPU 驱动与 500–1200MHz OPP 表，默认 ondemand，最低500MHz、最高1200MHz。不应用兼容超频内核补丁或 DTS 补丁；luanmuc 直接 PLL 写入已移除，超频行也移除。

stock-after-boost 工作流在四个超频分支最新构建全部成功之后才运行两个 NPU 变体。等待任务不提前编译固件；失败时保持阻塞，等待修复后的分支构建。等待最长约340分钟，超时不会启动不超频构建。
