# NonGKI_Kernel_Build_OP8 — Pure

Automated kernel build for **OnePlus 8 (instantnoodle, sm8250, 4.19.325-cip)** with
**LineageOS 23.2 (Android 16)**, formatted after
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd).
Chinese docs: [README_cn.md](README_cn.md)

**This branch (`Pure`) ships a clean kernel with no root implementation** — no KernelSU /
BakaSU / SUSFS / Magisk / Apatch baked in. Patch it afterwards with Apatch, Magisk, or
whatever you prefer.

> Want root out of the box? Use `master` (BakaSU + SUSFS), `KSU` (backslashxx with a
> hand-written SUSFS bridge), or `ReSuki_Luk` / `crdroid_Resuki` for those ROM trees.

## Integrations

| Component | Note |
|---|---|
| Re:Kernel-X | v9-series 4.19 port (in-tree `drivers/rekernel_x`), `CONFIG_REKERNEL_X=y` |
| DroidSpaces | non-GKI config (PID/IPC/NET/USER ns, cgroup, veth/bridge/NAT) + cgroup prefix hide |
| Baseband Guard | partition write-protection LSM (upstream `setup.sh`, `CONFIG_BBG=y`) |
| Hybrid Mount VFS | `fs/hybridmount`, built-in 4.19 (keyring `"hm1"`), **on by default** |
| NoMount VFS | `fs/nomount` via upstream `kernel/setup.sh` (keyring `"NOMOUNT"`), off by default |

The two VFS backends are **mutually exclusive**: they hijack the same VFS layer with
incompatible keyring protocols. The build validates this up front and fails if both are on.

## Artifact: HotSPatch1 (not AnyKernel3)

`Pure` produces a **HotSPatch1** archive that replaces the kernel inside *your* `boot.img`
on a PC — it is not a recovery flashable zip.

Layout after extraction:

```
kernel          compiled kernel (Image.gz-dtb / Image.gz / Image)
boot_patch.py   replacement logic (stdlib only, no third-party deps)
patch.sh        Linux / macOS launcher
patch.bat       Windows launcher
README.txt      in-package instructions
```

Usage:

1. Extract the archive to a folder;
2. Put your stock `boot.img` in the same folder (name it `boot.img`, or leave a single
   `.img` in the folder — it is auto-detected);
3. Run `./patch.sh` (double-click `patch.bat` on Windows);
4. A `boot-patched.img` is produced;
5. Flash it:

```bash
adb reboot bootloader
fastboot flash boot boot-patched.img
fastboot reboot
```

Details and limits:

- Supports Android boot header **v0 / v1 / v2** (OP8 is v2). v3 / v4 (GKI) fails with a
  clear error instead of producing a broken image;
- Only the kernel segment is replaced: ramdisk / second / recovery_dtbo / dtb / cmdline /
  address fields are preserved, everything is re-aligned to the original `page_size` and the
  header SHA1 id is recomputed;
- An existing AVB footer is stripped (the old signature cannot survive a kernel change);
- The original `boot.img` is never overwritten (`boot-patched.img` is always the output);
- Unlock the bootloader first and keep the original image for
  `fastboot flash boot boot.img` rollback.

## Building

1. Fork this repo and check out `Pure`;
2. **Settings → Actions → General → Workflow permissions** → `Read and write permissions`;
3. **Actions → Build Kernel → Run workflow**, pick one VFS backend (HybridMount / NoMount);
4. Download `*-HotSPatch1.zip` from the run artifacts.

Local builds need x86_64 and ≥ 8 GB RAM; never `-j8` when building on the phone itself.

## Key knobs (`build-oneplus-8-los23-a16.yml`)

| Variable | Value | Note |
|---|---|---|
| `KERNEL_SOURCE` / `KERNEL_BRANCH` | LineageOS `android_kernel_oneplus_sm8250` / `lineage-23.2` | always tracks the latest tip |
| `DEFCONFIG_NAME` | `vendor/kona-perf_defconfig` | merged with `vendor/oplus.config` (`schgm-flash.c` needs it) |
| `PACK_METHOD` | `HotSPatch1` | assembled by `pack-process` |
| `KERNELSU_ENABLE` | `false` | disables the KSU install and defconfig writes in `build-ready` |
| `VFS_HYBRIDMOUNT` / `VFS_NOMOUNT` | `true` / `false` | exclusive, driven by workflow inputs |
| `BASEBAND_GUARD_ENABLE` | `true` | BBG LSM |
| `REKERNEL_ENABLE` / `DROIDSPACES_ENABLE` | `true` | both switchable |

## Release tags (`build-release.yml`)

Tags are `<branch>-v<version>-<unix-ts>` and point at the commit that was actually built
(forwarded through the kernel job's `build_sha` output); only that one tag is pushed.

> Do not add `workflows: write` to `permissions:` to dodge GitHub's workflow permission
> error — it is not a valid scope and turns the whole workflow file into
> `Invalid workflow file`.

## Branch map

| Branch | Root | Artifact |
|---|---|---|
| `master` | BakaSU (official inline hooks) + SUSFS v2.3.0 | AnyKernel3 |
| `KSU` | backslashxx/KernelSU + **hand-written SUSFS bridge** | AnyKernel3 |
| `ReSuki_Luk` | BakaSU + NoMount (luk tree) | AnyKernel3 |
| `crdroid_Resuki` | BakaSU (crdroid tree, staged builds) | AnyKernel3 |
| **`Pure`** | **none** | **HotSPatch1** |

## Known limits

- Build host must be x86_64 (GitHub-hosted runners are fine);
- `dtb.img` is `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` (matches the official DTB_SZ); dtbo is not packaged;
- No SUSFS on `Pure`, so no path/mount hiding — use a root branch if you need that;
- Kernel and ROM versions must match (LineageOS 23.2 / Android 16).

## Credits

- [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — build template and 4.19 porting method
- [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) / [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) / [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
- [Hybrid Mount](https://github.com/Hybrid-Mount/meta-hybrid_mount) / [NoMount](https://github.com/maxsteeel/nomount)
