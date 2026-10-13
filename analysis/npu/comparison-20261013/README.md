# 2026-10-13 有线 NPU 静态分析补充

XG2010G没有WiFi，`npu_wifi.ko`不用于适配，本目录不纳入其分析输出。原始RV32固件自身可能含WiFi代码；完整候选导出保留这些字节的分析结果，但选择结论只使用有线控制与数据通路。

本目录保存三个raw样本的全部当前候选函数、错误及实际ranges；`analysis-manifest.json`记录完整含指令导出的SHA-256和大小。`full-static-exports.zip`包含本次完整分析资料，原始二进制、Ghidra数据库、编译器和REA缓存不在资料包中。

## 材料

- `rv32-*-candidate-functions.json`：从对应完整inventory机械摘出全部functions，原样保留伪代码、失败和边界。每份标明原始样本、profile及来源文件SHA-256；不是REA evidence envelope，也不是原厂源码或真实函数总数。
- `wired-mailbox-api-ledger.json`：从原始data字和基础profile的函数清单整理出的32条有线静态表记录。保留空/重复项和基础inventory摘要，不代表所有动态接口。5.4/1456补充profile的函数导出另有各自摘要。
- `ghidra-npu66-inventory.json` / `npu66-objdump.txt`：原始ARM64模块自身8个函数的完整补查，外部/thunk分开标记。REA原始证据仍在父目录。
- 四份Markdown审计：旧5.4/6.6、原厂加载模块、Clanker AN7581 NOWIFI源码、当前6.18有线主机控制及剩余问题。
- `tools`：实际使用的独立分析脚本和补充ISA文本。

## 原始导出复现

使用独立Ghidra12.1.4、JDK21。原始 code/data 必须按主报告SHA-256配对，REA当前raw profile不支持RV32。`NpuMap.java`、`NpuSeed.java`在父目录tools；下面的 `SCRIPT_DIR` 应同时包含父目录及本目录脚本。

标准6.6 profile示例：

```sh
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$NPU_PROJECTS" factory66 \
  -import "$NPU_CODE" -loader BinaryLoader -loader-baseAddr 0x84000000 \
  -processor RISCV:LE:32:default -cspec gcc \
  -scriptPath "$SCRIPT_DIR" -preScript NpuMap.java "$NPU_DATA" \
  -postScript NpuSeed.java 0x3e901328 \
  -postScript NpuInventory.java "$NPU_OUTPUT" 0x84002804 0x840027ee
```

补充5.4/1456 profile：在单独的Ghidra工具安装中，把 `npu-rv32-opaque.*` 两个文本放到 `Ghidra/Processors/RISCV/data/languages`。使用该安装自带的 `support/sleigh` 将 `.slaspec` 编译为相应 `.sla`。然后使用 `-processor RISCV:LE:32:NPU_OPAQUE_FC2`；仍导入原始字节。5.4 GP为 `0x3e901258`、补查入口 `0x8400619e/0x84006188`；1456 GP为 `0x3e9013a0`、补查入口 `0x8400bb82/0x8400bb6c`。

此profile只增加SYSTEM/op0x73、funct3=0、rd=0、imm0xFC2的载体译码，保留 `npu_vendor_fc2(rs1)` 为未知副作用userop。它不模拟或证明cache行为，不把原指令替换成NOP，不能据此认为所有反编译表达式或寄存器语义均正确。

ARM64模块先用REA分析原始ELF（父目录README）；缺失匿名回调补查使用独立项目的Ghidra默认ELF导入，再执行 `NpuModuleRepair.java` 和 `NpuInventory.java`。脚本的 `0x100000` 地址基于本次模块合成重定位；若新项目映射不同，先核对ELF relocation并调整分析地址，不能套用为设备地址。

`NpuOldAudit.java`仅用于5.4/6.6的特定地址辅助审计，不能直接用于1456。自动扫描可能把数据当成代码。复现结果必须结合数据指针、汇编、调用和原始relocation检查，不能用成功反编译数衡量真实完成率。

## 机械摘录

如果已在独立工作区得到上述完整 `evidence/` 和 `tools/`，运行：

```sh
python3 prepare-comparison.py --analysis-dir "$ANALYSIS_DIR" --out "$EXPORT_DIR"
```

该脚本仅复制已有分析并摘录JSON，不读取、执行或写回目标固件。资料包的完整清单和每文件摘要见 `bundle-manifest.json`；输入附件不随仓库发布。

## 解释边界

代码范围覆盖与完整驱动语义不同：原厂host HWNAT/PON外部实现未提供；厂商硬件指令和运行时配置有未知项；Clanker仅为明确提交的源码审计。当前证据支持1456作为6.18基线，不支持宣称双PPPoE、所有方向转发或性能已实测通过。
