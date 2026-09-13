# Working on FlowStation

## Project and ownership

This is a Rust 2024 workspace, not a CMake application. The fork is
`criede/flowstation`; its direct upstream is `razvanzeces/flowstation`, branch
`main`. MidnightBlueLabs/tetra-bluestation is the original ancestor, not the
scheduled merge source. Read README.md and Docs/DEVELOPMENT.md first.

- `bins/bluestation-bs`: the only enabled binary, packaged as `flowstation`.
- `crates/tetra-core`: shared types, bit buffers and timing.
- `crates/tetra-config`: TOML configuration and defaults.
- `crates/tetra-saps`: service access point contracts.
- `crates/tetra-pdus`: protocol encoding and decoding.
- `crates/tetra-entities`: PHY, MAC, call control, integrations and dashboard.
- `example_config`: operator templates; never insert real credentials.
- `contrib/systemd`: source-install service template.
- `contrib/packaging`: installed Debian service, using /usr/bin and /etc.
- `.github/workflows` and `.github/scripts`: fork CI, upstream sync and releases.

## Before and after changes

Write all repository-owned text in English, including documentation, comments,
commit messages, workflow names and output, generated web pages, package text,
and user-facing strings added by this fork. Preserve upstream text when merging;
translate it only when this fork intentionally takes ownership of that text.

Inspect the working tree and relevant callers before editing. Preserve unrelated
changes and keep upstream merges separate from feature changes. Use the pinned
rust-toolchain.toml and Cargo.lock. Do not update dependencies incidentally.

On Linux, install the dependencies documented in Docs/DEVELOPMENT.md, then run:

```sh
cargo build --locked --release -p bluestation-bs
cargo test --locked --workspace
cargo clippy --locked --workspace --all-targets -- -D warnings
```

Use the existing rustfmt.toml on changed Rust files; do not mass-format unrelated
protocol code. The workspace intentionally permits existing style lints. Do not
remove these allowances to clean up an unrelated change. Add regression tests
for changed protocol behavior; never claim RF validation from unit tests alone.

## Domain constraints

Preserve protocol timing, bit ordering, allocation/release ownership, duplicate
SDS handling and bounded audio queues. Read nearby tests and comments before
changing these. Default builds deliberately exclude `asterisk`: that feature
requires a separately installed native TETRA codec. Do not enable all features
in CI without provisioning that dependency.

Never start the base station, transmit RF, reset USB devices or contact real
radio/network services as a build smoke test. Use `bluestation-bs --help`.
Do not execute the source-install service's USB reset command during tests.

## Automation and packaging

Read Docs/RELEASES.md before changing workflows. Builds use native Debian
Bookworm/Trixie containers on matching AMD64/ARM64 runners. Keep builds locked,
test package installation, preserve configuration on upgrade and do not enable
or start the service automatically. APT metadata must remain signed; never use
`trusted=yes`. Keep signing keys and tokens out of files, artifacts and logs.
Upstream conflicts must fail visibly, never resolve them automatically with
`-X ours` or force pushes. Report exactly which checks ran and any limitations.
