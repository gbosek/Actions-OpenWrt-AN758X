# SPDX-License-Identifier: AGPL-3.0-or-later

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-mwan4
PKG_VERSION:=1.0.0
PKG_RELEASE:=19
# This vendored snapshot has no package-local Git history for LuCI findrev.
PKG_PO_VERSION:=$(PKG_VERSION)-r$(PKG_RELEASE)
PKG_LICENSE:=AGPL-3.0-or-later

LUCI_TITLE:=LuCI support for the MWAN4 MultiWAN Manager
LUCI_DEPENDS:=+luci-base +mwan4
LUCI_DESCRIPTION:=Simple, full-featured LuCI interface for mwan4 status and configuration.
LUCI_MAINTAINER:=Braulio Bhavamitra <braulio@brauliobo.org>
LUCI_MINIFY_JS:=0

include ../../luci.mk

# call BuildPackage - OpenWrt buildroot signature
