# Argon 3.1 integration

Pinned release: `jerrykuku/luci-theme-argon@96734f4f52e98ac70f564ca4b92644b849e189ba`
(`v3.1.0`, package release `20261022`). `Packages/Themes/SOURCE.json` records
upstream and delivered source hashes. The only runtime compatibility changes are
in `LOCAL-RUNTIME-COMPAT.patch`: whole-value matching for colors, numeric CSS
settings and wallpaper URLs with the pinned ucode runtime's regex semantics.

Replace the two original, known feed providers in place. Use upstream's empty
`luci-app-argon-config` compatibility package; the integrated theme owns the UI,
RPC, configuration and translation. No second legacy UI provider is installed.
The rest of the compatibility feed snapshot and PON R68 remain pinned.

Keep readable assets for exact delivery checks, upstream source templates, and
the existing fresh-image Bing default. Upstream first-boot migration preserves
configured values. This is source integration into a firmware, not an in-place
package-manager upgrade of a running router.

Validation includes old-provider migration, repeated installation, source and
provider conflict rejection, real package-index versions, 13 upstream config
tests, 40 upstream UI/template tests, real ucode validation/template compilation,
and 12 Aurora/Argon CPU/PON responsive layout cases. The workflow checks the real
staged files and package versions before uploading a firmware. Local fixtures
and package scans are not complete firmware or target-device validation.
