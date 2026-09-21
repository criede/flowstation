#!/usr/bin/env bash
set -euo pipefail

# Run inside a native Debian container with /source read-only and /output writable.
: "${DEB_VERSION:?Set the Debian package version}"
: "${SOURCE_DATE_EPOCH:?Set the source commit timestamp}"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  build-essential ca-certificates curl pkg-config libsoapysdr-dev \
  libclang-dev clang cmake python3 git binutils
mkdir -p /build /output
# Keep git metadata: tetra-core embeds git describe output in the binary.
tar -C /source --exclude=./target -cf - . | tar --no-same-owner -C /build -xf -
cd /build
toolchain=$(python3 -c 'import tomllib; print(tomllib.load(open("rust-toolchain.toml", "rb"))["toolchain"]["channel"])')
curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs -o /tmp/rustup-init.sh
sh /tmp/rustup-init.sh -y --profile minimal --default-toolchain "$toolchain"
export PATH="/root/.cargo/bin:$PATH"
# Asterisk SIP/RTP bridge needs the native TETRA ACELP codec; build the latest
# upstream main statically so the package has no extra runtime library dependency.
git clone --depth 1 --branch main https://github.com/outerplane/tetra-codec /tmp/tetra-codec
cmake -S /tmp/tetra-codec -B /tmp/tetra-codec/build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF
cmake --build /tmp/tetra-codec/build --parallel
cmake --install /tmp/tetra-codec/build
ldconfig
cargo build --locked --release -p bluestation-bs --features asterisk
if ldd target/release/bluestation-bs | grep -q tetra-codec; then
  echo "libtetra-codec is dynamically linked; the package would miss it at runtime" >&2
  exit 1
fi
cargo test --locked --workspace
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo clippy --locked -p bluestation-bs --features asterisk --all-targets -- -D warnings
cargo install cargo-deb --version 3.8.0 --locked
arch=$(dpkg --print-architecture)
cargo deb --locked --no-build -p bluestation-bs \
  --deb-version "$DEB_VERSION" --output "/output/flowstation_${DEB_VERSION}_${arch}.deb"
install -m 755 target/release/bluestation-bs /output/bluestation-bs
tar -C /output -czf "/output/flowstation_${DEB_VERSION}_${arch}.tar.gz" bluestation-bs
rm /output/bluestation-bs
printf 'Source: %s\nVersion: %s\nArchitecture: %s\nRust: %s\n' \
  "${SOURCE_SHA:?}" "$DEB_VERSION" "$arch" "$(rustc --version)" \
  > "/output/build-info_${DEB_VERSION}_${arch}.txt"
