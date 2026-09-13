#!/usr/bin/env bash
set -euo pipefail

# Exercise APT itself with disposable fixture packages and a disposable key.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scratch=$(mktemp -d)
trap 'gpgconf --kill gpg-agent || true; rm -rf -- "$scratch"' EXIT
export GNUPGHOME="$scratch/gnupg"
export REPO_DIR="$scratch/repository"
export PACKAGE_DIR="$scratch/packages"
mkdir -m 700 "$GNUPGHOME"
mkdir -p "$PACKAGE_DIR" "$scratch/staging/DEBIAN"
gpg --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key 'FlowStation disposable test key' rsa2048 sign 1d
GPG_KEY_FPR=$(gpg --batch --with-colons --list-secret-keys | awk -F: '$1 == "fpr" {print $10; exit}')
export GPG_KEY_FPR
for suite in bookworm trixie; do
  for arch in amd64 arm64; do
    printf 'Package: flowstation\nVersion: 0.4.0-1~%s\nArchitecture: %s\nMaintainer: Test <test@example.invalid>\nDescription: Disposable repository fixture\n' \
      "$suite" "$arch" > "$scratch/staging/DEBIAN/control"
    dpkg-deb --build --root-owner-group "$scratch/staging" "$PACKAGE_DIR/fixture_${suite}_${arch}.deb"
  done
done
bash "$script_dir/publish-apt.sh"
grep -q 'href="dists/"' "$REPO_DIR/index.html"
grep -q 'href="pool/"' "$REPO_DIR/index.html"
while IFS= read -r -d '' directory; do
  test -f "$directory/index.html"
done < <(find "$REPO_DIR/dists" "$REPO_DIR/pool" -type d -print0)
grep -q 'href="../">APT-Repository</a>' "$REPO_DIR/dists/index.html"
grep -q 'href="binary-amd64/"' "$REPO_DIR/dists/bookworm/main/index.html"
grep -q 'flowstation_0.4.0-1~bookworm_amd64.deb' \
  "$REPO_DIR/pool/bookworm/main/f/flowstation/index.html"
for suite in bookworm trixie; do
  gpgv --keyring "$REPO_DIR/flowstation-archive-keyring.gpg" "$REPO_DIR/dists/$suite/InRelease"
  gpgv --keyring "$REPO_DIR/flowstation-archive-keyring.gpg" \
    "$REPO_DIR/dists/$suite/Release.gpg" "$REPO_DIR/dists/$suite/Release"
done
client="$scratch/client"
mkdir -p "$client/etc/apt/sources.list.d" "$client/etc/apt/preferences.d" "$client/var/lib/apt/lists/partial" \
  "$client/var/cache/apt/archives/partial" "$client/var/lib/dpkg" "$scratch/download"
touch "$client/var/lib/dpkg/status"
arch=$(dpkg --print-architecture)
printf 'deb [arch=%s signed-by=%s] file:%s bookworm main\n' \
  "$arch" "$REPO_DIR/flowstation-archive-keyring.gpg" "$REPO_DIR" > "$client/etc/apt/sources.list"
options=(-o "Dir=$client" -o "APT::Sandbox::User=$(id -un)" -o APT::Update::Error-Mode=any)
apt-get "${options[@]}" update
(cd "$scratch/download" && apt-get "${options[@]}" download flowstation)
test -n "$(find "$scratch/download" -name '*.deb' -print -quit)"
# APT must reject a modified signed index.
sed -i 's/Origin: FlowStation/Origin: Tampered/' "$REPO_DIR/dists/bookworm/InRelease"
if apt-get "${options[@]}" update; then
  echo 'APT accepted tampered metadata' >&2
  exit 1
fi
echo 'Signed APT update, download, and tamper rejection passed.'
