# NonGKI_Kernel_Build_OP8

Automated kernel build for **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** with **LineageOS 23.2 (Android 16)**.
Formatted after [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) (sample branch).
Chinese docs: [README_cn.md](README_cn.md)

## Branches

| Branch | Kernel source | Root implementation | Workflow |
|---|---|---|---|
| `master` | LineageOS `lineage-23.2` | ReSukiSU (SUSFS inline hooks) | `Build Kernel` |
| `KSU` | LineageOS `lineage-23.2` | KernelSU (backslashxx, manual hooks + SUSFS bridge) | `Build Kernel` |
| `ReSuki_Luk` | luk1337 `luk` | ReSukiSU (SUSFS inline hooks) | `Build luk Kernel` |

> **`ReSuki_Luk`**: based on [luk1337/android_kernel_oneplus_sm8250](https://github.com/luk1337/android_kernel_oneplus_sm8250)
> branch `luk` (4.19.325). That kernel ships the full OPLUS/OOS configuration (`vendor/oplus.config`), so
> **one artifact works on both custom ROMs (LineageOS / crDroid, ...) and OOS**.
> The branch has its own `Patches/luk/` set and `build-luk-op8.yml` workflow - see [Patches/luk/README.md](Patches/luk/README.md).

## Integrations
| Component | Note |
|---|---|
| ReSukiSU | KernelSU fork, CONFIG_KSU_SUSFS (inline hook) mode |
| SUSFS v2.3.0 | Official gki v2.3.0 + JackA1ltman's proven 4.19 adaptations (i_state flags / p->state=0 / legacy fsnotify API) |
| ReKernel-X | v9.2 4.19 移植 (内置驱动), CONFIG_REKERNEL_X=y |
| DroidSpaces | cgroup prefix hiding + Non-GKI configs (incl. USER_NS) |
| Baseband Guard | partition write protection LSM |

## Usage
1. Fork this repo, enable **Actions** with `Read and write permissions`.
2. Run the `Build Kernel` workflow (or push to trigger).
3. Download the zip artifact and flash it via recovery (AnyKernel3 style).
4. Verify in KernelSU Manager: SUSFS version **2.3.0**, allowlist & modules working.

## Patches (Patches/)
| File | Content | Applied by |
|---|---|---|
| `Patch/susfs_patch_to_4.19.patch` | SUSFS v2.3.0 kernel-side code | patch-susfs action |
| `Patch/resukisu_inline_hooks.patch` | ReSukiSU SUSFS inline hooks: exec / open / read_write / stat / input / reboot / setresuid (+ SUS_KSTAT / SPOOF_UNAME bits) | custom workflow step |
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
> all 7 hooks pass ReSukiSU's compile-time `inline_hook_check.mk` (static_key gated).
> On 4.19 `__do_execve_file()` returns early (before `out_free:`) on the success path, so
> `ksu_handle_post_execveat_sucompat` sits on the exec-success path (the su fd must be installed after the
> exec into ksud - semantically the same spot as in the official 5.10 `do_execveat_common` layout).

## Key settings (build-oneplus-8-los23-a16.yml)
- `KERNEL_SOURCE/Branch`: LineageOS official repo, `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **required** (schgm-flash.c needs CONFIG_OPLUS_SM8250_CHARGER)
- ReSukiSU stays **latest** (setup.sh git pull each run)
- dtb: custom step concatenates `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img`; dtbo not packed (stock partition used)

## Deviations from Jack's original (intentional)
- `patch-no-kprobe` not used: its `susfs_inline_hook_patches.sh` is Jack's official inline-hook implementation (SUSFS v2.3.00+, compatible with ReSukiSU inline); the repo ships the equivalent content as `resukisu_inline_hooks.patch` (patch-based flow, reviewable, fixed apply order). Its selinuxfs static-symbol removal is skipped anyway (CONFIG_KALLSYMS_ALL=y)
- Only the 4.19 susfs patch is kept (fixed device kernel version)
- ReKernel-X 4.19 in-tree port via patch (replaces Re:Kernel v8.5)
- HOOK_METHOD kept but inert: ReSukiSU inline hooks come from resukisu_inline_hooks.patch

## Patch Record Archive (Patches/Archive/)

Complete patch records from local development:
- `0000-full-all-changes.patch` — full combined patch set
- `0001-resukisu-susfs.patch` — ReSukiSU+SUSFS v2.2.0 complete integration (namei/namespace/proc etc.)
- `0001-rekernel.patch` / `0001-droidspaces-cgroup-prefix.patch` / `0001-baseband-guard.patch` / `0001-defconfig.patch`
- `README-record.md` — development log (version history / known issues / build notes)

> Note: the workflows actually use the patches under `Patches/Patch/` and `Patches/Rekernel/`;
> `Archive/` is for record only and is not used in builds.

## Credits
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) · [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) · [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
