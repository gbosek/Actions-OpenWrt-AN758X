# 分析证据与复现

本目录保存 REA 原始 JSON、独立 Ghidra 的关键函数摘录、分析脚本、驱动对象编译记录。原始二进制未随补丁提交。

- `rea-npu66-*.json`：REA 实际输出，保留原始 Evidence ID 和样本摘要。路径是本次分析工作区路径。
- `rv32-selected-functions.json`：从独立 Ghidra RV32 导出中按明确地址摘录，保留完整导出的 SHA-256；引用地址的 `ram:` 命名空间规范化为十六进制地址。这不是 REA envelope。
- `build-driver-6.18.*.log`：实际 AArch64 驱动对象构建输出。配置和源码摘要见 `build-summary.json`，不代表完整固件或实机转发通过。
- `tools/Npu*.java`：原始 raw 映射、GP 和候选函数扫描、独立反编译导出脚本。候选扫描可能把数据指针误判为代码，仍需要逐项核对。
- `tools/extract-fit.py`：读取原始 FIT 的 inline/data-position/data-offset 图片数据用于检查 rootfs；不修改输入文件。

## REA 分析原厂 Linux 模块

使用 REA、Ghidra 12.1.4 和 JDK 21。先把 `GHIDRA_INSTALL_DIR` 和 `JAVA_HOME` 配到本地安装，然后运行：

```sh
"$REA_DIR/scripts/rea.mjs" function "$NPU_MODULE" init_module --provider ghidra --format json
"$REA_DIR/scripts/rea.mjs" function "$NPU_MODULE" fileCopyToSram --provider ghidra --format json
```

原始 `npu.ko` 应与主报告的 SHA-256 一致。模块解析地址包含分析器重定位，不能写入设备寄存器。

## 独立 Ghidra 分析 RV32 raw

下面示例使用上传的 1456 文件，`NPU_CODE`、`NPU_DATA` 指向原始文件；`SCRIPT_DIR` 指向本目录的 tools。输出项目和 JSON 放在独立分析目录：

```sh
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$NPU_PROJECTS" factory1456 \
  -import "$NPU_CODE" -loader BinaryLoader -loader-baseAddr 0x84000000 \
  -processor RISCV:LE:32:default -cspec gcc \
  -scriptPath "$SCRIPT_DIR" -preScript NpuMap.java "$NPU_DATA" \
  -postScript NpuSeed.java 0x3e9013a0 \
  -postScript NpuDump.java "$NPU_OUTPUT"
```

5.4 和 6.6 使用各自配套的数据文件，GP 分别为 `0x3e901258`、`0x3e901328`。GP 常量来自原始启动代码。需核对警告、函数边界和交叉引用，不能把导出函数数当作原厂函数数。

## 编译记录

在对应 Linux 源码应用固定 OpenWrt generic/Airoha 补丁栈和本项目队列，启用 Airoha Ethernet/NPU、FLOW_STATS、DEBUG_FS、WERROR，使用 AArch64 GCC 14.4.0：

```sh
make -C "$KERNEL_SOURCE" O="$KERNEL_BUILD" ARCH=arm64 \
  CROSS_COMPILE="$CROSS_PREFIX" prepare modules_prepare
make -C "$KERNEL_SOURCE" O="$KERNEL_BUILD" ARCH=arm64 \
  CROSS_COMPILE="$CROSS_PREFIX" W=1 drivers/net/ethernet/airoha/
```

本次为独立 arm64 配置的驱动对象编译。最终 OpenWrt 镜像的包依赖、封装和设备表现由后续构建及实机核对确认。
