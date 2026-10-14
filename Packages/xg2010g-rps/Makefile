include $(TOPDIR)/rules.mk

PKG_NAME:=xg2010g-rps
PKG_VERSION:=20261013
PKG_RELEASE:=2
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/xg2010g-rps
  SECTION:=net
  CATEGORY:=Network
  TITLE:=XG2010G persistent four-core RPS tuning
  DEPENDS:=+netifd +flock
endef

define Build/Compile
endef

define Package/xg2010g-rps/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/usr/libexec/platform $(1)/etc/uci-defaults $(1)/etc/hotplug.d/iface $(1)/etc/init.d
	$(INSTALL_BIN) ./files/rps-tune.sh $(1)/usr/bin/rps-tune.sh
	$(INSTALL_BIN) ./files/xg2010g-rps.init $(1)/etc/init.d/xg2010g-rps
	$(INSTALL_BIN) ./files/rps-watch.sh $(1)/usr/bin/rps-watch.sh
	$(INSTALL_BIN) ./files/rps-guard.sh $(1)/usr/bin/rps-guard.sh
	$(INSTALL_BIN) ./files/99-rps-guard $(1)/etc/hotplug.d/iface/99-rps-guard
	$(INSTALL_BIN) ./files/packet-steering.sh $(1)/usr/libexec/platform/packet-steering.sh
	$(INSTALL_BIN) ./files/99-xg2010g-rps $(1)/etc/uci-defaults/99-xg2010g-rps
endef

$(eval $(call BuildPackage,xg2010g-rps))
