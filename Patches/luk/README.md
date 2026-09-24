# ReSuki_Luk 分支 — OnePlus 8 luk 内核 (自定义 ROM + OOS 双兼容)

本分支为 **luk1337/android_kernel_oneplus_sm8250** 的 **`luk`** 分支 (4.19.325) 提供
ReSukiSU / SUSFS 集成补丁与独占构建工作流。

> **隔离声明**: 本分支只新增文件 (`Patches/luk/*`、`.github/workflows/build-luk-op8.yml`
> 及 README 章节), 不改动仓库中原有的 LineageOS 工作流与 composite action,
> 也不影响 `master` / `KSU` 分支的运行。

## 目标内核

| 项目 | 值 |
|---|---|
| 仓库 | `luk1337/android_kernel_oneplus_sm8250` |
| 分支 | `luk` |
| 内核版本 | 4.19.325 (含 CIP / MGLRU 等 OPLUS 上游合并) |
| 本地验证基准提交 | `bc6f3fcb9` |
| 设备 | OnePlus 8 (`instantnoodle`, sm8250/kona) |
| root 实现 | ReSukiSU (v4.2.0-rc3 系列), `CONFIG_KSU_SUSFS` inline hook 模式 |
| 工作流 | `.github/workflows/build-luk-op8.yml` (`Build luk Kernel`) |

## 双系统兼容 (自定义 ROM + OOS)

luk 分支与 LineageOS 树的关键区别: 它**保留了 OPLUS/OOS 的完整内核配置**
(`arch/arm64/configs/vendor/oplus.config`, 含 60+ 个 `CONFIG_OPLUS_*` 开关与
`CONFIG_OPLUS_FEATURE_SAUPWK` / `CONFIG_OPLUS_FEATURE_CMDLINE` /
`CONFIG_OPLUS_SM8250_CHARGER` 等), 而 LineageOS 树的 oplus.config 已裁剪到最小集。

因此构建流程固定为:

1. `vendor/kona-perf_defconfig` — 使用 luk 自带 defconfig
2. 合并 `vendor/oplus.config` — OOS 侧驱动/特性完整保留
3. 仅追加 ReSukiSU/SUSFS 开关 (`Patches/luk/susfs.config`) 与可选 DroidSpaces 配置

产物为 **同一份 Image + dtb.img**, AnyKernel3 刷入即可, 自定义 ROM 与 OOS 通用。

补充说明:

- luk 的 defconfig 中 `CONFIG_MODULE_SIG=y` + `CONFIG_MODULE_SIG_FORCE=y` **保持不动**:
  OnePlus 8 的 vendor 分区没有内核模块 (LineageOS 专有文件清单中无任何 `.ko`,
  WLAN 等全部内建 `=y`), 模块签名校验不影响两个系统的启动
- ReSukiSU 以内建 (builtin) 方式编入内核, 不依赖模块加载
- dtb: 构建后拼接 `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img` (与官方一致);
  dtbo 不打包, 沿用系统分区的 dtbo (自定义 ROM / OOS 均是如此)

## 补丁清单 (`Patches/luk/`)

| 文件 | 内容 | 行数 |
|---|---|---|
| `0001-resukisu-inline-hooks.patch` | ReSukiSU SUSFS inline 模式官方 7 个内联钩子 (exec / open / read_write / stat / input / reboot / setresuid) + fs/stat.c 的 SUS_KSTAT 片段 + kernel/sys.c uname 伪装片段 | 401 |
| `0002-susfs-v2.3.0.patch` | SUSFS v2.3.0 全部内核侧代码 (18 个文件: `fs/susfs.c`、`include/linux/susfs.h`、`susfs_def.h`、namei/namespace/proc/statfs/mm/kallsyms/avc/cmdline 等) | 4184 |
| `0003-netprio-cgroup-css-id.patch` | 修复 luk 树 `net_prio` 使用 `css->cgroup->id` (该树 `struct cgroup` 无 `id` 成员) → `css->id`, 5 处; 仅当 DroidSpaces 打开 `CONFIG_CGROUP_NET_PRIO` 时需要 | 54 |
| `susfs.config` | KSU + SUSFS 编译开关 (merge_config 片段) | 26 |
| `droidspaces.config` | DroidSpaces Non-GKI 配置 (USER_NS / PID_NS / netns 等), 工作流可选启用 | 98 |
| `fix_restore_cgroup_file_prefix_handling.cocci` | cgroup.c 补 `kernfs_create_link` 前缀链接 (DroidSpaces 用) | 16 |

> 补丁基于 luk 提交 **`bc6f3fcb9`** 生成; 工作流默认使用分支最新源码
> (可用 `kernel_ref` 输入固定到该提交), 常规偏移下 `patch -p1` 自动应用。
> 若 luk 上游更新导致 reject, 重新生成:
> ```bash
> git diff <新base> -- drivers/input/input.c fs/exec.c fs/open.c fs/read_write.c fs/stat.c \
>   kernel/reboot.c kernel/sys.c > Patches/luk/0001-resukisu-inline-hooks.patch
> git diff <新base> -- fs include/linux/susfs.h include/linux/susfs_def.h kernel/kallsyms.c \
>   mm/memory.c security/selinux/avc.c > Patches/luk/0002-susfs-v2.3.0.patch
> ```

## 为什么需要单独适配 (与 LineageOS 树的差异)

luk 树与 LineageOS `lineage-23.2` 树**不同源**, 直接套用本仓库 LineageOS 补丁会出现:

| 文件 | luk 树差异 | 处理 |
|---|---|---|
| `drivers/input/input.c` | 含 `OPLUS_FEATURE_SAUPWK` 条件代码块 (在 `input_handle_event()` 内) | 钩子重定位: `extern` 声明置于 OPLUS weak extern 之后; 钩子调用置于 `disposition` 计算之后、OPLUS 块**之前** (该钩子只读 `type/code/value`, 与 OPLUS 转发无顺序依赖) |
| `fs/exec.c` | 含 MGLRU (`lru_gen_add_mm/use_mm`), 行号整体偏移 | 上下文匹配, 补丁自动适配; post-execveat 钩子仍在成功路径 `task_numa_free()` 之后 |
| `fs/open.c` | 较老基线 (无 `close_range`, `vfs_tmpfile` 无 `IS_ERR` 检查) | 上下文匹配, 无冲突 |
| `fs/read_write.c` | 无 `vfs_iocb_iter_read` 等新 helper | 上下文匹配, 无冲突 |
| `mm/memory.c` | 含 MGLRU, 行号偏移 49 行 | 上下文匹配 (`__access_remote_vm` 中 SUS_MAP 检查位置正确) |

## 本地验证流程与结果

环境: clang 18 + LLVM=1 + LLVM_IAS=0 + GNU binutils (aarch64), ccache 加速。

| 检查项 | 结果 |
|---|---|
| 补丁应用 (纯净 luk 树, `patch -p1`) | 0001: 7 文件 0 reject; 0002: 18 文件 0 reject (若干 hunk 带偏移) |
| ReSukiSU 编译期钩子校验 (`inline_hook_check.mk`) | 7/7 通过: setresuid / execveat / faccessat / sys_read / stat / sys_reboot / input |
| SUSFS 版本识别 | `SUSFS_VERSION: v2.3.0` (`kernel/Kbuild` 自动读取) |
| KSU 内核类型判定 | `KERNEL_TYPE: Non-GKI`, `using SuSFS Inline hook` |
| 完整编译 (stage1: ReSukiSU+SUSFS) | 见下方"构建产物" |
| 完整编译 (stage2: +DroidSpaces) | 见下方"构建产物" |

### 构建产物

| 阶段 | 产物 | 结果 |
|---|---|---|
| stage1 (ReSukiSU + SUSFS v2.3.0) | `out/arch/arm64/boot/Image` (56.5 MB) + `dtb.img` (1.53 MB) | BUILD_EXIT=0, 0 error |
| stage2 (+ DroidSpaces 配置 + cgroup 前缀补丁 + netprio 修复) | `out/arch/arm64/boot/Image` (58.6 MB) + `dtb.img` (1.53 MB) | BUILD_EXIT=0, 0 error |

关键校验 (stage2 最终编译日志):

```
-- KERNEL_TYPE: Non-GKI
-- ReSukiSU: using SuSFS Inline hook
-- SUSFS_VERSION: v2.3.0
```

符号表校验 (`nm out/vmlinux`):

| 符号 | 命中 |
|---|---|
| `ksu_handle_execveat` | 1 |
| `ksu_handle_input_handle_event` | 1 |
| `ksu_handle_stat` | 1 |
| `ksu_handle_setresuid` | 1 |
| `susfs_init` | 1 |

配置校验 (`out/.config`): `CONFIG_KSU=y`、`CONFIG_KSU_SUSFS=y`、
`CONFIG_USER_NS=y`、`CONFIG_PID_NS=y`、`CONFIG_NET_NS=y`、
`CONFIG_CGROUP_NET_PRIO=y`、`CONFIG_OPLUS_FEATURE_WIFI_ROUTERBOOST=y` 全部生效。

## 未集成项 (有意为之)

- **ReKernel-X**: 其 4.19 移植补丁直接改写 `drivers/android/binder.c` / `kernel/signal.c`,
  在 luk 树上有 4 处 hunk 冲突 (binder 代码基线不同), 需要重写补丁; 本分支暂不集成
- **Baseband Guard**: 上游 `setup.sh` 方式集成, 与 luk 树无冲突, 如需可后续按需追加
- SUSFS 的 OPEN_REDIRECT 实际重定向在 4.19 上不生效 (架构限制, 与官方一致)

## 已知限制

- luk 分支的 `CONFIG_CC_WERROR=y` 会保留: 上游 CI 使用 clang 19.1.7; 若本地
  用更老的 clang 编译遇到新 warning 报错, 属工具链差异, 不影响 GitHub Actions 构建
- DroidSpaces 与 SUSFS 同时启用时, 上游提示可能影响 DroidSpaces 部分功能
  (`enable_droidspaces` 输入可关闭)