# Development

FlowStation is a Rust 2024 workspace. Use the compiler pinned in
`rust-toolchain.toml`; dependencies are resolved by the committed `Cargo.lock`.
The default build produces `bluestation-bs`, without the optional native
Asterisk codec. Agent instructions are in [AGENTS.md](../AGENTS.md).

## Linux setup

On Debian Bookworm/Trixie or Ubuntu 24.04 (including WSL):

```sh
sudo apt-get update
sudo apt-get install build-essential pkg-config libsoapysdr-dev libclang-dev clang cmake curl ca-certificates git
curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs -o /tmp/rustup-init.sh
sh /tmp/rustup-init.sh -y --profile minimal
. "$HOME/.cargo/env"
cargo build --locked --release -p bluestation-bs
cargo test --locked --workspace
cargo clippy --locked --workspace --all-targets -- -D warnings
./target/release/bluestation-bs --help
```

Run from the repository root so rustup selects the pinned compiler. Do not use
`--all-features`: `asterisk` needs a separately installed `tetra-codec` library.
`--help` is safe without radio hardware. Starting with an actual configuration
opens the SDR and can transmit. Unit tests do not validate on-air operation.

Apply `cargo fmt` to changed code only; avoid unrelated formatting churn.
The workspace Clippy allowances include the pre-existing style findings exposed
by Rust 1.98.1; correctness and other unlisted warnings still fail CI. Active crates and
their responsibilities are listed in AGENTS.md; the other binary directories
are not currently workspace members.

## Debian builds

The CI workflow builds and tests Rust inside native Debian containers, packages
with pinned `cargo-deb`, and installs each package in a fresh container. To run
the same build locally on a Linux host with Docker:

```sh
mkdir -p target/packages
docker run --rm -v "$PWD:/source:ro" -v "$PWD/target/packages:/output" \
  -e DEB_VERSION=0.4.0-1~bookworm \
  -e SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)" \
  -e SOURCE_SHA="$(git rev-parse HEAD)" \
  debian:bookworm-slim bash /source/.github/scripts/build-deb.sh
docker run --rm -v "$PWD:/source:ro" -v "$PWD/target/packages:/packages:ro" \
  debian:bookworm-slim bash /source/.github/scripts/test-deb.sh
```

Use a host matching the target architecture. ARM64 is built on ARM64 runners,
AMD64 on AMD64. The existing `Cross.toml` remains available for manual cross
compilation but is not used by Debian release builds.

See [RELEASES.md](RELEASES.md) for signing, publication and operator setup.
