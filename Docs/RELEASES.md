# Releases and Debian repository

This fork follows the structure of
[svxlink-db9cr's upstream automation](https://github.com/criede/svxlink-db9cr/blob/master/.github/UPSTREAM-SYNC.MD),
using Cargo and cargo-deb for this Rust project.

## Workflows

- `ci.yml`: pull requests and main pushes run automation checks and the Rust /
  Debian matrix. No publishing credentials are exposed to pull requests.
- `sync-upstream.yml`: daily at 02:17 UTC (03:17 CET / 04:17 CEST), merges
  `razvanzeces/flowstation:main` into `criede/flowstation:main`. Own `.github`
  files are restored before committing. Other conflicts abort without pushing.
  Never force-push. Tags and upstream releases are not mirrored.
- `build.yml`: reusable native Rust build, tests, Clippy, cargo-deb and fresh
  installation tests for Bookworm/Trixie, AMD64/ARM64. All four must pass before
  publication. SoapySDR is supplied by the matching Debian distribution.
- `build-and-publish.yml`: callable from sync, manually, or on `v*` tag pushes.
  Builds the resolved full commit SHA, publishes binary archives, .deb files,
  build provenance and SHA256SUMS, then updates signed APT metadata and Pages.
  The workflow is reusable in other forks; update the APT HTML URLs there.

An unchanged scheduled sync skips builds. A manual sync always builds. A
heartbeat after 25 days without commits keeps GitHub's 60-day inactivity limit
from silently disabling the schedule. Enable Actions and scheduled runs on the
fork first. Called build jobs appear under the sync run in the Actions UI.
`GITHUB_TOKEN` pushes do not trigger another workflow, so sync calls the build
workflow explicitly. A PAT may additionally trigger CI.

## Initial GitHub setup

1. Push these changes to the default branch `main`, and enable GitHub Actions.
2. Set secret `APT_SIGNING_KEY` to an ASCII-armored private signing key without
   a passphrase. Generate one locally, record its fingerprint and keep a backup:

   ```sh
   gpg --batch --passphrase '' --quick-generate-key 'FlowStation APT Repository' rsa4096 sign 3y
   gpg --list-secret-keys --keyid-format long 'FlowStation APT Repository'
   gpg --armor --export-secret-keys FINGERPRINT | gh secret set APT_SIGNING_KEY --repo criede/flowstation
   ```

3. Under Settings > Pages, select **GitHub Actions** as the publishing source.
   This is a GitHub Pages APT repository, not a Sites deployment. Allow `main`
   and release tags in the `github-pages` deployment environment. The workflow
   token cannot change existing administrative Pages/environment policies.
4. Allow the workflow's `contents: write` push to `main` and `gh-pages` in branch
   rules. Where necessary, set `UPSTREAM_SYNC_TOKEN` to a repository-scoped token
   with Contents and Workflows read/write permissions. Never put it in git.
5. Run **Build and publish** manually for an initial build, or **Sync upstream**
   to merge first. Leave inputs empty for a daily build. A supplied `source_sha`
   must be the full 40-character SHA and contain this build infrastructure.

Signing fails early without the secret. Private keys are imported into a
temporary isolated GNUPGHOME and removed in an always-running cleanup step.
Only public keys are published. Monitor key expiry; replacing the key requires
operators to update their installed keyring after verifying the new fingerprint.

## Versions and storage

For stable releases, create an existing source tag `v0.4.0` matching the
workspace version, then push it. Fork packaging revisions may use
`v0.4.0-db9cr.2` (Debian version `0.4.0-2~bookworm`). The first `vX.Y.Z` uses
revision 1; start additional fork revisions at 2 to avoid a version collision.
The manual `tag` input rebuilds an existing tag. Tags and source_sha must agree.

Dailys use `0.4.0+dailyYYYYMMDD.RUN.ATTEMPT.gSHA-1~bookworm`. They become
prereleases, never Latest. They sort higher than the stable release of the same
base version but lower than the next project version. The main APT component
contains both; pin/hold a version to stay on a stable build.

Parallel build jobs upload temporary artifacts (14-day retention); one serialized
publish job owns `gh-pages`, preventing competing architecture pushes. Its pool
persists previous packages. Existing package versions cannot be replaced by
different bytes; bump the revision to publish a changed rebuild. Publication
is not a transaction across GitHub Releases and Pages: retry after a deployment
failure, and check both destinations. No partial matrix is published.

```text
pool/<suite>/main/f/flowstation/*.deb
dists/<suite>/main/binary-<arch>/Packages[.gz]
dists/<suite>/Release, Release.gpg, InRelease
pubkey.gpg                       ASCII-armored public key
flowstation-archive-keyring.gpg   binary public key
index.html                      installation instructions
```

Daily retention is shared by release and pool cleanup: every build under 7 days,
newest per ISO week until 30 days, newest per month until 365 days. Stable
versions and the latest daily per suite/architecture are retained. Unrecognized
versions are never deleted. Git history on gh-pages still contains old objects;
retention limits the deployed site, not historical git storage.

## Installation

After a successful deployment, follow
<https://criede.github.io/flowstation/>. Supported targets are Debian 12/13 and
64-bit Raspberry Pi OS Bookworm/Trixie, on AMD64/ARM64 as appropriate. Do not
substitute a different suite on an unsupported OS.

```sh
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://criede.github.io/flowstation/flowstation-archive-keyring.gpg \
  | sudo tee /etc/apt/keyrings/flowstation.gpg > /dev/null
sudo chmod 0644 /etc/apt/keyrings/flowstation.gpg
. /etc/os-release
arch=$(dpkg --print-architecture)
echo "deb [arch=$arch signed-by=/etc/apt/keyrings/flowstation.gpg] https://criede.github.io/flowstation $VERSION_CODENAME main" \
  | sudo tee /etc/apt/sources.list.d/flowstation.list
sudo apt update
sudo apt install flowstation
sudo editor /etc/flowstation/config.toml
sudo systemctl enable --now bluestation-bs.service
journalctl -u bluestation-bs.service -f
```

Install the SoapySDR module appropriate to the actual SDR separately. The
default package excludes Asterisk/native tetra-codec. The packaged unit comes
from `contrib/packaging/bluestation-bs.service`; `contrib/systemd` is the
source-install template with user-specific paths. The existing packaged service
runs as root for hardware/scheduling and dashboard management; that behavior
has not been redesigned here. Installation does not enable/start the service.
Configure station identity, RF settings, SDR and dashboard access before start.

The config is a dpkg conffile and local edits survive upgrades. An upgrade does
not automatically restart an operating station; schedule a manual
`sudo systemctl restart bluestation-bs` when ready. Use APT for packaged binary
updates, not the dashboard's source-tree rebuild/OTA feature.

Rollback: `apt list -a flowstation`, then `sudo apt install flowstation=VERSION`.
Use `sudo apt-mark hold flowstation` and `sudo apt-mark unhold flowstation` to
pause/resume upgrades. Versions remain available within the retention window.
