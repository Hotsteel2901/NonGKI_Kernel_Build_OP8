# NonGKI_Kernel_Build_OP8

基于 [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的 sample 分支格式，
为 **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** 的 **LineageOS 23.2 (Android 16)** 内核提供自动化编译。

## 集成内容

| 组件 | 说明 |
|---|---|
| KernelSU (backslashxx) | **[backslashxx/KernelSU](https://github.com/backslashxx/KernelSU)** master, 固定 `4e6e9ff`。该分支**上游不支持 SUSFS**, 内核侧是**本仓库手写的桥接**, 不是 BakaSU 的官方 inline hook 那套。 |
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
4. 构建完成后在 **Actions → 本次运行 → Artifacts** 下载 zip。本包为 **AnyKernel3** 格式, 刷入步骤:
   - 重启到 recovery (TWRP / Lineage Recovery / crDroid Recovery)
   - **Apply update (应用更新)** → **Apply from ADB (从 ADB 应用)**, 然后执行 `adb sideload NonGKI_Kernel_<代号>_<构建号>.zip`
   - 重启进入系统
   - 仅替换内核镜像, **不会清空** `/data`; 刷入前建议**备份原厂 `boot.img`** 以便回滚
   - 本包**与 Magisk 不兼容**, 请勿与 Magisk 一起刷入
5. 安装 **[KernelSU Manager](https://github.com/tiann/KernelSU/releases)** (官方管理器, backslashxx/KernelSU 走它的协议) 并验证: root 正常, 模块可挂载, `ksu_susfs` 报告 SUSFS **2.3.0**.

> 与 `master` / `ReSuki_Luk` / `crdroid_Resuki` (BakaSU, 官方 SUSFS inline hook) 不同, 本分支跟的是
> **[backslashxx/KernelSU](https://github.com/backslashxx/KernelSU)** —— 更精简、不支持 SUSFS,
> 所以内核侧由本仓库手写桥接。

## 补丁说明 (Patches/)

| 文件 | 内容 | 应用时机 |
|---|---|---|
| `Patches/Patch/susfs_patch_to_4.19.patch` | SUSFS v2.3.0 全部内核侧代码 (susfs.c/namei/namespace/proc/statfs/mm/kallsyms/avc/cmdline 等) | patch-susfs 动作 |
| `Patches/Patch/backslashxx_manual_hooks.patch` | backslashxx 的静态调用点钩子: `ksu_handle_execveat/faccessat/stat/newfstat_ret/fstat64_ret/sys_reboot` (另含 fs/stat.c SUS_KSTAT 与 kernel/sys.c uname 伪装片段) | 工作流自定义步骤 |
| `Patches/Patch/backslashxx_susfs_bridge.patch` | SUSFS 命令分发接入 backslashxx: `ksu_handle_susfs_cmd()` / `SUSFS_MAGIC` 路由 / `susfs_init()` / sdcard 监控 / `susfs_set_current_proc_umounted()` | 工作流自定义步骤 (受 `SUSFS_ENABLE` 控制) |
| `Patches/Patch/hybridmount_patch_to_4.19.patch` | Hybrid Mount VFS 子系统 (`fs/hybridmount`, keyring 魔数 `"hm1"`) | 工作流自定义步骤 (受 `VFS_HYBRIDMOUNT` 控制) |
| *(NoMount)* | 本仓库无补丁文件, 直接拉上游 `kernel/setup.sh` | 工作流自定义步骤 (受 `VFS_NOMOUNT` 控制) |
| `Patches/RekernelX/rkx-4.19.patch` | ReKernel-X 4.19 移植 (drivers/rekernel_x/ + binder + signal + genl,自带 Kconfig/Makefile 注册) | patch-rekernel 动作 |
| `Patches/Droidspaces/*` | droidspaces.config (配置) + cgroup 前缀 cocci + xt_qtaguid panic 修复 cocci | patch-droidspaces 动作 |

> 说明: 补丁基于生成时 lineage-23.2 最新提交 (当前 `66e230426430`) 生成; 工作流使用**最新**内核源码
> (不固定 checkout), 常规偏移下 `patch -p1` 自动应用。若 LineageOS 上游更新导致 reject, 请基于新 tip 重新生成:
> ```bash
> git diff <新base> -- <susfs相关文件> > Patches/Patch/susfs_patch_to_4.19.patch
> ```
>
> ⚠️ **本分支的钩子是自己写的, 不是 BakaSU 那套。** BakaSU 官方支持 SUSFS inline hook
> (`CONFIG_KSU_SUSFS` + `inline_hook_check.mk`); backslashxx/KernelSU 两者都没有, 所以上面两份补丁
> 由本仓库维护, 上游一动就得重新对齐。
>
> `build-oneplus-8-los23-a16.yml` 里的 `KERNELSU_PIN` 把 KernelSU 钉在核对过的 SHA 上,
> 补丁与源码树永远对得上。升上游流程: 改 `KERNELSU_PIN` → 对新 SHA 重生成
> `backslashxx_susfs_bridge.patch` → 让 `🔎 Verify KernelSU hook symbols` 步骤确认每个钩子签名没变。
>
> `backslashxx_manual_hooks.patch` 要求 `sucompat.c` 的钩子保持**外部可见**, 也就是
> `CONFIG_KSU_TAMPER_SYSCALL_TABLE` 与 `CONFIG_KSU_HACK_ARM64_BRANCH_LINK` 必须都是 `n`
> (否则 `SUCOMPAT_HOOK_TYPE` 退化成 `static __always_inline`)。defconfig 步骤已把这两个钉死。

## VFS 路径重定向后端（二选一）

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

在 `build-oneplus-8-los23-a16.yml` 的 `env:` 段修改，或使用工作流暴露的
`workflow_dispatch` 输入（视具体工作流而定）。

> 两者都必须内置（`=y`）而非 `=m`：4.19 没有匹配的预编译 `.ko`
> （上游只提供 5.10/5.15/6.1/6.6/6.12 的模块）。
>
> Hybrid Mount 与 NoMount 是**同源不同家**：`fs/hybridmount` 是从 NoMount fork 出来的，
> 但重命名了符号、换了自己的 wire magic（`"HYBRIDMO"` vs `"NOMOUNT"`），
> 两者元模块与工具链**互不通用**。按你的 userspace 管理器支持哪套来选。
>
> AK3 标题行在构建时按**实际启用**的后端动态拼装，因此标题不会出现内核里其实没有的后端。
>

## Release tag 机制 (build-release.yml)

`Build and Release Kernel` 会构建内核并发布 GitHub **Release**，tag 精确标识「本次编译
所用的那个 commit」。

| 项目 | 行为 |
|---|---|
| tag 格式 | `<分支名>-v<版本>-<unix 时间戳>`，例如 `master-v35203-1791179734` |
| 冲突处理 | 该 tag 已存在时追加 `-2`、`-3`… 后缀 |
| tag 指向 | **实际构建的 commit**，由内核 job 通过 `build_sha` outputs 逐层透传（不是 release job 的 `HEAD`） |
| 推送方式 | `git push origin refs/tags/$NEW_TAG` —— **只推当前这一个 tag** |

这里有两处是刻意设计，且很容易改错：

> **加分支前缀。** 不加前缀时，同一天在别的分支（或同一分支）再跑一次就会 tag 冲突、
> release 直接失败。带上分支名后 tag 既能保证唯一，也自带出处信息。

> **只推当前 tag。** 用 `git push --tags` 会把本地历史里**所有** tag 一起推上去。
> 这些 tag 可能指向「修改过 `.github/workflows/` 的 commit」，GitHub 会以
> `refusing to allow a GitHub App to create or update workflow ... without workflows
> permission` 拒绝。只推 `refs/tags/$NEW_TAG` 就不会携带那段历史，也就不需要额外权限。
>
> ⚠️ 千万**不要**为了绕过这个拒绝而去 `permissions:` 里加 `workflows: write` ——
> `workflows` **不是合法的权限作用域**，写了会让 GitHub 把**整个工作流文件**判为
> `Invalid workflow file`，导致该分支上所有工作流全部失效。合法作用域只有：
> `actions`、`attestations`、`checks`、`contents`、`deployments`、`discussions`、
> `id-token`、`issues`、`packages`、`pages`、`pull-requests`、`repository-projects`、
> `security-events`、`statuses`。

## 关键配置项 (build-oneplus-8-los23-a16.yml)

- `KERNEL_SOURCE/Branch`: LineageOS 官方仓库 `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **必须保留** (schgm-flash.c 需要 CONFIG_OPLUS_SM8250_CHARGER)
- `VFS_HYBRIDMOUNT / VFS_NOMOUNT` — 互斥, 详见上一节
- `KERNELSU_AUTO_FORK: xxksu` + `KERNELSU_PIN: 4e6e9ff` — 取 backslashxx/KernelSU 并**钉在该 SHA**
  (手写补丁就是按它对齐的, 不钉的话补丁和源码树会对不上)
- dtb: 构建后自定义步骤拼接 `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img` (与官方 DTB_SZ 一致)
- dtbo: 不打包 (NEED_DTBO=false, 沿用系统分区的 dtbo)

## 与 Jack 原版格式的差异（有意为之）

- `patch-no-kprobe` 步骤/动作未采用: 其 `susfs_inline_hook_patches.sh` 是给 BakaSU 官方 inline hook
  用的, backslashxx 没有那套 API; 本分支改为自己的 `backslashxx_manual_hooks.patch` +
  `backslashxx_susfs_bridge.patch`; 该脚本的 selinuxfs 静态符号移除部分因本内核
  CONFIG_KALLSYMS_ALL=y 会跳过, 无实际作用
- 仅保留 4.19 版本的 susfs 补丁 (设备内核版本固定, 无需 4.4/4.9/5.4 等)
- ReKernel-X 4.19 直接用补丁集成 (内置), 替换原 Re:Kernel v8.5
- HOOK_METHOD 变量保留但无实际作用: 钩子是 backslashxx_manual_hooks.patch 里的静态调用点

## 补丁记录存档 (Patches/Archive/)

开发过程中的完整补丁记录: `0000-full-all-changes.patch` (全量合集)、
`0001-resukisu-susfs.patch` (ReSukiSU (现 BakaSU) + SUSFS v2.2.0 完整集成)、
`0001-rekernel.patch` / `0001-droidspaces-cgroup-prefix.patch` /
`0001-baseband-guard.patch` / `0001-defconfig.patch` 及 `README.md` (开发记录)。
工作流实际使用 `Patches/Patch/` 与 `Patches/Rekernel/`, Archive 仅存档。

## 已知限制

- 构建需要 x86_64 环境 (GitHub Actions 默认 runner 即可)
- SUSFS v2.3.0 的 OPEN_REDIRECT 实际重定向在 4.19 上不生效 (架构限制, 与官方一致)
- 若使用本地构建 (非 GitHub Actions), 内存 ≥ 8G 且用 `make -j2` (手机本体构建严禁 -j8)

## 鸣谢

- [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — 项目格式与 4.19 移植方法
- [BakaSU](https://github.com/Baka-SU/BakaSU) / [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) / [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) / [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) / [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
