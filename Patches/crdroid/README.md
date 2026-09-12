# crdroid 分支 — OnePlus 8 crDroid 内核定制

本分支为 **crDroid OnePlus 8 内核**（`crdroidandroid/android_kernel_oneplus_sm8250` @ `16.0`）
提供 ReSukiSU / SUSFS / DroidSpaces 集成补丁与独占构建工作流。

> **隔离声明**：本分支只新增文件，不改动 `master` / `KSU` / `KSU_update` 三个分支的任何内容。
> 原有 LineageOS 工作流与 10 个 composite action 保持原样。

## 目标内核

| 项目 | 值 |
|---|---|
| 仓库 | `crdroidandroid/android_kernel_oneplus_sm8250` |
| 分支 | `16.0`（Android 16） |
| 内核版本 | 4.19.325-cip135 |
| 本地验证基准提交 | `d5040872497a4d33a1e2a24cd613213087bdbeb4` |
| 设备 | OnePlus 8 (`instantnoodle`, sm8250/kona) |

**关键前提**：crDroid 的 `16.0` 分支与 LineageOS 树同源（HEAD 同为 `d504087`），
因此本项目在 LineageOS 上验证过的补丁可零改动复用。

## 集成组件与构建阶段

工作流用 `stage` 参数**循序渐进**控制，每个 stage 都经过本地完整编译验证：

| Stage | 组件 | 本地验证结果 |
|---|---|---|
| `stage1` | ReSukiSU（manual hook 模式） | ✅ Image **54,820,880 B**，0 错误，30 个 ksu 符号 |
| `stage2` | + SUSFS v2.3.0 | ✅ Image **54,824,976 B**，0 错误，64 个 susfs 符号 |
| `stage3` | + DroidSpaces | ✅ Image **54,845,456 B**，0 错误，dtb.img **1,428,199 B** |

> `dtb.img` 字节数与参考项目记录完全一致（1428199），可作为正确性佐证。

## 补丁清单（`Patches/crdroid/`）

| 文件 | 内容 | 行数 |
|---|---|---|
| `0001-stage1-resukisu.patch` | ReSukiSU inline hooks（8 文件）+ defconfig + Makefile/Kconfig 接线 | 433 |
| `0002-stage2-susfs.patch` | SUSFS v2.3.0 全部内核侧代码（17 文件） | 2066 |
| `0003-stage3-droidspaces.patch` | cgroup 前缀隐藏 + droidspaces.config | 16 |
| `droidspaces.config` | DroidSpaces Non-GKI 内核配置（含 USER_NS 等） | 98 |
| `fix_restore_cgroup_file_prefix_handling.cocci` | cgroup.c 补 `kernfs_create_link` 前缀链接 | 16 |

## 本地验证过程中修复的三个关键问题

这三个问题在参考项目（LineageOS）中不存在，是本分支针对 **当前 ReSukiSU main** 新增的适配：

### 1. TP hooks 与 Non-GKI 不兼容
```
drivers/kernelsu/Kbuild:171: *** TP hooks are incompatible with Non-GKI/GKI 1.0 kernels.
```
ReSukiSU 有三种钩子模式，默认落到 `CONFIG_KSU_TRACEPOINT_HOOK`（仅支持 GKI 2.0）。
Non-GKI 必须显式启用 manual hook：
- Stage1：加 `CONFIG_KSU_MANUAL_HOOK=y`
- Stage2/3：走 `CONFIG_KSU_SUSFS=y` 的 inline hook 分支

### 2. 门禁新增 `ksu_handle_newfstat_ret` / `ksu_handle_fstat64_ret` 要求
当前 ReSukiSU 的 `tools/manual_hook_check.mk` 额外要求这两个钩子出现在 `fs/stat.c`，
而参考项目的补丁基于旧版（当时无此检查）。已在 `SYSCALL_DEFINE2(newfstat)` 与
`SYSCALL_DEFINE2(fstat64)` 返回前补上钩子调用。

### 3. 钩子守卫条件冲突（最隐蔽的一个）
- `ksu_handle_newfstat_ret` / `ksu_handle_fstat64_ret` **只在 `CONFIG_KSU_MANUAL_HOOK` 下定义**
- `ksu_is_init_rc_hook_enabled` **只在 `CONFIG_KSU_SUSFS` 下定义**

若统一用 `CONFIG_KSU` 守卫，两种模式下各会有一处 `undefined reference`。
正确做法是**按符号实际定义条件分别守卫**：
- `fs/stat.c` 的两处调用 → `#ifdef CONFIG_KSU_MANUAL_HOOK`
- `fs/read_write.c` 的 `ksu_is_init_rc_hook_enabled` → `#ifdef CONFIG_KSU_SUSFS`
- `fs/stat.c` 的 `ksu_handle_vfs_fstat` → `#ifdef CONFIG_KSU_SUSFS`（原有）

> 构建时若看到 `WARNING: Detected KSU_MANUAL_HOOK guard in ../fs/stat.c` 属**预期正常**，
> 这是 SUSFS inline 模式门禁认出我们的守卫，不影响构建。

## 环境依赖（本地验证实测）

```bash
# 系统包
apt install -y flex bison libssl-dev libelf-dev device-tree-compiler \
  ccache cpio rsync zip unzip bc python3 coccinelle \
  gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
  gcc-arm-linux-gnueabi binutils-arm-linux-gnueabi

# 工具链: clang 19 + lld 19 (Ubuntu 24.04 自带 19.1.1, 或 LLVM 19.1.7 prebuilt)
```

## 构建命令（本地复现）

```bash
cd device_kernel
export PATH=/opt/llvm/bin:$PATH
MAKE_OPTS="ARCH=arm64 CC=ccache clang LLVM=1 LLVM_IAS=0"

make O=out $MAKE_OPTS CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu- \
  vendor/kona-perf_defconfig
./scripts/kconfig/merge_config.sh -O out/ -m out/.config arch/arm64/configs/vendor/oplus.config
# stage3 追加: ./scripts/kconfig/merge_config.sh -O out/ -m out/.config arch/arm64/configs/droidspaces.config
make O=out $MAKE_OPTS CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -j$(nproc) O=out $MAKE_OPTS CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu-
```

**产物**：`out/arch/arm64/boot/Image`
**dtb**：`cat kona.dtb kona-v2.dtb kona-v2.1.dtb > dtb.img`

> ⚠️ `vendor/oplus.config` **必须合并**，否则 `schgm-flash.c` 缺
> `CONFIG_OPLUS_SM8250_CHARGER` 会编译失败。

## 已知限制

- SUSFS v2.3.0 的 `OPEN_REDIRECT` 实际重定向在 4.19 上不生效（架构限制，与官方一致）
- SUSFS 与 DroidSpaces 共存时上游有兼容性警告，本分支 stage3 已验证可正常编译
- ReSukiSU 固定提交 `fa1da13`。若需升级，务必重新核对符号契约与门禁要求
- 工作流 `kernel_ref` 留空则用 `16.0` 分支最新提交；上游漂移可能导致补丁 `.rej`

## 触发方式

Actions → **Build crDroid OnePlus 8 Kernel (ReSukiSU + SUSFS + DroidSpaces)** → Run workflow

选择 `stage`：
- `stage1` = 仅 ReSukiSU
- `stage2` = ReSukiSU + SUSFS
- `stage3` = 全部三个组件（推荐）

产物为 AnyKernel3 刷机包，按名称区分 stage。
