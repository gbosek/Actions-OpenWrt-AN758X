# NPU LuCI 最新更新与重新编译（2026-10-24，r907）

- 本轮核实 naoki66/luci-app-airoha 默认分支已为 main，最新提交 `d496614002cf21f83e96e4741716eab1e5333ede`；保留祖先关系合并到 gbosek/luci-app-airoha master `f8c1bc6872b36bc5445fd0946103d65b1f736d7b`。
- 本地独立修订 r907。纳入 955c732 的 PSE 共享缓冲硬件峰值、胶囊占用条，以及 d496614 的 PPE 表头右侧统计胶囊、不换行布局。前一轮 r906 的 CPU/频率悬停、NPU 状态信息和 Zero-L2 提示保留。
- 修正上游失败路径：峰值寄存器读取失败输出 null，不冒充实测为 0。运行实际 RPC 函数的峰值非零、实测为零、读取失败三种夹具均通过；未访问硬件寄存器。
- 保留本地 IRQ 只累加 CPU 列、算法引用口径、CDM 区间占比、完整 PPE 分页导出、64 位计数和 XG2010G/活动 WAN 控制保护。CDM 占比和 PPE BND 均不当成 NPU 利用率。
- 18 个 vendored 文件逐一等于上述 fork Git blob（仅翻译文件按既有规则改名）。shared ui.js 加入实际成品字节验收，使用构建相同的 jsmin 比对。
- LuCI 兼容、实际遥测函数、JS/shell 语法、po2lmo 翻译、固件 NPU 适配、运行时、完整导出、网络默认值回归及精确补丁哈希检查通过。
- 原 939 PHY 加固、949–952 guarded PPE 路径和门禁保留；Boot/DTS/GPIO/网口映射、DHCP/netifd、PON R68、CPU 500–1400MHz、MWAN4 默认关闭不变。YYH2913 候选未加入。
- 这是本地源码验证；整机编译、实际 FIT/rootfs 验收和实机验证分别记录。没有证据证明本轮显示更新能解决另一固件失联或提高实际 BND。
- 上一轮 40068096959 被本轮精确 UI 版本替代，不将替代记成编译失败。准确新提交/运行以外部 build-state.json 为准。
- 未访问或修改路由器。自动跟进、自动消息和关机保持取消。

来源：
- https://github.com/naoki66/luci-app-airoha/commit/d496614002cf21f83e96e4741716eab1e5333ede
- https://github.com/gbosek/luci-app-airoha/commit/f8c1bc6872b36bc5445fd0946103d65b1f736d7b

本地证据在 output/naoki-offload-integration-20261024/luci-main-update-20261024/：luci-validation.json、firmware-ui-validation.json、source-inventory.json、integrity.json。交付时必须继续运行 verify-delivered-images.py，不能以预检或已启动代替成功成品。
