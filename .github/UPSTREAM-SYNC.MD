# Upstream synchronization

The Rust-specific setup, workflow behavior, signing and installation instructions
are maintained in [Docs/RELEASES.md](../Docs/RELEASES.md).

Direct upstream: `razvanzeces/flowstation`, branch `main`.
Fork: `criede/flowstation`, branch `main`.
Schedule: daily at 02:17 UTC. Manual runs are available in Actions.

The example is [svxlink-db9cr](https://github.com/criede/svxlink-db9cr/blob/master/.github/UPSTREAM-SYNC.MD).
Unlike its automatic local-wins merge policy, this fork stops on source
conflicts. Its own `.github` automation is retained before the merge is committed.
