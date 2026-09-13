# Fork changelog

## Unreleased

- Add Rust-focused agent instructions, development documentation and pinned
  Rust 1.98.1 tooling.
- Track razvanzeces/flowstation main daily, preserve fork automation and stop
  on source conflicts. Build the synchronized commit via a reusable workflow.
- Build Rust, run workspace tests and Clippy, and package Debian Bookworm/Trixie
  for native AMD64/ARM64 runners. Test installation in fresh containers.
- Publish tagged releases and daily prereleases with binary archives, Debian
  packages, provenance and SHA256 checksums.
- Publish a signed APT repository through GitHub Pages with shared daily
  release/package retention and installation instructions.
- Fix existing Debian systemd integration by generating maintainer scripts;
  preserve operator configuration and leave service activation to the operator.
- Remove scheduler-sensitive timing from a presence-tracking regression test
  and align existing style-lint allowances with the pinned compiler.

See [release setup](Docs/RELEASES.md) and
[the upstream comparison](https://github.com/razvanzeces/flowstation/compare/main...criede:flowstation:main).
