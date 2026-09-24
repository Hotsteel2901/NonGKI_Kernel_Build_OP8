# NonGKI_Kernel_Build_OP8

基于 [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的 sample 分支格式，
为 **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** 的 **LineageOS 23.2 (Android 16)** 内核提供自动化编译。

## 集成内容

| 组件 | 说明 |
|---|---|
| ReSukiSU | KernelSU 分支, CONFIG_KSU_SUSFS (inline hook) 模式 |
| SUSFS v2.3.0 | 官方 gki v2.3.0 + JackA1ltman 实证的 4.19 适配 (i_state 标志位 / p->state=0 / 旧 fsnotify API) |
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
5. 刷入后通过 KernelSU Manager 验证: 版本显示 **SUSFS 2.3.0**, 授权/模块功能正常.

## 补丁说明 (Patches/)

| 文件 | 内容 | 应用时机 |
|---|---|---|
| `Patches/Patch/susfs_patch_to_4.19.patch` | SUSFS v2.3.0 全部内核侧代码 (susfs.c/namei/namespace/proc/statfs/mm/kallsyms/avc/cmdline 等) | patch-susfs 动作 |
| `Patches/Patch/resukisu_inline_hooks.patch` | ReSukiSU SUSFS inline 模式官方内联钩子: exec / open / read_write / stat / input / reboot / setresuid (另含 fs/stat.c SUS_KSTAT 与 kernel/sys.c uname 伪装片段) | 工作流自定义步骤 |
| `Patches/RekernelX/rkx-4.19.patch` | ReKernel-X 4.19 移植 (drivers/rekernel_x/ + binder + signal + genl,自带 Kconfig/Makefile 注册) | patch-rekernel 动作 |
| `Patches/Droidspaces/*` | droidspaces.config (配置) + cgroup 前缀 cocci + xt_qtaguid panic 修复 cocci | patch-droidspaces 动作 |

> 说明: 补丁基于生成时 lineage-23.2 最新提交 (当前 `66e230426430`) 生成; 工作流使用**最新**内核源码
> (不固定 checkout), 常规偏移下 `patch -p1` 自动应用。若 LineageOS 上游更新导致 reject, 请基于新 tip 重新生成:
> ```bash
> git diff <新base> -- <susfs相关文件> > Patches/Patch/susfs_patch_to_4.19.patch
> ```
>
> 内联钩子与 Jack 的官方 `susfs_inline_hook_patches.sh` (SUSFS v2.3.00+ 官方内联钩子) 对齐:
> 7 个钩子均通过 ReSukiSU `inline_hook_check.mk` 的编译期校验 (static_key 门控)。
> 因 4.19 的 `__do_execve_file()` 成功路径在 `out_free:` 之前提前返回, `ksu_handle_post_execveat_sucompat`
> 钩子置于 exec 成功路径 (su fd 必须在 exec 进 ksud 之后安装; 与官方 5.10 `do_execveat_common` 布局语义等价)。

## 关键配置项 (build-oneplus-8-los23-a16.yml)

- `KERNEL_SOURCE/Branch`: LineageOS 官方仓库 `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **必须保留** (schgm-flash.c 需要 CONFIG_OPLUS_SM8250_CHARGER)
- `KERNELSU_AUTO_FORK: resukisu` — 自动获取最新 ReSukiSU
- dtb: 构建后自定义步骤拼接 `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img` (与官方 DTB_SZ 一致)
- dtbo: 不打包 (NEED_DTBO=false, 沿用系统分区的 dtbo)

## 与 Jack 原版格式的差异（有意为之）

- `patch-no-kprobe` 步骤/动作未采用: 其 `susfs_inline_hook_patches.sh` 即 Jack 的官方内联钩子实现
  (SUSFS v2.3.00+, 与 ReSukiSU inline 模式兼容), 本仓库以等价内容固化为
  `resukisu_inline_hooks.patch` (保持补丁化流程、便于审查与固定应用顺序);
  该脚本的 selinuxfs 静态符号移除部分因本内核 CONFIG_KALLSYMS_ALL=y 会跳过, 无实际作用
- 仅保留 4.19 版本的 susfs 补丁 (设备内核版本固定, 无需 4.4/4.9/5.4 等)
- ReKernel-X 4.19 直接用补丁集成 (内置), 替换原 Re:Kernel v8.5
- HOOK_METHOD 变量保留但无实际作用: ReSukiSU inline 钩子由 resukisu_inline_hooks.patch 提供

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
- [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) / [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) / [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) / [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) / [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
