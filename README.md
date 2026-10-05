# NonGKI_Kernel_Build_OP8

Automated kernel build for **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** with **LineageOS 23.2 (Android 16)**.
Formatted after [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) (sample branch).
Chinese docs: [README_cn.md](README_cn.md)

## Integrations
| Component | Note |
|---|---|
| BakaSU | KernelSU fork (formerly ReSukiSU), CONFIG_KSU_SUSFS (inline hook) mode |
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
4. Install **[BakaSU Manager](https://github.com/Baka-SU/BakaSU/releases)** and verify in it: SUSFS version **2.3.0**, allowlist & modules working.

> The upstream ReSukiSU project has been renamed/migrated to **[BakaSU](https://github.com/Baka-SU/BakaSU)** (the old
> `ReSukiSU/ReSukiSU` org is archived; GitHub keeps permanent redirects, so old URLs still resolve). This repo now
> points at the new address directly.

## Patches (Patches/)
| File | Content | Applied by |
|---|---|---|
| `Patch/susfs_patch_to_4.19.patch` | SUSFS v2.3.0 kernel-side code | patch-susfs action |
| `Patch/resukisu_inline_hooks.patch` | BakaSU SUSFS inline hooks: exec / open / read_write / stat / input / reboot / setresuid (+ SUS_KSTAT / SPOOF_UNAME bits) | custom workflow step |
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
> The inline hooks match Jack's official `susfs_inline_hook_patches.sh` (official SUSFS v2.3.00+ inline hooks):
> all 7 hooks pass BakaSU's compile-time `inline_hook_check.mk` (static_key gated).
> On 4.19 `__do_execve_file()` returns early (before `out_free:`) on the success path, so
> `ksu_handle_post_execveat_sucompat` sits on the exec-success path (the su fd must be installed after the
> exec into ksud - semantically the same spot as in the official 5.10 `do_execveat_common` layout).

## VFS backends (pick at most ONE)

Three path-redirection backends are supported. They all hijack **the same VFS layer**
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
| `VFS_ZEROMOUNT` | ZeroMount VFS | `false` | **not implemented yet** — enabling fails the build |

Set them in the workflow's `env:` block (`build-oneplus-8-los23-a16.yml`) or via the
`workflow_dispatch` inputs where the workflow exposes them.

> All three must be built-in (`=y`), never `=m`: 4.19 has no matching prebuilt `.ko`
> (upstream only ships 5.10/5.15/6.1/6.6/6.12 modules).
>
> Hybrid Mount and NoMount are **same-root, different vendors**: `fs/hybridmount` was forked
> from NoMount but renamed its symbols and changed its wire magic (`"HYBRIDMO"` vs `"NOMOUNT"`),
> so metamodules and tooling are **not** interchangeable. Pick the one your userspace
> manager supports.
>
> The AK3 title line is assembled at build time from the backend actually enabled, so the
> title never claims a backend the kernel does not contain.

## Key settings (build-oneplus-8-los23-a16.yml)
- `KERNEL_SOURCE/Branch`: LineageOS official repo, `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **required** (schgm-flash.c needs CONFIG_OPLUS_SM8250_CHARGER)
- `VFS_HYBRIDMOUNT / VFS_NOMOUNT / VFS_ZEROMOUNT` — mutually exclusive, see the section above
- BakaSU stays **latest** (setup.sh git pull each run)
- dtb: custom step concatenates `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img`; dtbo not packed (stock partition used)

## Deviations from Jack's original (intentional)
- `patch-no-kprobe` not used: its `susfs_inline_hook_patches.sh` is Jack's official inline-hook implementation (SUSFS v2.3.00+, compatible with BakaSU inline); the repo ships the equivalent content as `resukisu_inline_hooks.patch` (patch-based flow, reviewable, fixed apply order). Its selinuxfs static-symbol removal is skipped anyway (CONFIG_KALLSYMS_ALL=y)
- Only the 4.19 susfs patch is kept (fixed device kernel version)
- ReKernel-X 4.19 in-tree port via patch (replaces Re:Kernel v8.5)
- HOOK_METHOD kept but inert: BakaSU inline hooks come from resukisu_inline_hooks.patch

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
