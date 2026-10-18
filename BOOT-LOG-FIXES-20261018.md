# XG2010G boot log fixes

Applies to the pinned Airoha Linux 6.18.55 XG2010G build.

- PHY LED setup: the board DTS uses GPIO-controlled panel LEDs and omits a `gbe-led` pinctrl state. The driver now treats that state as optional for this board. If another board declares it, setup errors and probe deferral remain visible. Patch `938-net-phy-an7581-optional-led-pinctrl.patch`.
- Early fstab: install a minimal global `/etc/config/fstab` in the SquashFS image so `block` sees a valid configuration before overlay recovery. Preserve any build-supplied mount or extroot entries.
- Cron severity: enable BusyBox `FEATURE_SYSLOG_INFO`. Startup INFO messages will be recorded at their intended level rather than `cron.err`.
- Large wall-clock steps: keep BusyBox's `time disparity` diagnostic. It indicates cron skipped jobs in the elapsed interval after a large time correction; suppressing it would conceal clock changes.

Integrated by `apply-runtime-fixes.py`, with build-time assertions in `check-runtime-config.py` and `check-xg2010g-build.py`.

Local checks: repeatable installer and custom-fstab preservation; five probe outcomes (optional state absent/present, `-EPROBE_DEFER`, pinctrl error, allocation failure); actual OpenWrt Kconfig expansion; ARM64 PHY object compilation for both project bases. Results: `../validation.json`. Firmware builds and a physical reboot have not been run for this change.
