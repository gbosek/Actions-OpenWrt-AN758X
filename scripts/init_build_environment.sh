#!/bin/bash
# OpenWrt host build prerequisites only. No remote shell, full-upgrade or TeX.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt_options=(-o Acquire::Retries=2 -o Acquire::http::Timeout=30
  -o Acquire::https::Timeout=30 -o DPkg::Lock::Timeout=120
  -o APT::Update::Error-Mode=any)
packages=(autoconf automake autopoint bc binutils bison build-essential bzip2
  ccache clang cmake cpio curl device-tree-compiler dos2unix dwarves file flex
  g++-multilib gawk gcc-multilib gettext git gperf help2man intltool jq
  libelf-dev libgmp-dev libltdl-dev libmpc-dev libmpfr-dev libncurses-dev
  libreadline-dev libssl-dev libtool libyaml-dev llvm ninja-build patch pkgconf
  python3 python3-dev python3-pyelftools python3-setuptools python3-venv
  qemu-utils quilt re2c rsync scons sharutils squashfs-tools subversion swig
  tar texinfo uglifyjs unzip wget xxd xz-utils zip zlib1g-dev zstd)
timeout --signal=TERM --kill-after=15s 240s sudo -E apt-get "${apt_options[@]}" update
timeout --signal=TERM --kill-after=15s 900s sudo -E apt-get "${apt_options[@]}" \
  install -y --no-install-recommends "${packages[@]}"
