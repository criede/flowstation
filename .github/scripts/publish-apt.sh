#!/usr/bin/env bash
set -euo pipefail

: "${REPO_DIR:?}"
: "${PACKAGE_DIR:?}"
: "${GPG_KEY_FPR:?}"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$REPO_DIR"
shopt -s nullglob
packages=("$PACKAGE_DIR"/*.deb)
(( ${#packages[@]} > 0 ))
for package in "${packages[@]}"; do
  name=$(dpkg-deb -f "$package" Package)
  version=$(dpkg-deb -f "$package" Version)
  arch=$(dpkg-deb -f "$package" Architecture)
  suite=${version##*~}
  [[ "$name" == flowstation && "$suite" =~ ^(bookworm|trixie)$ && "$arch" =~ ^(amd64|arm64)$ ]]
  destination="$REPO_DIR/pool/$suite/main/f/flowstation"
  mkdir -p "$destination"
  target="$destination/flowstation_${version}_${arch}.deb"
  if [[ -f "$target" ]] && ! cmp -s "$package" "$target"; then
    echo "Refusing to replace an existing package version: $version/$arch" >&2
    exit 1
  fi
  cp "$package" "$target"
done
python3 "$script_dir/retention.py" pool "$REPO_DIR"
cd "$REPO_DIR"
gpg --batch --armor --export "$GPG_KEY_FPR" > pubkey.gpg
test -s pubkey.gpg
gpg --batch --export "$GPG_KEY_FPR" > flowstation-archive-keyring.gpg
for suite in bookworm trixie; do
  [[ -d "pool/$suite" ]] || continue
  for arch in amd64 arm64; do
    index="dists/$suite/main/binary-$arch"
    mkdir -p "$index"
    dpkg-scanpackages --multiversion --arch "$arch" "pool/$suite" /dev/null > "$index/Packages"
    gzip -n -9 -c "$index/Packages" > "$index/Packages.gz"
  done
  # Do not hash previous Release files into the new Release.
  rm -f "dists/$suite/Release" "dists/$suite/InRelease" "dists/$suite/Release.gpg"
  apt-ftparchive \
    -o APT::FTPArchive::Release::Origin=FlowStation \
    -o APT::FTPArchive::Release::Label=FlowStation \
    -o "APT::FTPArchive::Release::Suite=$suite" \
    -o "APT::FTPArchive::Release::Codename=$suite" \
    -o 'APT::FTPArchive::Release::Architectures=amd64 arm64' \
    -o APT::FTPArchive::Release::Components=main \
    release "dists/$suite" > Release.tmp
  mv Release.tmp "dists/$suite/Release"
  gpg --batch --yes --local-user "$GPG_KEY_FPR" --digest-algo SHA256 \
    --clearsign --output "dists/$suite/InRelease" "dists/$suite/Release"
  gpg --batch --yes --local-user "$GPG_KEY_FPR" --digest-algo SHA256 \
    --armor --detach-sign --output "dists/$suite/Release.gpg" "dists/$suite/Release"
  gpg --batch --verify "dists/$suite/InRelease"
done
cp "$script_dir/apt-index.html" index.html
touch .nojekyll
