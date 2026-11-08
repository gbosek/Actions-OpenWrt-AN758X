# MWAN4 简体中文界面

简体中文源文件位于 `po/zh_Hans/mwan4.po`，使用标准 LuCI 翻译机制。
OpenWrt 的 `luci.mk` 自动将其生成到 `luci-i18n-mwan4-zh-cn`，无需更改
MWAN4、NIKKI、WAN/LAN、DNS 或防火墙配置。

## 固件或 SDK 编译

将本应用放到 LuCI applications 目录，启用：

```text
CONFIG_PACKAGE_luci-app-mwan4=y
CONFIG_LUCI_LANG_zh_Hans=y
CONFIG_PACKAGE_luci-i18n-mwan4-zh-cn=y
```

按正常 OpenWrt 编译流程生成适合固件的 APK 或 IPK。应用需要配套的
`mwan4` 后端；高级页面可用性仍取决于后端能力和可选组件。

## 仅编译语言包

安装 gettext，并准备 LuCI 的 `po2lmo` 与 OpenWrt 的 APK v3 工具后执行：

```sh
PO2LMO=/path/to/po2lmo APK=/path/to/apk sh scripts/build-zh-cn.sh /tmp/mwan4-zh-cn
```

脚本生成 LMO 和无签名的 APK v3 语言包。脚本不会访问或修改路由器。
旧版 opkg 固件请通过对应 SDK 编译 IPK，不能直接安装 APK。

语言包文件为 `/usr/lib/lua/luci/i18n/mwan4.zh-cn.lmo`。选择 LuCI 简体中文
或浏览器中文后刷新页面即可；不需要重启网络或 MWAN4。

## 此次界面修复

- 补齐概览、WAN 线路、路径、策略、规则、全局设置及高级诊断的中文提示。
- 运行状态枚举只在显示时翻译，后端值及 CSS 状态判断保持原义。
- 健康检测失败数读取 `failed_targets`，目标总数使用实际目标列表。
- WAN 加入/移出路由按钮用明确的操作说明，避免误解为网口物理启停。
