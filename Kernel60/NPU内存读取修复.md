# NPU 内存显示为空的修复

当前 723fd37 固件的 NPU 已加载 1456-62，运行于 800MHz；“内存 —”不能据此判定 NPU 未启用。

实机证据：NPU 节点 memory-region phandle=0x33，对应 reserved-memory/npu-binary@84000000，reg 为地址 0x84000000、长度 0x00a00000，即 10485760 字节（10MiB）。现 RPC memory_regions=[]，旧 /tmp/npu-mem-regions.json 为 []，dmesg 中已没有匹配的启动预留记录。旧实现只读启动日志并永久缓存空结果，导致管理页显示空。

本地 r914 增加只读 ucode helper，从正在运行的 DT 按 NPU memory-region/phandle 关联读取 reg、address-cells、size-cells，计算真实地址和长度。不硬编码 10MiB，不把 QDMA/ATF 预留计入 NPU，也不是 NPU 动态占用率。换用 v2 缓存摆脱旧空数组；失败/空发现不永久缓存，仍保留日志兼容路径。

验证包括二进制 DT 用例（1/2 cells、>4GiB、错误 phandle、零/损坏属性、多元组）、真实 RPC 缓存代码、无启动日志、旧空缓存恢复和失败后重试；实际 package install recipe 核对 helper 的安装和执行权限。还通过 SSH 将同一 helper 从 stdin 送入实机 ucode 只读执行，返回 npu-binary / 10240 KiB；没有安装或替换在线设备文件。

实机原始证据与只读运行结果在上一层输出目录 live-npu-cpu-readonly.json、npu-memory-live-reader-verification.json。实际新固件的安装和页面展示仍须成品构建/实机验收。本修复不改变 PPE 绑定、NPU 微码、频率或内存分配。
