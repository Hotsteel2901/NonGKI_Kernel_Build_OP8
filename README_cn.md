# NonGKI_Kernel_Build_OP8 — Pure

基于 [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的构建模板，
为 **OnePlus 8 (instantnoodle, sm8250, 4.19.325-cip)** 的 **LineageOS 23.2 (Android 16)** 内核提供自动化编译。

**本分支（Pure）只产出"纯净内核"：不集成任何 root 实现**（无 KernelSU / BakaSU / SUSFS /
Magisk / Apatch 预置），用于你自己用 Apatch、Magisk 等工具事后修补。

> 需要开箱即用的 root？请用 `master`（BakaSU + SUSFS）、`KSU`（backslashxx 手写桥接）、
> `ReSuki_Luk` / `crdroid_Resuki`（对应 ROM 变体）。

## 集成内容

| 组件 | 说明 |
|---|---|
| Re:Kernel-X | v9 系列的 4.19 移植（内置驱动 `drivers/rekernel_x`），`CONFIG_REKERNEL_X=y` |
| DroidSpaces | Non-GKI 配置（PID/IPC/NET/USER ns、cgroup、veth/bridge/NAT 等）+ cgroup 前缀隐藏 |
| Baseband Guard | 分区写保护 LSM（上游 `setup.sh` 动态集成，`CONFIG_BBG=y`） |
| Hybrid Mount VFS | `fs/hybridmount`，4.19 built-in（keyring `"hm1"`），**默认开启** |
| NoMount VFS | `fs/nomount`，走上游 `kernel/setup.sh`（keyring `"NOMOUNT"`），默认关闭 |

VFS 两个后端**互斥**：它们劫持同一层 VFS 且 keyring 协议不兼容，同时开启会让元模块
握手失败甚至崩溃。构建开头有校验，开启多个直接 fail。

## 产物：HotSPatch1（不是 AnyKernel3）

Pure 分支的构建产物是 **HotSPatch1** 压缩包，用于在电脑上把新内核替换进你自己的
`boot.img`，而不是 recovery 刷机包。

解压后的结构：

```
kernel          编译好的内核（Image.gz-dtb / Image.gz / Image）
boot_patch.py   替换逻辑（纯 Python 标准库，无第三方依赖）
patch.sh        Linux / macOS 启动脚本
patch.bat       Windows 启动脚本
README.txt      包内使用说明
```

使用步骤：

1. 解压到一个文件夹；
2. 把原机 `boot.img` 放进同一文件夹（建议就命名为 `boot.img`；目录里只有一个 `.img` 时也会自动识别）；
3. 执行 `./patch.sh`（Windows 双击 `patch.bat`）；
4. 生成 `boot-patched.img`；
5. 刷入：

```bash
adb reboot bootloader
fastboot flash boot boot-patched.img
fastboot reboot
```

细节与限制：

- 支持 Android boot header **v0 / v1 / v2**（OP8 为 v2）；v3 / v4（GKI）会明确报错，不会产出坏包；
- 只替换 kernel 段，ramdisk / second / recovery_dtbo / dtb / cmdline / 地址字段原样保留，
  按原 `page_size` 重新对齐并重算 header 的 SHA1 id；
- 原镜像若带 AVB footer 会被剥离（改 kernel 后原签名必然失效）；
- 不会覆盖原始 `boot.img`（输出固定为 `boot-patched.img`）；
- 刷入前请确认 bootloader 已解锁，并保留原始 `boot.img` 以便 `fastboot flash boot boot.img` 回滚。

## 使用方法（编译）

1. Fork 本仓库，切到 `Pure` 分支；
2. **Settings → Actions → General → Workflow permissions** 选 `Read and write permissions`；
3. **Actions → Build Kernel → Run workflow**，按需勾选 VFS 后端（HybridMount / NoMount，二选一）；
4. 构建完成后在 **Artifacts** 下载 `*-HotSPatch1.zip`。

本地构建（非 Actions）需要 x86_64、内存 ≥ 8G；手机本体构建严禁 `-j8`。

## 关键配置（`build-oneplus-8-los23-a16.yml`）

| 变量 | 值 | 说明 |
|---|---|---|
| `KERNEL_SOURCE` / `KERNEL_BRANCH` | LineageOS `android_kernel_oneplus_sm8250` / `lineage-23.2` | 始终跟随最新 tip，不 pin |
| `DEFCONFIG_NAME` | `vendor/kona-perf_defconfig` | 另合并 `vendor/oplus.config`（`schgm-flash.c` 需要） |
| `PACK_METHOD` | `HotSPatch1` | 由 `pack-process` 组装工具包 |
| `KERNELSU_ENABLE` | `false` | 关掉 build-ready 里的 KSU 安装与 defconfig 写入 |
| `VFS_HYBRIDMOUNT` / `VFS_NOMOUNT` | `true` / `false` | 互斥，实际值来自 workflow 输入 |
| `BASEBAND_GUARD_ENABLE` | `true` | BBG LSM |
| `REKERNEL_ENABLE` / `DROIDSPACES_ENABLE` | `true` | 均可用开关关闭 |

## Release tag 机制（`build-release.yml`）

tag 格式 `<分支名>-v<版本>-<unix 时间戳>`，指向**本次实际编译的 commit**（由内核 job 的
`build_sha` outputs 逐层透传），只推当前这一个 tag。

> 不要为了绕过 GitHub 的 workflow 权限拒绝而在 `permissions:` 里写 `workflows: write`——
> 它不是合法作用域，写了会让整个工作流文件变成 `Invalid workflow file`。

## 与 root 分支的关系

| 分支 | root 实现 | 产物 |
|---|---|---|
| `master` | BakaSU（官方 inline hooks）+ SUSFS v2.4.0 | AnyKernel3 |
| `KSU` | backslashxx/KernelSU + **手写 SUSFS 桥接** | AnyKernel3 |
| `ReSuki_Luk` | BakaSU + NoMount（luk 树适配） | AnyKernel3 |
| `crdroid_Resuki` | BakaSU（crdroid 树，分 stage 构建） | AnyKernel3 |
| **`Pure`** | **无** | **HotSPatch1** |

## 已知限制

- 构建需要 x86_64 环境（GitHub Actions 默认 runner 即可）；
- dtb 由 `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` 拼接为 `dtb.img`（与官方 DTB_SZ 一致），dtbo 不打包；
- Pure 不含 SUSFS，因此没有路径/挂载隐藏能力；需要隐藏请用 root 分支；
- 内核与 ROM 版本必须匹配（LineageOS 23.2 / Android 16）。

## 鸣谢

- [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — 构建模板与 4.19 移植方法
- [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) / [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) / [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
- [Hybrid Mount](https://github.com/Hybrid-Mount/meta-hybrid_mount) / [NoMount](https://github.com/maxsteeel/nomount)
