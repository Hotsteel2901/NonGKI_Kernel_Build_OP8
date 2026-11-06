# NonGKI_Kernel_Build_OP8

Automated kernel build for **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** with **LineageOS 23.2 (Android 16)**.
Formatted after [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) (sample branch).
Chinese docs: [README_cn.md](README_cn.md)

## Integrations
| Component | Note |
|---|---|
| KernelSU (backslashxx) | **[backslashxx/KernelSU](https://github.com/backslashxx/KernelSU)** master, pinned to `4e6e9ff`. This fork has **no upstream SUSFS support**, so the kernel side is a **hand-written bridge maintained in this repo** — not BakaSU's official inline-hook set. |
| SUSFS v2.3.0 | Official gki v2.3.0 + JackA1ltman's proven 4.19 adaptations (i_state flags / p->state=0 / legacy fsnotify API) |
| Hybrid Mount VFS | `fs/hybridmount` built-in 4.19 port (keyring magic `"hm1"`), **default ON** |
| NoMount VFS | `fs/nomount` built-in via upstream `kernel/setup.sh` (keyring magic `"NOMOUNT"`), off by default |
| ReKernel-X | v9.2 4.19 移植 (内置驱动), CONFIG_REKERNEL_X=y |
| DroidSpaces | cgroup prefix hiding + Non-GKI configs (incl. USER_NS) |
| Baseband Guard | partition write protection LSM |

## Usage
1. Fork this repo, enable **Actions** with `Read and write permissions`.
2. Run the `Build Kernel` workflow (or push to trigger).
3. Download the `*.zip` artifact and flash it via recovery — this is an **AnyKernel3** package:
   - Reboot to **Recovery** (TWRP / Lineage Recovery / crDroid Recovery)
   - **Apply update** → **Apply from ADB**, then `adb sideload NonGKI_Kernel_<codename>_<build>.zip`
   - Reboot to **System**
   - The kernel image is the only thing replaced — `/data` is **not** wiped. Back up your stock `boot.img` first so you can roll back.
   - **Magisk is NOT compatible** with these builds.
4. Install the **[KernelSU Manager](https://github.com/tiann/KernelSU/releases)** (official manager; backslashxx/KernelSU speaks its protocol) and verify: root works, modules mount, `ksu_susfs` reports SUSFS **2.3.0**.

> Unlike the `master` / `ReSuki_Luk` / `crdroid_Resuki` branches (BakaSU, official SUSFS inline hooks), this branch
> tracks **[backslashxx/KernelSU](https://github.com/backslashxx/KernelSU)** — a leaner fork without SUSFS support,
> hence the hand-written bridge below.

## Patches (Patches/)
| File | Content | Applied by |
|---|---|---|
| `Patch/susfs_patch_to_4.19.patch` | SUSFS v2.3.0 kernel-side code | patch-susfs action |
| `Patch/backslashxx_manual_hooks.patch` | Static call-site hooks for backslashxx (`ksu_handle_execveat/faccessat/stat/newfstat_ret/fstat64_ret/sys_reboot` + SUS_KSTAT / SPOOF_UNAME bits) | custom workflow step |
| `Patch/backslashxx_susfs_bridge.patch` | SUSFS command dispatch into backslashxx: `ksu_handle_susfs_cmd()`, `SUSFS_MAGIC` routing, `susfs_init()`, sdcard monitor, `susfs_set_current_proc_umounted()` | custom workflow step (gated by `SUSFS_ENABLE`) |
| `Patch/hybridmount_patch_to_4.19.patch` | Hybrid Mount VFS subsystem (`fs/hybridmount`, keyring magic `"hm1"`) | custom workflow step (gated by `VFS_HYBRIDMOUNT`) |
| *(NoMount)* | no in-repo patch — pulled from upstream `kernel/setup.sh` | custom workflow step (gated by `VFS_NOMOUNT`) |
| `RekernelX/rkx-4.19.patch` | ReKernel-X 4.19 移植 (driver + binder + signal + genl) | patch-rekernel action |
| `Droidspaces/*` | droidspaces.config + 2 cocci scripts | patch-droidspaces action |

> Patches are generated against the then-current lineage-23.2 tip (now `66e230426430`); the workflow uses the
> **latest** kernel source (no pinned checkout), so `patch -p1` applies them with normal offsets.
> Regenerate after upstream changes:
> ```bash
> git diff <new-base> -- <susfs-files> > Patches/Patch/susfs_patch_to_4.19.patch
> ```
>
> ⚠️ **This branch's hooks are hand-written, not BakaSU's.** BakaSU ships official SUSFS inline hooks
> (`CONFIG_KSU_SUSFS` + `inline_hook_check.mk`); backslashxx/KernelSU has neither, so the two patches above
> are maintained here and must be re-anchored whenever upstream moves.
>
> `KERNELSU_PIN` in `build-oneplus-8-los23-a16.yml` pins KernelSU to the audited SHA, so the patches and the
> source tree always match. To bump: change `KERNELSU_PIN` → regenerate `backslashxx_susfs_bridge.patch`
> against the new SHA → let the `🔎 Verify KernelSU hook symbols` step confirm every hook signature is unchanged.
>
> `backslashxx_manual_hooks.patch` needs the `sucompat.c` hooks to stay **externally visible**, which means
> `CONFIG_KSU_TAMPER_SYSCALL_TABLE` and `CONFIG_KSU_HACK_ARM64_BRANCH_LINK` must both stay `n`
> (`SUCOMPAT_HOOK_TYPE` degrades to `static __always_inline` otherwise). The defconfig step pins both.

## VFS backends (pick at most ONE)

Two path-redirection backends are supported. They both hijack **the same VFS layer**
(`inode_operations` / `file_operations` / `dentry_operations`) and each speaks its own
**incompatible keyring protocol**, so **exactly one may be enabled at a time**. Enabling
two makes the drivers fight over the same hooks: the userspace metamodule cannot handshake
(it reports "kernel not supported"), and it can crash outright. Upstream Hybrid Mount's own
Kconfig states it is *"not compatible with NoMount's metamodule or its tooling"*.

A validation step runs at the start of the build and **fails immediately** if more than one
backend is enabled.

| Switch | Backend | Default | Kernel side |
|---|---|---|---|
| `VFS_HYBRIDMOUNT` | Hybrid Mount VFS | `true` | `fs/hybridmount` (in-tree 4.19 port) |
| `VFS_NOMOUNT` | NoMount VFS | `false` | `fs/nomount` (upstream `setup.sh` integration) |

Set them in the workflow's `env:` block (`build-oneplus-8-los23-a16.yml`) or via the
`workflow_dispatch` inputs where the workflow exposes them.

> Both must be built-in (`=y`), never `=m`: 4.19 has no matching prebuilt `.ko`
> (upstream only ships 5.10/5.15/6.1/6.6/6.12 modules).
>
> Hybrid Mount and NoMount are **same-root, different vendors**: `fs/hybridmount` was forked
> from NoMount but renamed its symbols and changed its wire magic (`"HYBRIDMO"` vs `"NOMOUNT"`),
> so metamodules and tooling are **not** interchangeable. Pick the one your userspace
> manager supports.
>
> The AK3 title line is assembled at build time from the backend actually enabled, so the
> title never claims a backend the kernel does not contain.
>

## Release tags (build-release.yml)

`Build and Release Kernel` builds the kernel and publishes a GitHub **Release** whose tag
identifies exactly which commit was compiled.

| Aspect | Behavior |
|---|---|
| Tag format | `<branch>-v<version>-<unix-ts>`, e.g. `master-v35203-1791179734` |
| Collision | if that exact tag already exists, a `-2`, `-3`, … suffix is appended |
| Tag target | the **actual build commit**, passed up from the kernel job via `build_sha` outputs (not the release job's `HEAD`) |
| Push | `git push origin refs/tags/$NEW_TAG` — **only the current tag** |

Two things here are deliberate and easy to get wrong:

> **Branch prefix.** Without it, a same-day run on a different branch (or the same branch)
> produces a colliding tag and the release fails. The branch name makes tags unique per
> branch and self-describing.

> **Push only the current tag.** Using `git push --tags` also pushes every *other* tag in the
> local history. Since these tags can point at commits that modify `.github/workflows/`,
> GitHub rejects the push with `refusing to allow a GitHub App to create or update workflow
> ... without workflows permission`. Pushing just `refs/tags/$NEW_TAG` never carries that
> history, so no extra permission is needed.
>
> ⚠️ Do **not** try to "fix" that rejection by adding `workflows: write` to the workflow's
> `permissions:` block — `workflows` is **not a valid permission scope**, and including it
> makes GitHub mark the **entire workflow file** as `Invalid workflow file`, breaking every
> workflow on the branch. Valid scopes are only: `actions`, `attestations`, `checks`,
> `contents`, `deployments`, `discussions`, `id-token`, `issues`, `packages`, `pages`,
> `pull-requests`, `repository-projects`, `security-events`, `statuses`.

## Key settings (build-oneplus-8-los23-a16.yml)
- `KERNEL_SOURCE/Branch`: LineageOS official repo, `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **required** (schgm-flash.c needs CONFIG_OPLUS_SM8250_CHARGER)
- `VFS_HYBRIDMOUNT / VFS_NOMOUNT` — mutually exclusive, see the section above
- KernelSU is **pinned** to `KERNELSU_PIN` (`4e6e9ff`) — the hand-written patches are anchored to it, so the build is reproducible
- dtb: custom step concatenates `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img`; dtbo not packed (stock partition used)

## Deviations from Jack's original (intentional)
- `patch-no-kprobe` not used: its `susfs_inline_hook_patches.sh` targets BakaSU's official inline-hook API, which backslashxx does not have; this branch ships its own `backslashxx_manual_hooks.patch` + `backslashxx_susfs_bridge.patch` instead. Its selinuxfs static-symbol removal is skipped anyway (CONFIG_KALLSYMS_ALL=y)
- Only the 4.19 susfs patch is kept (fixed device kernel version)
- ReKernel-X 4.19 in-tree port via patch (replaces Re:Kernel v8.5)
- HOOK_METHOD kept but inert: backslashxx hooks are static call sites from backslashxx_manual_hooks.patch

## Patch Record Archive (Patches/Archive/)

Complete patch records from local development:
- `0000-full-all-changes.patch` — full combined patch set
- `0001-resukisu-susfs.patch` — ReSukiSU (now BakaSU) + SUSFS v2.2.0 complete integration (namei/namespace/proc etc.)
- `0001-rekernel.patch` / `0001-droidspaces-cgroup-prefix.patch` / `0001-baseband-guard.patch` / `0001-defconfig.patch`
- `README-record.md` — development log (version history / known issues / build notes)

> Note: the workflows actually use the patches under `Patches/Patch/` and `Patches/Rekernel/`;
> `Archive/` is for record only and is not used in builds.

## Credits
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) · [BakaSU](https://github.com/Baka-SU/BakaSU) · [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) · [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) · [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
