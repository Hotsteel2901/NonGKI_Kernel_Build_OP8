# NonGKI_Kernel_Build_OP8

基于 [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的 sample 分支格式，
为 **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** 的 **LineageOS 23.2 (Android 16)** 内核提供自动化编译。

## 集成内容

| 组件 | 说明 |
|---|---|
| KernelSU (backslashxx) | KernelSU 分支 (`xxksu`), 手动钩子参照 [backslashxx/KernelSU#5](https://github.com/backslashxx/KernelSU/issues/5) (v2.3, exec 经 do_execveat_common); 管理器不带 SUSFS 版本检测。管理器为 **backslashxx 自有的 KernelSU Manager**（非 BakaSU Manager） |
| SUSFS v2.3.0 | 官方 gki v2.3.0 + JackA1ltman 实证的 4.19 适配 (i_state 标志位 / p->state=0 / 旧 fsnotify API) |
| Hybrid Mount VFS | `fs/hybridmount` 4.19 内置移植 (keyring 魔数 `"hm1"`), **默认开启** |
| NoMount VFS | `fs/nomount` 内置集成, 走上游 `kernel/setup.sh` (keyring 魔数 `"NOMOUNT"`), 默认关闭 |
| ReKernel-X | v9.2 4.19 移植 (内置驱动), CONFIG_REKERNEL_X=y |
| DroidSpaces | cgroup 前缀隐藏 + Non-GKI 配置 (含 USER_NS) |
| Baseband Guard | 分区写保护 LSM |

## 使用方法

1. **Fork 本仓库** 到你自己的 GitHub 账号
2. **Settings → Actions → General → Workflow permissions** 选择 `Read and write permissions`
3. 进入 **Actions** 页, 选择 `Build Kernel` 工作流, 点 **Run workflow** (或直接 push 触发)
4. 构建完成后在 **Actions → 本次运行 → Artifacts** 下载 zip, 用 AnyKernel3 方式刷入:
   - 重启到 recovery (fastboot boot recovery 或按键进入)
   - Apply update → 选择下载的 zip
   - 或 `adb sideload xxx.zip`
5. 刷入后通过 KernelSU Manager 验证: 授权/模块功能正常 (backslashxx 分支, 与官方 KernelSU 类似; SUSFS 仅内核侧, 管理器**不显示** SUSFS 版本)

## 补丁说明 (Patches/)

| 文件 | 内容 | 应用时机 |
|---|---|---|
| `Patches/Patch/susfs_patch_to_4.19.patch` | SUSFS v2.3.0 全部内核侧代码 (susfs.c/namei/namespace/proc/statfs/mm/kallsyms/avc/cmdline 等) | patch-susfs 动作 |
| `Patches/Patch/backslashxx_manual_hooks.patch` | KernelSU 手动钩子 (do_execveat_common execve/faccessat/newfstatat/newfstat-ret/sys_reboot + 32-bit, #5 v2.3) + SUSFS stat/uname spoof + `susfs_is_current_ksu_domain()` | 工作流自定义步骤 |
| `Patches/Patch/backslashxx_susfs_bridge.patch` | SUSFS↔KernelSU 桥接 (命令分发 / `susfs_init` / sdcard 监控 / umount 标记)。已对齐 master @ `1f47db46` (32657) | 工作流自定义步骤 |
| `Patches/Patch/hybridmount_patch_to_4.19.patch` | Hybrid Mount VFS 子系统 (`fs/hybridmount`, keyring 魔数 `"hm1"`) | 工作流自定义步骤 (受 `VFS_HYBRIDMOUNT` 控制) |
| *(NoMount)* | 本仓库无补丁文件, 直接拉上游 `kernel/setup.sh` | 工作流自定义步骤 (受 `VFS_NOMOUNT` 控制) |
| `Patches/Patch/zeromount_patch_to_4.19.patch` | ZeroMount VFS 子系统 (`fs/zeromount`, 自带字符设备 + ioctl 协议) | 工作流自定义步骤 (受 `VFS_ZEROMOUNT` 控制), 必须排在 SUSFS + HybridMount 之后 |
| `Patches/RekernelX/rkx-4.19.patch` | ReKernel-X 4.19 移植 (drivers/rekernel_x/ + binder + signal + genl,自带 Kconfig/Makefile 注册) | patch-rekernel 动作 |
| `Patches/Droidspaces/*` | droidspaces.config (配置) + cgroup 前缀 cocci + xt_qtaguid panic 修复 cocci | patch-droidspaces 动作 |

> 注意: 所有补丁基于内核提交 **`4238ee49a84b`** 生成。工作流会自动 `git checkout 4238ee49a84b`
> 固定该提交以保证补丁干净应用。若 LineageOS 上游有重大更新导致补丁失败, 请基于新提交重新生成补丁:
> ```bash
> git diff <新base> -- <susfs相关文件> > Patches/Patch/susfs_patch_to_4.19.patch
> ```

## VFS 路径重定向后端（三选一）

本仓库支持三种路径重定向后端。它们全部工作在**同一个 VFS 层**
（劫持 `inode_operations` / `file_operations` / `dentry_operations`），且各自使用
**互不兼容的 keyring 协议**，因此**同一时间最多只能开启一个**。同时开启会让两套驱动
争抢同一批 hook：userspace 元模块无法握手（会提示"内核不支持"），严重时直接崩溃。
上游 Hybrid Mount 的 Kconfig 里就明确写了与 NoMount 的元模块
*"not compatible with NoMount's metamodule or its tooling"*。

构建开头有一步校验：**开启超过一个会立刻 fail**，不会产出一个坏内核。

| 开关 | 后端 | 默认 | 内核侧 |
|---|---|---|---|
| `VFS_HYBRIDMOUNT` | Hybrid Mount VFS | `true` | `fs/hybridmount` (本仓库 4.19 内置移植) |
| `VFS_NOMOUNT` | NoMount VFS | `false` | `fs/nomount` (上游 `setup.sh` 集成) |
| `VFS_ZEROMOUNT` | ZeroMount VFS | `false` | `fs/zeromount` (本仓库自研 4.19 移植, SUSFS 感知) |

在 `build-oneplus-8-los23-a16.yml` 的 `env:` 段修改，或使用工作流暴露的
`workflow_dispatch` 输入（视具体工作流而定）。

> 三者都必须内置（`=y`）而非 `=m`：4.19 没有匹配的预编译 `.ko`
> （上游只提供 5.10/5.15/6.1/6.6/6.12 的模块）。
>
> Hybrid Mount 与 NoMount 是**同源不同家**：`fs/hybridmount` 是从 NoMount fork 出来的，
> 但重命名了符号、换了自己的 wire magic（`"HYBRIDMO"` vs `"NOMOUNT"`），
> 两者元模块与工具链**互不通用**。按你的 userspace 管理器支持哪套来选。
>
> AK3 标题行在构建时按**实际启用**的后端动态拼装，因此标题不会出现内核里其实没有的后端。
>
> **ZeroMount 移植说明**：上游 `Enginex0/zeromount` 只提供 5.4 / 5.10 / 5.15 / 6.1 / 6.6 / 6.12
> 的补丁，non-GKI 4.19 在它的 roadmap 里仍标着 *Planned*。本仓库的
> `Patches/Patch/zeromount_patch_to_4.19.patch` 是自研移植（12 个文件、+1962 行），
> 与 ZeroMount 5.4 原版保持 `zeromount.c` / `zeromount.h` **逐字一致**，差异只在
> 4.19 内核侧的接线：
>
> - 4.19 没有 `CONFIG_ANDROID_VENDOR_OEM_DATA` / `current->android_oem_data1`，
>   自动回落到头文件内置的 `current->journal_info` 重入标记分支；
> - 4.19 的 `SYSCALL_DEFINE3(getdents64, ...)` 只是 `ksys_getdents64()` 的壳，
>   真正的 `iterate_dir` 调用在后者里，因此 dents 注入钩子挂在 `ksys_getdents64`；
> - `vfs_getattr` / `inode_permission` / `kern_path` / `lookup_one_len` 等接口签名
>   与 5.4 完全一致，无需适配。
>
> 该补丁的**基线是「SUSFS + HybridMount 之后」的树**（不是 pristine 4.19），因为它与
> SUSFS 在 `fs/readdir.c`（SUSFS 重写了 `iterate_dir` 调用点并加 `orig_flow:` 标签）
> 和 `fs/proc/task_mmu.c`（两者都要往 `show_map_vma` 插钩子）上有大量上下文重叠。
> 工作流里 ZeroMount 步骤已排在 SUSFS / BakaSU hooks / HybridMount 之后，顺序不能调换。

## 关键配置项 (build-oneplus-8-los23-a16.yml)

- `KERNEL_SOURCE/Branch`: LineageOS 官方仓库 `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **必须保留** (schgm-flash.c 需要 CONFIG_OPLUS_SM8250_CHARGER)
- `VFS_HYBRIDMOUNT / VFS_NOMOUNT / VFS_ZEROMOUNT` — 互斥, 详见上一节
- `KERNELSU_AUTO_FORK: xxksu` — 自动获取最新 backslashxx KernelSU (master 分支)
- 补丁对齐基准: backslashxx/KernelSU master @ `1f47db46` (**KSU_VERSION=32657**)。构建时取的是
  master 最新提交而非固定该 SHA; 该值仅记录补丁最后一次对齐到的上游状态。若上游再次改动钩子接口,
  请重新生成 `backslashxx_susfs_bridge.patch`。
- dtb: 构建后自定义步骤拼接 `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img` (与官方 DTB_SZ 一致)
- dtbo: 不打包 (NEED_DTBO=false, 沿用系统分区的 dtbo)

## 与 Jack 原版格式的差异（有意为之）

- `patch-no-kprobe` 步骤/动作已移除: 其 `susfs_inline_hook_patches.sh` 面向 KSU v1.x
  bool 钩子与旧版 selinux 修改, 与 ReSukiSU inline 模式不兼容 (seccomp filter_count
  在 4.19 上由 kernel_compat.mk 条件编译排除, 无需补丁); 其 selinuxfs 静态符号移除
  部分因本内核 CONFIG_KALLSYMS_ALL=y 而跳过, 无实际作用
- 仅保留 4.19 版本的 susfs 补丁 (设备内核版本固定, 无需 4.4/4.9/5.4 等)
- ReKernel-X 4.19 直接用补丁集成 (内置), 替换原 Re:Kernel v8.5
- HOOK_METHOD 变量保留但无实际作用: 手动钩子由 backslashxx_manual_hooks.patch 提供 (backslashxx 模式);
  `CONFIG_KSU_HACK_ARM64_BRANCH_LINK` / `CONFIG_KSU_TAMPER_SYSCALL_TABLE` 均保持关闭, KSU 走手动钩子 + LSM
- backslashxx 的 Kconfig 没有 `CONFIG_KSU_SUSFS*` 定义; 孤儿配置符号会被 `olddefconfig` 丢弃,
  因此工作流会把 SUSFS 的 Kconfig 块追加到 `drivers/kernelsu/Kconfig` (见 "Add SUSFS Kconfig definitions" 步骤)。
  `backslashxx_manual_hooks.patch` 还补了 `susfs_is_current_ksu_domain()` (backslashxx 缺失),
  使未改动的 SUSFS 4.19 补丁能链接到此分支。
- SUSFS 还需要 KernelSU 分支在 `ksu_susfs` 用户态工具与 `fs/susfs.c` 之间做桥接。
  master 分支的 ReSukiSU 内建了这套桥接; **backslashxx 完全没有** (所以工具的 sys_reboot(SUSFS_MAGIC)
  调用无人处理, SUSFS 形同虚设)。`backslashxx_susfs_bridge.patch` 参照 ReSukiSU 把缺失部分移植进
  backslashxx 源码:
  - `supercall/dispatch.c` 新增 `ksu_handle_susfs_cmd()` (把 `CMD_SUSFS_*` 全部转发到 `fs/susfs.c`),
    整体以 `#ifdef CONFIG_KSU_SUSFS` 包裹并与 ReSukiSU 保持一致
  - `supercall/supercall.c` 的 `ksu_handle_sys_reboot()` 新增 `SUSFS_MAGIC` 路由, 并补充
    `ksu_handle_susfs_cmd` 的 extern 声明; 分发时打印 `sys_reboot: SUSFS cmd dispatch: ...` 便于 `dmesg` 排障
  - `ksu.c` 的 `kernelsu_init()` 调用 `susfs_init()` (同时引入 `<linux/susfs.h>` 与 `<linux/susfs_def.h>`)
  - `supercall/dispatch.c` 在 boot completed 时调用 `susfs_start_sdcard_monitor_fn()`
  - `feature/kernel_umount.c` 的 `ksu_handle_umount()` 调用 `susfs_set_current_proc_umounted()`
    (使 sus_path 隐藏对 umount 应用生效)
  工作流在打补丁后还会校验: 若存在 `.rej/.orig` 或源码中找不到分发符号, 构建直接失败, 避免静默产出坏包。

## 补丁记录存档 (Patches/Archive/)

开发过程中的完整补丁记录: `0000-full-all-changes.patch` (全量合集)、
`0001-resukisu-susfs.patch` (ReSukiSU+SUSFS v2.2.0 完整集成)、
`0001-rekernel.patch` / `0001-droidspaces-cgroup-prefix.patch` /
`0001-baseband-guard.patch` / `0001-defconfig.patch` 及 `README.md` (开发记录)。
工作流实际使用 `Patches/Patch/` 与 `Patches/Rekernel/`, Archive 仅存档。

## 已知限制

- 构建需要 x86_64 环境 (GitHub Actions 默认 runner 即可)
- SUSFS v2.3.0 的 OPEN_REDIRECT 实际重定向在 4.19 上不生效 (架构限制, 与官方一致)
- 若使用本地构建 (非 GitHub Actions), 内存 ≥ 8G 且用 `make -j2` (手机本体构建严禁 -j8)

## 鸣谢

- [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — 项目格式与 4.19 移植方法
- [backslashxx/KernelSU](https://github.com/backslashxx/KernelSU) / [BakaSU](https://github.com/Baka-SU/BakaSU) (原 ReSukiSU; 本分支参考其 SUSFS 集成) / [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) / [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) / [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) / [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
