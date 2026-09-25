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

- **`CONFIG_MODULE_SIG_FORCE` 必须关闭** (见下方"OOS 兼容性修复"): luk 原厂
  defconfig 带 `CONFIG_MODULE_SIG_FORCE=y`, 会强制校验所有模块签名。OOS 的
  `vendor_dlkm` / `system_dlkm` 里的 `.ko` 由一加官方私钥签名, 与本内核构建
  密钥不同, 一旦强制校验将**全部拒绝加载**。这与"vendor 分区没有内核模块"
  是两回事 —— luk 的 `oplus.config` 本身就有 `=m` 的项 (如
  `CONFIG_OPLUS_FEATURE_WIFI_ROUTERBOOST=m`), OOS 侧正是在系统分区里加载这些
  `.ko`。本分支通过 `susfs.config` 显式关闭 FORCE (保留 `CONFIG_MODULE_SIG=y`,
  模块仍带签名, 只是不强制校验)
- ReSukiSU 以内建 (builtin) 方式编入内核, 不依赖模块加载
- dtb: 构建后拼接 `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img` (与官方一致);
  dtbo 不打包, 沿用系统分区的 dtbo (自定义 ROM / OOS 均是如此)
- **模块策略**: 本工作流默认只替换 kernel (`Image` + `dtb.img`), 不覆盖系统分区里
  的原厂 `.ko` —— 两个系统都沿用各自已有的模块, 这也是"同一产物双系统通用"的前提。
  若本次配置确实产生了模块, 会一并打进 zip 的 `modules/` 目录并在日志中列出

## OOS 兼容性修复 (2026-09)

> 背景: OOS 用户刷入后能正常开机并取得 root, 但反馈 "missing that whole
> opensource driver" / "wifi not work"。

**根因**: `Patches/luk/susfs.config` 曾含一行

```
CONFIG_OPLUS_FEATURE_WIFI_ROUTERBOOST=y
```

而 luk 原厂 `arch/arm64/configs/vendor/oplus.config:51` 的值是 `=m`。

`merge_config.sh` 按命令行顺序合并, 后合并的片段覆盖先前的:

```
kona-perf_defconfig  →  vendor/oplus.config (=m)  →  susfs.config (=y)  →  olddefconfig
                                                          ↑ 这里把 m 覆盖成了 y
```

`net/Makefile:98` 是 `obj-$(CONFIG_OPLUS_FEATURE_WIFI_ROUTERBOOST) += oplus_connectivity_routerboost/`,
于是构建行为从

| 配置 | Kbuild 行为 | 产物 |
|---|---|---|
| `=m` (原厂) | `obj-m := oplus_connectivity_routerboost.o` | `oplus_connectivity_routerboost.ko` |
| `=y` (被覆盖) | `obj-y := oplus_connectivity_routerboost/` | 链接进 `built-in.o`, **不产生 .ko** |

OOS 的 userspace 仍按原厂路径加载 `oplus_connectivity_routerboost.ko`, 但该文件
已不存在 → 加载失败 → 相关网络加速特性失效。

**修复**:

1. 删除 `susfs.config` 中的 `CONFIG_OPLUS_FEATURE_WIFI_ROUTERBOOST=y`, 恢复原厂 `=m`
2. 在 `susfs.config` 中显式 `# CONFIG_MODULE_SIG_FORCE is not set`, 使 OOS 原厂
   已签名模块可以加载
3. 工作流新增**配置漂移守卫**: 构建前断言 `CONFIG_OPLUS_FEATURE_WIFI_ROUTERBOOST=m`
   且 `CONFIG_MODULE_SIG_FORCE` 未启用, 任一不符即 fail, 避免同类静默覆盖再次发生
4. `Verify` 步骤新增 OOS 兼容性断言 (`built-in.o` 不存在 / 模块签名策略正确)

### 关于"vendor/qcom/opensource 三个目录缺失"

此说法经核对**不成立**。luk 树 (`bc6f3fcb9`) 实际情况:

| 目录 | luk 树状态 |
|---|---|
| `drivers/staging/qcacld-3.0` | ✅ 存在 (830 文件) |
| `drivers/staging/qca-wifi-host-cmn` | ✅ 存在 (905 文件) |
| `drivers/staging/fw-api` | ✅ 存在 (3355 文件) |
| `techpack/audio` | ✅ 存在 (494 文件) |

- `drivers/staging/utils` 在 luk 树中**本就不需要**: sm8350 (msm-5.4) 的 manifest
  把 wlan `utils` 软链到 `staging/utils`, 而 luk 的 `qcacld-3.0/Kbuild` 引用的是
  `$(WLAN_COMMON_ROOT)/utils/...`, 即 `qca-wifi-host-cmn/utils/`, 该目录及其全部
  子目录 (`host_diag_log` / `epping` / `sys` / `nlink` / `logging`) 均存在
- audio 走 `techpack/audio` (由 `techpack/Kbuild` 自动纳入构建) 而非
  `drivers/staging/audio-kernel`, 两者是不同世代的驱动布局
- 参考 manifest (`fatalcoder524/OP9_KSUN_SUSFS`) 用的是 `<linkfile>`, 即从外部
  仓库**软链**, 并非 merge; 且其面向 sm8350/msm-5.4, 路径假设不能直接套用 sm8250/luk

## 补丁清单 (`Patches/luk/`)


| 文件 | 内容 | 行数 |
|---|---|---|
| `0001-resukisu-inline-hooks.patch` | ReSukiSU SUSFS inline 模式官方 7 个内联钩子 (exec / open / read_write / stat / input / reboot / setresuid) + fs/stat.c 的 SUS_KSTAT 片段 + kernel/sys.c uname 伪装片段 | 401 |
| `0002-susfs-v2.3.0.patch` | SUSFS v2.3.0 全部内核侧代码 (18 个文件: `fs/susfs.c`、`include/linux/susfs.h`、`susfs_def.h`、namei/namespace/proc/statfs/mm/kallsyms/avc/cmdline 等) | 4184 |
| `0003-netprio-cgroup-css-id.patch` | 修复 luk 树 `net_prio` 使用 `css->cgroup->id` (该树 `struct cgroup` 无 `id` 成员) → `css->id`, 5 处; 仅当 DroidSpaces 打开 `CONFIG_CGROUP_NET_PRIO` 时需要 | 54 |
| `susfs.config` | KSU + SUSFS 编译开关 (merge_config 片段); 同时负责关闭 `CONFIG_MODULE_SIG_FORCE` 以保证 OOS 原厂模块可加载 | 40 |
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