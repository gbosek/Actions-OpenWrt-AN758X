# XG2010G Linux 6.18.55 selective maintenance

基线为成功交付的723fd37，内核固定6.18.55，保留PON R68、PPE/NPU1456-62、949–960安全门控/RCU/PHY维护、500–1400MHz、MWAN4 r29/LuCI r16中文与默认关闭、Argon3.1、clients r5内存和DNS历史修复。

`scripts/apply-maintenance55.py`在原有所有层安装之后应用唯一的精确差分，按完整输入/输出哈希识别重复安装并拒绝来源漂移。不是将6.18.60的整套驱动复制到6.18.55。

本轮选入：

- **961**：完整转发路径错误传播、VLAN仅匹配VID、嵌套桥FDB移动清理作用域、VLAN去标签计数下溢保护。保留现有自定义桥调用者与安全条件。
- **962**：回移Linux6.18.56 flowtable工作/GC并发同步与表达式初始化失败时释放引用，合并原有工作生命周期修复，避免重复叠加。
- dnsmasq安全边界、ubus释放/重连、解析配置原子发布；odhcp6c ubus重连；PPP仅参数引用处理，未更换非root jail架构。
- FullCone端口范围/标志及既有32位ABI兼容；musl正则溢出；五项netdev LED生命周期/锁/并发；原block-NVMEM错误路径UAF。
- 整理14项继承补丁的上下文，保持其准备后原功能；删去606中与604重复的PCS索引检查，保留全部四项端口数量配置。共享源码已有其他板级代码不等于为XG2010G安装那些设备的组件。

界面使用naoki66：NPU相关最后变更`cf9c4c11cbc670ef1cf15d0a1a1d3e9dc250b210`，仓库头`0b1d8a0a250cb2e4a218b1fad5df2b923a0b0e00`新增内容仅涉及其他clients改动；PON卡片固定`3cb13560459f1d51136dac662baa1f399028b2b4`。采用本地r915适配，保留真实DT预留NPU内存读取、完整PPE导出和原始地址/MAC/VLAN显示。PON仅保留原铺满宽度的布局适配，不修改光功率读数、阈值或数据路径。

暂不纳入整套QDMA/LRO替换、DSA host-FDB重构、NPU DMA池RFC、多MAC覆盖风险的IPv6共享UPDMEM方案、fw4/netifd/ucode整体升级或无关USB/Wi-Fi/音频组件。保留Ethernet所需USB SerDes/PHY。

验证分层：精确源与重复/冲突检查、455项generic头文件补丁/638项完整补丁严格正向fuzz=0重放、真实函数回归、GCC14.4 ARM64对象和CI前置检查；整机CI编译、FIT/SquashFS成品检查、刷机验证分别记录。离线通过不能保证双10G长期稳定，未将本轮变化宣称为已解决LAN1失联或实测增加BND。

`SOURCE.json`保存完整补丁队列、准备后源码哈希、选择范围与上游界面身份。构建会导出`MAINTENANCE55-*`证据；最终镜像要求Linux6.18.55、修复后包版本及DNS init准确哈希。构建触发不等于编译成功。
