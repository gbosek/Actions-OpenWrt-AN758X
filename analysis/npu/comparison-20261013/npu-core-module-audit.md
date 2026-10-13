# 原厂6.6 npu.ko：加载和启动控制审计

日期：2026-10-13。目标设备 XG2010G 没有 WiFi；`npu_wifi.ko` 不进入此次有线适配范围。输入来自用户上传 ZIP，原始字节未修改。

## 本文件代码范围

SHA-256：`1f8f2e2a7eab33197b24204e4c4ea45aa952cabf10f331337bb6c8bc237a079d`。ARM64 ELF ET_REL、vermagic 6.6.23、Proprietary。

`.text` 1536字节，`.exit.text` 64字节。8个非导入函数的实际地址范围覆盖这1600字节；不是原厂整个HWNAT驱动的覆盖率。模块重定位分析地址不代表设备实际地址。

| 分析地址 | 字节数 | 已恢复行为 |
| --- | ---: | --- |
| `0x100000` | 324 | proc write：解析 core0..7 或8，调用外部 `host_dump_npu_csr` |
| `0x100144` | 372 | `fileCopyToSram`：文件路径、大小检查，委托实际 RAM 复制 |
| `0x1002b8` | 288 | `init_module`：加载 code/data，初始化必要信息，启动核心和建立 proc 节点 |
| `0x1003d8` | 28 | `boot_all_npu_cores`：转调外部 `boot_npu_all_cores` |
| `0x1003f4` | 132 | `AN7552_NPU_PS`：芯片特定省电接口，不视为AN7581通用控制 |
| `0x100478` | 360 | 原模块附带的 WiFi mapping 诊断查询；不用于XG2010G适配 |
| `0x1005e0` | 32 | proc write：调用上述 mapping 诊断 |
| `0x100600` | 64 | `cleanup_module`：原模块 proc/外部清理 |

REA 默认模型把 `0x1005e4` 误当成函数；原始 `.rela.rodata` 指向 `.text+0x5e0`，入口首指令为 PACIASP，`+0x5e4` 为内部 STP。本次在独立 Ghidra 数据库修复边界；没有修改输入模块。完整函数范围、伪代码和指令见 `ghidra-npu66-inventory.json`。

## 加载和错误处理

`init_module` 从 `/userfs/npu_rv32.bin`、`/userfs/npu_data.bin` 取文件，上限分别2MiB和64KiB；data传入地址为 `0xbe900000`。原模块在 RAM 检查或文件加载失败分支仍返回0，所以“insmod成功”不能证明固件已经启动。

真正的 `copy_file_to_ram`、`set_npu_needed_info`、`boot_npu_all_cores`、`host_notify_npuMbox`、CSR和省电实现由外部符号提供。上传包没有提供这些函数及完整HWNAT主机实现。原模块自身也调用WiFi外部初始化；它不是一个可直接移植到当前6.18的有线驱动。

## REA 与补充分析的边界

| REA 操作 | 实际 Evidence ID |
| --- | --- |
| overview | `ev_96a2d5820cf24eb2730ff966d0ad71220dd3ee7210fc72d27a4f40061f8930aa` |
| init_module | `ev_64f4a67e83a07cd7d57711735856d382857229253ce245d6a480e1973617a4d7` |
| fileCopyToSram | `ev_6019a052f843dbc7e965379288acd4c4215f734dc6d01770106c4496b12f6086` |

REA 原始 JSON 保留在父目录。匿名回调、边界修复及完整代码清单属于独立 Ghidra 补充，不伪装为上述REA操作的结果。

## 用于当前项目的结论

该文件支持确认原厂加载、启动及诊断顺序；它没有提供完整的PPE表项生成、双PPPoE会话隔离或PON bearer控制实现。当前项目继续使用Linux6.18的Airoha主机驱动与1456原始firmware，参考原厂机制完善有线控制，不加载这个6.6.23模块。
