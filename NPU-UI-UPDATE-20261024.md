# NPU LuCI 最新更新与重新编译（2026-10-24）

- 检查时 naoki66/luci-app-airoha master：`74c360563b3e2f8d4696e888f99a7d25a6ed414f`（2026-10-24 05:06:21 UTC）。
- 已保留提交祖先关系合并到 gbosek/luci-app-airoha：`9bb3808e33c686955ff8a502fe58aeb7054f54ef`，并推送 master。
- 固件独立修订 r906。新增 CPU/频率历史图悬停采样读数；NPU 卡片显示状态、固件、频率、核心、设备、预留内存；Zero-L2 占表达到50%时标红。
- 本次只更新上游的 JS 和两个翻译文件，RPC/解析器/包依赖不变。原完整导出、64位计数字符串、统计口径和板级控制保护保留。
- 原有 939 PHY 加固、949–952 guarded PPE 路径及其验证要求保留；设备树、GPIO、DHCP/PON/MWAN4 和 CPU 配置不变。YYH2913 候选尚未经过移植验证，本轮未加入。
- LuCI 兼容性、统计解析、JS、po2lmo 翻译检查通过；固件适配、完整导出、运行时及网络默认值回归通过。
- 上一轮 40062746762 在本轮开始时两个任务都已进入 Compile the firmware，无失败步骤。新一轮使用新提交，最终状态以 build-state.json 为准。
- 本地检查通过不代表固件已完整编译、成品已验收或已在实机运行。未访问或修改路由器；不恢复自动跟进或关机。

来源：https://github.com/naoki66/luci-app-airoha/commit/74c360563b3e2f8d4696e888f99a7d25a6ed414f

本地证据：luci-validation.json、firmware-ui-validation.json 及同目录 *.log。实际成品仍须用 verify-delivered-images.py 对准确新提交验收。
