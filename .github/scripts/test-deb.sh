#!/usr/bin/env bash
set -euo pipefail

# No systemd or radio is started in this clean target-distribution container.
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends /packages/*.deb
test "$(dpkg-query -W -f='${Architecture}' flowstation)" = "$(dpkg --print-architecture)"
test -f /etc/flowstation/config.toml
test -f /usr/lib/systemd/system/bluestation-bs.service || \
  test -f /lib/systemd/system/bluestation-bs.service
test ! -e /etc/systemd/system/multi-user.target.wants/bluestation-bs.service
test -f /var/lib/dpkg/info/flowstation.postinst
test -f /var/lib/dpkg/info/flowstation.prerm
test -f /var/lib/dpkg/info/flowstation.postrm
bluestation-bs --help
if ldd /usr/bin/bluestation-bs | grep -q 'not found'; then
  echo 'Missing runtime library' >&2
  exit 1
fi
# Check conffile preservation when reinstalling the package.
printf '\n# package preservation test\n' >> /etc/flowstation/config.toml
apt-get install -y --reinstall --no-install-recommends /packages/*.deb
grep -q '^# package preservation test$' /etc/flowstation/config.toml
