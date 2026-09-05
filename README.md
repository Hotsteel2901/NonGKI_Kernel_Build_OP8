# NonGKI_Kernel_Build_OP8

Automated kernel build for **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** with **LineageOS 23.2 (Android 16)**.
Formatted after [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) (sample branch).
Chinese docs: [README_cn.md](README_cn.md)

## Integrations
| Component | Note |
|---|---|
| KernelSU (backslashxx) | KernelSU fork (`xxksu`), manual hooks per [backslashxx/KernelSU#5](https://github.com/backslashxx/KernelSU/issues/5) (v2.3, exec via do_execveat_common); no SUSFS-version detection in manager |
| SUSFS v2.3.0 | Official gki v2.3.0 + JackA1ltman's proven 4.19 adaptations (i_state flags / p->state=0 / legacy fsnotify API) |
| ReKernel-X | v9.2 4.19 移植 (内置驱动), CONFIG_REKERNEL_X=y |
| DroidSpaces | cgroup prefix hiding + Non-GKI configs (incl. USER_NS) |
| Baseband Guard | partition write protection LSM |

## Usage
1. Fork this repo, enable **Actions** with `Read and write permissions`.
2. Run the `Build Kernel` workflow (or push to trigger).
3. Download the zip artifact and flash it via recovery (AnyKernel3 style).
4. Verify in KernelSU Manager: allowlist & modules working (backslashxx fork, like official KernelSU; SUSFS runs kernel-side only, version is **not** shown in the manager).

## Patches (Patches/)
| File | Content | Applied by |
|---|---|---|
| `Patch/susfs_patch_to_4.19.patch` | SUSFS v2.3.0 kernel-side code | patch-susfs action |
| `Patch/backslashxx_manual_hooks.patch` | KernelSU manual hooks (do_execveat_common execve / faccessat / newfstatat / newfstat-ret / sys_reboot, #5 v2.3) + SUSFS stat/uname spoof + `susfs_is_current_ksu_domain()` | custom workflow step |
| `Patch/backslashxx_susfs_bridge.patch` | SUSFS↔KernelSU bridge into backslashxx source (SUSFS command dispatch, `susfs_init`, sdcard monitor, umount flag) | custom workflow step |
| `RekernelX/rkx-4.19.patch` | ReKernel-X 4.19 移植 (driver + binder + signal + genl) | patch-rekernel action |
| `Droidspaces/*` | droidspaces.config + 2 cocci scripts | patch-droidspaces action |

> All patches are generated against kernel commit `4238ee49a84b`; the workflow pins that commit (`git checkout 4238ee49a84b`).
> Regenerate patches after upstream changes:
> ```bash
> git diff <new-base> -- <susfs-files> > Patches/Patch/susfs_patch_to_4.19.patch
> ```

## Key settings (build-oneplus-8-los23-a16.yml)
- `KERNEL_SOURCE/Branch`: LineageOS official repo, `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **required** (schgm-flash.c needs CONFIG_OPLUS_SM8250_CHARGER)
- KernelSU (backslashxx) stays **latest** (setup.sh git pull each run)
- dtb: custom step concatenates `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img`; dtbo not packed (stock partition used)

## Deviations from Jack's original (intentional)
- `patch-no-kprobe` removed: its hook scripts target KSU v1.x bool hooks (incompatible with ReSukiSU inline); its selinuxfs static-symbol removal is skipped anyway (CONFIG_KALLSYMS_ALL=y)
- Only the 4.19 susfs patch is kept (fixed device kernel version)
- ReKernel-X 4.19 in-tree port via patch (replaces Re:Kernel v8.5)
- HOOK_METHOD kept but inert: manual hooks come from backslashxx_manual_hooks.patch (backslashxx mode); `CONFIG_KSU_HACK_ARM64_BRANCH_LINK`/`CONFIG_KSU_TAMPER_SYSCALL_TABLE` stay off, KSU uses manual hooks + LSM
- backslashxx defines no `CONFIG_KSU_SUSFS*` in its Kconfig; orphan config symbols are dropped by `olddefconfig`, so the workflow appends the SUSFS Kconfig block to `drivers/kernelsu/Kconfig` (see "Add SUSFS Kconfig definitions" step). `backslashxx_manual_hooks.patch` also provides `susfs_is_current_ksu_domain()` (backslashxx lacks it), so the unchanged SUSFS 4.19 patch links against this fork.
- SUSFS needs the KernelSU fork to bridge between the `ksu_susfs` userspace tool and `fs/susfs.c`. The master branch's ReSukiSU has this built-in; **backslashxx has none of it** (so the tool's sys_reboot(SUSFS_MAGIC) calls went nowhere and SUSFS was inert). `backslashxx_susfs_bridge.patch` ports the missing pieces into backslashxx's source, mirroring ReSukiSU:
  - `ksu_handle_susfs_cmd()` in `supercall/dispatch.c` (dispatches all `CMD_SUSFS_*` to `fs/susfs.c`, wrapped in `#ifdef CONFIG_KSU_SUSFS` like ReSukiSU)
  - `SUSFS_MAGIC` routing in `ksu_handle_sys_reboot()` (`supercall/supercall.c`) plus its `extern` declaration; logs `sys_reboot: SUSFS cmd dispatch: ...` for `dmesg` debugging
  - `susfs_init()` in `kernelsu_init()` (`ksu.c`, with `<linux/susfs.h>`/`<linux/susfs_def.h>` includes)
  - `susfs_start_sdcard_monitor_fn()` on boot completed (`supercall/dispatch.c`)
  - `susfs_set_current_proc_umounted()` in `ksu_handle_umount()` (`feature/kernel_umount.c`, so sus_path hiding applies to umounted apps)
  - The workflow verifies after patching: any `.rej/.orig` or a missing dispatch symbol fails the build loudly instead of shipping a broken kernel silently.

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
