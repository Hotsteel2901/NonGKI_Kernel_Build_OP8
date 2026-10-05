# ReSukiSU-SUSFS Kernel Patch Archive

内核: LineageOS 23.2 (sm8250/kona) 4.19.325-cip132
Base commit: 4238ee49a84b (techpack: audio: tfa98xx-v6: Prevent node being created twice)
内核源码: ~/android_kernel_oneplus_sm8250_official
生成时间: 2026-08-05, 工作树当时状态 (git status 见 0000 头部)
更新记录:
  - 2026-08-05: ReSukiSU 88dbc786 -> 058cdc93 (12 commits, 仅 x86_64/tracepoint/用户态变化, 集成未破坏)
  - 2026-08-05: SUSFS v2.1.0 -> v2.2.0 (官方 gki-android15-6.6@be7b7ef 最新, 2026-06-21 发布),
    构建 #6 Wed Aug 5 16:56:49 UTC 2026
  - 2026-08-05: 【修复】v2.2.0 首版开不了机(黄警告屏后黑屏, recovery 正常)。回退 fs/namei.c
    到原版 (构建 #7)。根因判断: 我移植的 namei.c 查找级 SUS_PATH 隐藏(stat/open 对
    sus 路径返回 ENOENT + 假 dentry)是相对 v2.1.0 的全新行为, 在带真实 sus 配置的
    system 启动中触发异常; v2.1.0/KSUN 从未有查找级隐藏(仅 readdir/proc 列表层),
    回退后行为与已验证的 v2.1.0 一致。fs/namei.c 保持原版, 不再做任何修改。
    附带说明: susfs.c 中 susfs_fake_qstr_name/susfs_open_redirect_spoof_do_sys_openat
    仍定义但无调用方(无害); OPEN_REDIRECT 实际重定向本来就不生效。
  - 2026-08-05: 【最终决定】回退整个 SUSFS 到 v2.1.0 (wagamy/KSUN 版本), 仅保留
    ReSukiSU 更新 (058cdc93)。v2.2.0 集成(含 namei 回退后的 #7 构建)在实机上
    依然黑屏无法开机, 未定位到根因(无 pstore 日志, 崩溃极早)。重建方式:
    KSUN_SUSFS 内核提交 ac5f7e57d3f1 提取全部 v2.1.0 susfs 文件 + 5 处 ReSukiSU
    适配(见下), 构建 #8 Wed Aug 5 18:50 UTC 2026, Image 54835216 B 与用户能正常
    开机的旧 2.1.0 构建字节数完全一致。v2.2.0 不再尝试。
    教训: 4.19 上只做"列表层隐藏"的 v2.1.0 是唯一验证可用的状态;
    v2.2.0 的所有新特性 (UID_SCHEME/open_redirect 重构/2e9 mnt_id/静态键化)
    对 4.19 收益低且引入了无法定位的开机崩溃。
  - 2026-08-06: 【v2.2.0 重做 - 按 JackA1ltman 实证方法】构建 #9 Wed Aug 6 16:57 UTC 2026。
    参考 NonGKI_Kernel_Build_2nd (github.com/JackA1ltman) 的通用 susfs_patch_to_4.19.patch
    (v2.2.0 for 4.19, 15+ 设备 Stable) 重做集成:
      - 直接应用其通用 4.19 补丁 (仅 namespace.c 两个 hunk + task_mmu pagemap hunk 手工修)
      - 关键 4.19 适配: set_nameidata() 里 p->state = 0 (此前黑屏的头号嫌疑!);
        AS_FLAGS_* 存 inode->i_state (非 GKI 的 i_mapping->flags);
        fsnotify 用旧 API (SUSFS_DECL_FSNOTIFY_OPS + m_free);
        namei 层 FUSE+O_CREAT 返回 -EACCES 防护
      - namespace.c: 同 IDA 2e9 (与他们的 LOS 构建一致, 独立 IDA 声明未使用已删);
        钩 vfs_create_mount (本树 fs_context 版, 唯一分配点)
      - 保留 ReSukiSU inline 钩子 (exec/open/read_write/stat/input/reboot/setresuid),
        补回 stat.c ksu_handle_stat + reboot.c + sys.c setresuid (其补丁不含)
      - 构建内存教训: 环境跑在手机本体 (8G), 必须 -j2, 严禁 -j8 (OOM 黑屏卡死)
    若此版仍黑屏: 回退 v2.1.0 包 (build #8 存档) 或按 0001 patch 重放 v2.1.0。
  - 2026-08-06: 【修复 KSU 用户态失效】构建 #9 能开机但管理器"工作中"为假: 授权数/模块数
    全 0, 无法授权。根因: 重建时从 v2.1.0 的 exec.c 做符号替换, 把
    `if (unlikely(!susfs_is_sdcard_android_data_decrypted))` (decrypted 默认 false → 恒真)
    错写成 `if (unlikely(!static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)))`
    (not_decrypted 默认 true → 恒假) -> ksu_handle_execveat 永不执行 -> KernelSU 核心
    exec 处理 (授权/ksud/escape_to_root) 全死。构建 #10 修复为官方 v2.2.0 分支:
    `if (static_branch_unlikely(&not_decrypted)) ksu_handle_execveat; else sucompat;`
    教训: 布尔→静态键替换时注意极性反转 (decrypted=false 与 not_decrypted=true 语义等价,
    不能机械加 !)。
  - 2026-08-27: 【ReSukiSU 03b60f2 更新破坏构建 → 跟随 Jack 上游修复】ReSukiSU commit
    03b60f2 "kernel: sync with latest susfs" (2026-08-23, AlexLiuDev233 + simonpunk) 起,
    CONFIG_KSU_SUSFS 模式下改用新 SUSFS API, 导致 GitHub Actions 链接阶段失败:
      - undefined reference to `susfs_is_current_proc_no_su` / `susfs_set_current_proc_no_su`
        / `susfs_clear_current_proc_no_su` / `susfs_set_current_proc_umounted_for_zygote_next`
        (来自 ReSukiSU kernel/feature/sucompat.c + kernel/hook/setuid_hook.c)
      - ksu_handle_stat / ksu_handle_faccessat 签名由 `const char __user **` 改为
        `struct filename **` (GKI 6.6 风格); 若只补函数修好链接, 旧 inline hook 传
        `const char __user **` 会被新 handler 解引用 `(*filename)->name` 造成运行崩溃
    修复 (对齐 JackA1ltman/NonGKI_Kernel_Build_2nd mainline+sample 分支当日 23:06 提交):
      - Patches/Patch/susfs_patch_to_4.19.patch: include/linux/susfs_def.h 新增
        `TIF_PROC_NO_SU 34` / `TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT 35` 及
        susfs_clear_current_proc_umounted / zygote_next 三件套 / no_su 三件套 内联函数
        (与 Jack 逐字一致, 行数 180 -> 210)
      - Patches/Patch/resukisu_inline_hooks.patch: fs/exec.c guard 改用
        susfs_is_current_proc_no_su(); fs/open.c do_faccessat 与 fs/stat.c vfs_statx
        改用 `getname_flags() -> ksu_handle_*(&dfd,&fname,...) -> filename_lookup()` 流程
        (4.19 filename_lookup 非 static 可直接调用; fs/open.c 已含 "internal.h";
        fs/stat.c 补 `#include "internal.h"`); 原 newfstatat 旧签名 hook 移除,
        SUS_KSTAT spoofing 保留; input/read_write/reboot/sys 四节未动
    其他组件排查 (均非失败原因): DroidSpaces cocci 与上游一致; Re:Kernel 静态
    rekernel_extra.patch 与 myflavor/ReKernel-X Integrate v8.5 一致 (仅 cfg->static 与
    jobctl.h 两处既有适配); Baseband-guard 实时下载但编译通过。
  - 2026-09-05: 【ReSukiSU inline 钩子对齐最新上游】对照 ReSukiSU main (HEAD 3c18828,
    2026-09-05) 与 Jack sample (HEAD a2cf40a, 2026-09-04):
      - 符号契约核对: resukisu_inline_hooks.patch 引用的全部符号/签名仍匹配当前
        ReSukiSU main (sucompat.c/ksud_integration.c/allowlist.c/supercall.c/setuid_hook.c),
        可过 CONFIG_KSU_SUSFS 编译门禁 tools/inline_hook_check.mk
      - 对齐 Jack 新增: fs/stat.c vfs_statx_fd 处补 ksu_handle_vfs_fstat(fd,&stat->size)
        init.rc fstat 大小注入 (extern ksu_is_init_rc_hook_enabled 守卫, ReSukiSU main
        在 CONFIG_KSU_SUSFS 下导出该函数); kernel/reboot.c 的 ksu_handle_sys_reboot
        加 `if (system_state == SYSTEM_RUNNING)` 守卫
      - 不采纳: Jack 脚本 read_write.c 仍用旧 1 参 ksu_handle_sys_read(fd), 与当前
        ReSukiSU main 的 3 参导出不符, 我们保留 3 参新式
  - 2026-09-05: 【SUSFS v2.2.0 -> v2.3.0 + 优化】对照 Jack sample 12e1465 (2026-09-04,
    "susfs version code upgrade to v2.3.0", 引用 simonpunk fb16b41a) 与本仓库内容级比对:
      - include/linux/susfs.h: SUSFS_VERSION "v2.2.0" -> "v2.3.0"
      - fs/namespace.c: __lookup_mnt 补 zygote_next 进程的 sus mount 隐藏块
        (susfs_is_current_proc_umounted_for_zygote_next() 时仅返回非 sus mount,
         TIF 35 / DEFAULT_KSU_MNT_ID 此前已具备)
      - 内核源码不同注意: 我们用的 LineageOS sm8250 4.19 是 fs_context 版
        (namespace.c 钩 vfs_create_mount, 参数 fc), Jack 通用 CAF 4.19 钩
        vfs_kern_mount(name) —— fc->source vs name 差异属内核结构, 不照抄;
        namei.c 的 __lookup_hash #ifdef/#else 化仅风格差异无功能变化, 亦不采纳
      - 其余 15 文件与 Jack 逐字节一致 (fs/susfs.c 1491 行 / susfs_def.h 210 行等)
      - 补丁已基于 lineage-23.2 最新提交 d504087 (2026-09-05 tip) 重新生成并验证
        git apply --check 与 patch -p1 --dry-run 干净通过; 注意工作流当前不 pin
        内核提交, 上游若再漂移需重新生成

  - 2026-10-05: 【ZeroMount 4.19 自研移植 + 两个致命缺陷修复】
    新增第三个 VFS 后端 ZeroMount（`fs/zeromount`，`/dev/zeromount` 字符设备 + 自定义
    ioctl，不依赖 keyring），并修复移植过程中引入的两个问题：

    缺陷 1 — **补丁按 pristine 4.19 写，静默删掉 SUSFS/KSU 钩子**。
      `Patches/Patch/zeromount_patch_to_4.19.patch` 最初是照着原始上游 4.19 生成的，
      但实际内核里 `fs/stat.c` 早已被 SUSFS + BakaSU inline hooks 改过。补丁的 hunks
      把「已被打上钩子的区域」当作待替换的旧代码：
        fs/stat.c: +46 行 / -86 行
      结果 `ksu_handle_stat`、`ksu_handle_vfs_fstat`、`ksu_is_init_rc_hook_enabled`、
      SUSFS `susfs_sus_kstat_spoof_generic_fillattr` / `susfs_is_inode_sus_kstat`
      全被抹掉。**补丁应用时 0 个 .rej**，所以工作流里原有的 reject 检查完全没拦住，
      直到编译期才死在 BakaSU 的 inline_hook_check.mk：
        -- You lost ksu_handle_stat hook in your kernel
        KernelSU/kernel/tools/inline_hook_check.mk:52: *** You should integrate BakaSU
        in your kernel. . Stop.
        make[2]: *** [../scripts/Makefile.modbuiltin:55: drivers/kernelsu] Error 2
      修复: 以「SUSFS + inline hooks 之后」的真实树为基线重新生成补丁。核对每个文件
      的增删行数，确认**唯一**的破坏性文件就是 fs/stat.c（其余 9 个纯新增）；
      把 fs/stat.c 的 7 个破坏性 hunk 重写为 3 个纯新增 hunk，让两套子系统并存：
      ZeroMount 的 zeromount_stat_hook() 先跑，返回 -ENOENT 时落回未被改动的
      SUSFS filename_lookup / orig_flow: 路径。
      结果: 36 hunk -> 32 hunk，ksu_/susfs_ 删除行数 86 -> 0，四个分支统一
      md5 478e8abe69a47b9e0b5715a375ce3a74。

    缺陷 2 — **`CONFIG_ZEROMOUNT` 没有进 .config，头文件 stub 与实现冲突**。
      必须在 fs/Kconfig 的「最后一个 endmenu」之前注入 config 块，并在 fs/Makefile
      尾部追加 obj-$(CONFIG_ZEROMOUNT) += zeromount.o。这两个文件**不放进补丁**：
      它们的双后端上下文锚点无法同时兼容「有 HybridMount」与「没有 HybridMount」
      两种树（patch 的 fuzz 匹配会静默插错位置），改由工作流做文本注入。
      注意 fs/Kconfig 的文本注入必须用 `tail -1` 取**最后一个** endmenu。

    防回归 — 加了逐符号守卫。教训是 **`0 reject` 不等于打对了**，所以在
      build-oneplus-8-los23-a16.yml、build-luk-op8.yml、build-crdroid-op8.yml
      三个工作流（crdroid 有两处）的 ZeroMount 步骤里，补丁之后逐个核对 9 个符号
      （fs/stat.c 的 ksu_handle_stat / ksu_handle_vfs_fstat / ksu_is_init_rc_hook_enabled
      / susfs_sus_kstat_spoof_generic_fillattr / zeromount_stat_hook，fs/exec.c 的
      ksu_handle_execveat，fs/open.c 的 ksu_handle_faccessat，fs/read_write.c 的
      ksu_handle_sys_read，kernel/sys.c 的 ksu_handle_setresuid），少任何一个即 fail。
      已做对照实验验证：旧补丁 0 reject 但守卫立刻报错拦截。

    验证: 本地按 CI 真实顺序（SUSFS -> 清 rej/orig -> BakaSU inline hooks ->
      ZeroMount -> Kconfig/Makefile 注入）跑端到端，rej=0、9/9 钩子齐全、
      CONFIG_ZEROMOUNT=y、编译 0 错误 0 警告。另做对照实验（注入探针符号后确认其
      出现在预处理输出中）证明 CONFIG_KSU_SUSFS 分支确实被编译，排除「分支没激活
      所以看起来能过」的假阳性。
      CI 实测 run 37294291263（ZeroMount 模式）: 14m43s success，日志中 7 个
      BakaSU/susfs_inline 钩子全部 found（含 ksu_handle_stat），产出
      Kernel-instantnoodle-lineage23.2_a16-*.zip（24 MB）。

    缺陷 3 — **KSU 分支不能照抄 BakaSU 的守卫清单（实测暴露）**。
      KSU 分支与本仓其余三支**结构不同**，务必区分：
        - KSU 用 backslashxx/KernelSU（**手动补丁**），**没有官方 SUSFS 支持**，
          全部桥接（backslashxx_manual_hooks.patch + backslashxx_susfs_bridge.patch）
          都是手写的；它**完全不使用** resukisu_inline_hooks.patch。
        - KSU 把内核 pin 在 4238ee49a84bd418c8515c297563bb29f95ab40b，与其余分支
          的基线不同。
      因此两套符号集**实质不同**：
        | 符号 | BakaSU/ReSukiSU | backslashxx/KernelSU |
        |---|---|---|
        | ksu_handle_stat | ✓ | ✓ |
        | ksu_handle_vfs_fstat | ✓ | ✗ |
        | ksu_is_init_rc_hook_enabled | ✓ | ✗ |
        | ksu_handle_sys_read | ✓ | ✗ |
        | ksu_handle_setresuid | ✓ | ✗（其 setresuid 走 selinux hook）|
        | ksu_handle_newfstat_ret | ✗ | ✓ |
        | ksu_handle_fstat64_ret | ✗ | ✓ |
        | ksu_handle_sys_reboot | ✓ | ✓ |
      我最初把 BakaSU 的 9 符号清单**原样部署到了 KSU 工作流**，实测证明这会**假失败**：
      在 KSU 真实基线上 grep 那 4 个 BakaSU 专有符号，`ksu_handle_vfs_fstat` /
      `ksu_is_init_rc_hook_enabled` / `ksu_handle_sys_read` 命中 **0 个文件**，
      `ksu_handle_setresuid` 虽然存在但不在清单指定的 fs/read_write.c 里 ——
      守卫会在补丁**完全正确**的情况下报错退出。
      修复: KSU 工作流的守卫改为 KSU 专用的 8 符号清单
        fs/stat.c  : ksu_handle_stat / ksu_handle_newfstat_ret / ksu_handle_fstat64_ret
                     / susfs_sus_kstat_spoof_generic_fillattr / zeromount_stat_hook
        fs/exec.c  : ksu_handle_execveat
        fs/open.c  : ksu_handle_faccessat
        kernel/reboot.c : ksu_handle_sys_reboot
      并用 /tmp/verify_guards.py 逐分支校验「守卫引用的每个符号，该分支自己的钩子
      补丁确实提供」，四个分支全部通过。

      KSU 本地实测（在真实 baseline 4238ee49a84b、真实 KSU 顺序
      SUSFS -> manual hooks -> SUSFS bridge -> ZeroMount 下）:
        - 旧补丁: 产生 **1 个 .rej**（fs/stat.c.rej），但 ksu_handle_stat 竟然活了下来
          —— 说明「有 rej」与「钩子丢失」是两件独立的事，两边的表现都不一致，
          更印证了必须用逐符号守卫而非 rej 计数。
        - 新补丁: 0 个 .rej，8/8 KSU 钩子齐全，ksu_handle_vfs_fstat 等 BakaSU 专有
          符号正确缺席，CONFIG_ZEROMOUNT=y，fs/stat.o 与 fs/zeromount.o 编译干净。
        - 注意: 新补丁在 KSU 上带 **fuzz 1 / fuzz 2** 警告（锚点上下文与 BakaSU 不同）。
          已核对插入位置正确（zeromount_stat_hook 落在 vfs_statx 内、retry: 标签之前），
          fuzz 本身不影响正确性，但这也是守卫必须逐符号核对的原因。

  - 2026-10-05: 【Release tag 机制修正】
    build-release.yml 原先的 tag 设计有多个缺陷，导致「一天只能发一次 release」：
      - tag 命名改为带分支前缀 `<branch>-v<version>-<unix-ts>`，冲突时追加 -2/-3
      - 推送方式由 `git push --tags` 改为 `git push origin refs/tags/$NEW_TAG`，
        只推当前 tag。原方式会连带推送指向「含 .github/workflows/ 变更的 commit」的
        历史 tag，被 GitHub 以 "refusing to allow a GitHub App to create or update
        workflow ... without workflows permission" 拒绝
      - tag 目标改为实际构建的 commit（通过 build_sha outputs 从内核 job 逐层透传），
        不再指向 release job 的 HEAD
      - 补 fetch-depth: 0；删除从未被使用的死代码 LATEST_TAG
    踩坑记录: 曾试图用 `permissions: workflows: write` 绕过上面那个拒绝 —— **这是错的**。
      `workflows` 根本不是合法作用域，写入后 GitHub 把整个工作流文件判为
      `Invalid workflow file`，导致四个分支上**所有**工作流全部失效。
      合法作用域仅: actions / attestations / checks / contents / deployments /
      discussions / id-token / issues / packages / pages / pull-requests /
      repository-projects / security-events / statuses。
      离线复现方法: actionlint v1.7.7，`actionlint -oneline .github/workflows/*.yml`。

本目录内容与重放顺序（若内核更新破坏集成，按此顺序恢复）:

## 0. 先解包源码（patch 外的外部依赖）
   - KernelSU-src-full.tar.gz      -> 内核根目录解出 KernelSU/ 目录（含 .git, ReSukiSU v4.1.0-058cdc93）
        git clone 自 https://github.com/ReSukiSU-Kernel/ReSukiSU（/tmp/opencode/ReSukiSU 备份）
   - Baseband-guard-src-full.tar.gz -> /root/Baseband-guard/（vc-teahouse/Baseband-guard，已修复 tracing/Makefile 中错误 obj-y += selinux.o）
   - scmversion.hotsteel           -> 复制为内核根 .scmversion（内容: -g4238ee49a84b-hotsteel，覆盖 setlocalversion）

## 1. resukisu-susfs/0001-resukisu-susfs.patch   (14910 行)
   ReSukiSU (CONFIG_KSU_SUSFS 模式) + SUSFS v2.2.0 (4.19, 当前版本)
   来源: 官方 gitlab gki 分支 v2.2.0 源码 + JackA1ltman (NonGKI_Kernel_Build_2nd)
         通用 susfs_patch_to_4.19.patch 的 4.19 适配 (i_state/旧 fsnotify/p->state=0)
   核心 4.19 适配 (勿覆盖):
     - fs/namei.c: set_nameidata() 中 p->state = 0 (必须!);
       lookup_fast/lookup_open/__lookup_slow 假 dentry + link_path_walk 拦截 +
       do_last/lookup_last 状态位 + FUSE+O_CREAT 返回 -EACCES 防护 + OPEN_REDIRECT
       重定向 (set_nameidata 3 参 + old_dfd != -1 守卫)
     - fs/susfs.c: 所有 AS_FLAGS_* 存 inode->i_state (4.19 实证, 非 GKI 的
       i_mapping->flags); fsnotify 用旧 API (SUSFS_DECL_FSNOTIFY_OPS + m_free +
       4.18 版本分支 fsnotify_add_inode_mark); sdcard 监听用 raw_file_name 字符串
     - fs/namespace.c: 同 IDA mnt_id_ida + ida_alloc_min(DEFAULT_KSU_MNT_ID=2e9);
       钩 vfs_create_mount (本树 fs_context 版为唯一分配点, 其 LOS 版钩 vfs_kern_mount);
       static_key susfs_is_sdcard_android_data_not_decrypted
   保留的 ReSukiSU inline 钩子 (其 syscall 法补丁不含, 必须手工补回):
     - fs/stat.c: newfstatat 直连 ksu_handle_stat (CONFIG_KSU 门控)
     - kernel/sys.c: __sys_setresuid 里 ksu_handle_setresuid
     - kernel/reboot.c: ksu_handle_sys_reboot 无条件调用
     - fs/exec.c: ksu_su_compat_enabled 静态键 + susfs_is_sdcard_android_data_not_decrypted
       静态键 (sucompat 选择)
     - fs/open.c / fs/read_write.c / drivers/input/input.c: v2.1.0 静态键形式沿用
   构建注意事项: 本环境跑在手机本体 (8G 内存), 只允许 make -j2 (严禁 -j8, 会 OOM)。

## 2. rekernel/0001-rekernel.patch   (593 行)
   Re:Kernel 集成 (drivers/rekernel/: rekernel.c 333行 + rekernel.h + Kconfig + Makefile,
   drivers/android/binder.c +113, kernel/signal.c +8)
   来源: ~/ReKernel-X/Integrate/patches.sh (须在内核根目录执行; 误从 ~ 执行会在 /root 产生 stray drivers/)
   备注: rekernel.c 的 cfg 全局改 static (与 techpack VL53L1 冲突); rekernel.h 补 include/linux/sched/jobctl.h
   defconfig 部分在 5. 的 patch 中 (CONFIG_REKERNEL=y, CONFIG_REKERNEL_NETWORK=n)

## 3. droidspaces/0001-droidspaces-cgroup-prefix.patch   (16 行)
   DroidSpaces: kernel/cgroup/cgroup.c cgroup_add_file 加前缀 (对 zygote 隐藏非 cgroup 项)
   来源: ~/Droidspaces-OSS/Documentation/Kernel-Configuration.md (Non-GKI 部分)
   defconfig Non-GKI 配置在 5. (SYSVIPC/POSIX_MQUEUE/PID_NS/IPC_NS/CGROUP_DEVICE/CGROUP_PIDS/
   CGROUP_NET_PRIO/DEVTMPFS/BRIDGE_NETFILTER/NF_TABLES/NETFILTER_XT_MATCH_ADDRTYPE/USER_NS;
   xt_qtaguid 补丁不适用 - 本树无此驱动)
   注意: defconfig 原有一行 "# CONFIG_PID_NS is not set" 需改为启用。

## 4. baseband-guard/0001-baseband-guard.patch   (77 行)
   Baseband-guard LSM 集成
   包含: security/Kconfig security/Makefile (security/baseband-guard -> /root/Baseband-guard symlink)
         security/selinux/Makefile (追加 sepatch.txt 内容, ifeq CONFIG_BBG BBG_USE_DEFINE_LSM)
         security/selinux/include/objsec.h (task_security_struct 加 bbg_cred 字段)
         security/selinux/include/bbg_tracing.h (symlink -> ../../baseband-guard/tracing/tracing.h)
   依赖: 第0步解包 Baseband-guard 到 /root/Baseband-guard (symlink 目标)
   注意: 本内核已 backport DEFINE_LSM, BBG 走 BBG_USE_DEFINE_LSM 模式,
         CONFIG_LSM 必须含 baseband_guard 否则 BBG Makefile abort。
   白名单分区 (baseband_guard.h allowlist): boot init_boot vendor_boot vendor_kernel_boot dtbo
         userdata cache metadata misc vbmeta vbmeta_system vbmeta_vendor recovery (+slot后缀+zram)

## 5. defconfig/0001-defconfig.patch   (46 行)
   arch/arm64/configs/vendor/kona-perf_defconfig 全部改动:
   CONFIG_KSU=y + CONFIG_KSU_SUSFS=y (全部 SUSFS 子选项), CONFIG_REKERNEL=y (NETWORK=n),
   Non-GKI DroidSpaces 配置, CONFIG_BBG=y, CONFIG_LSM="...,bpf,baseband_guard"

## 6. 可选 VFS 后端（三选一，见仓库主 README 的 "VFS backends" 一节）
   以下三个后端都劫持同一层 VFS + 使用互不兼容的 keyring/ioctl 协议，**同时只能开一个**:

   - Hybrid Mount:  Patches/Patch/hybridmount_patch_to_4.19.patch   (默认开)
   - NoMount:       本仓库无补丁, 走上游 kernel/setup.sh
   - ZeroMount:     Patches/Patch/zeromount_patch_to_4.19.patch     (默认关, 32 hunk)

   ⚠️ 顺序要求: ZeroMount 必须排在 SUSFS + BakaSU inline hooks **之后**。
      它的基线是「SUSFS + inline hooks 之后」的树，与 SUSFS 在 fs/readdir.c /
      fs/proc/task_mmu.c / fs/stat.c 上有上下文重叠。
      该补丁必须**纯新增**: `ksu_`/`susfs_` 删除行数必须为 0。校验方法:
        grep -cE '^-.*(ksu_|susfs_)' Patches/Patch/zeromount_patch_to_4.19.patch   # 必须为 0
      工作流里另有一道逐符号守卫兜底（见本节末尾）。

   ZeroMount 的 fs/Kconfig + fs/Makefile 改动**不在补丁里**，由工作流文本注入完成
   （原因: 这两个文件的双后端上下文锚点无法同时兼容「有/无 HybridMount」两种树，
   patch 的 fuzz 匹配会静默插错位置）。注入要点:
     - fs/Kconfig: 在**最后一个** endmenu 之前插入 `config ZEROMOUNT` 块
       （必须 `grep -n '^endmenu' fs/Kconfig | tail -1`，不能取第一个）
     - fs/Makefile: 尾部追加 `obj-$(CONFIG_ZEROMOUNT)		+= zeromount.o`

   ⚠️ **`0 reject` 不等于打对了。** 曾出现过补丁 0 .rej 却静默删掉 ksu_handle_stat
      的情况，直到编译期才死在 inline_hook_check.mk。因此在补丁之后必须逐符号核对
      SUSFS/KSU 钩子仍在（3 个工作流共 4 处守卫: build-oneplus-8 x1、
      build-luk-op8 x1、build-crdroid-op8 x2）:
        fs/stat.c:ksu_handle_stat / ksu_handle_vfs_fstat / ksu_is_init_rc_hook_enabled
                  / susfs_sus_kstat_spoof_generic_fillattr / zeromount_stat_hook
        fs/exec.c:ksu_handle_execveat        fs/open.c:ksu_handle_faccessat
        fs/read_write.c:ksu_handle_sys_read  kernel/sys.c:ksu_handle_setresuid

## 7. 全量参考
   0000-full-all-changes.patch: 全部改动合集 (排除 *.bak 备份文件), 适用于整体重放/对照

## 构建命令 (重放后)
   # 1) 合并配置 (必须含 oplus 片段, 否则 schgm-flash.c 编译失败)
   scripts/kconfig/merge_config.sh -m -O /root/kout \
     arch/arm64/configs/vendor/kona-perf_defconfig arch/arm64/configs/vendor/oplus.config
   cd /root/kout && make ARCH=arm64 CC=clang CLANG_TRIPLE=aarch64-linux-gnu- \
     CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
   # 2) 构建 (在内核根目录, O=/root/kout)
   make O=/root/kout ARCH=arm64 CC=clang CLANG_TRIPLE=aarch64-linux-gnu- \
     CROSS_COMPILE=aarch64-linux-gnu- \
     KCFLAGS="-Wno-visibility -Wno-incompatible-function-pointer-types -Wno-cast-function-type-strict -Wno-deprecated-non-prototype" \
     -j8
   # 3) 产物
   Image:  /root/kout/arch/arm64/boot/Image (54835216 B, v2.1.0)
   dtb:    cat kona.dtb kona-v2.dtb kona-v2.1.dtb > dtb.img (1428199 B, 与官方 DTB_SZ 一致)
   dtbo:   kona-{instantnoodle,instantnoodlep,kebab,lemonades}-overlay.dtbo

## AK3 打包要点 (参考 ~/success-ak3/ 两个可用包)
   anykernel.sh: do.devicecheck=0, BLOCK=boot, IS_SLOT_DEVICE=auto, dump_boot+write_boot
   dtb 命名为 dtb.img; tools 为 Magisk v30.7 arm64 (busybox/magiskboot/magiskpolicy)
   最终包: /root/ReSukiSU-kernel-instantnoodle.zip

## 验证快照
   build-config.kout               : /root/kout/.config (v2.2.0 Jack 版构建 #9)
   System.map.build9-v220-jack     : v2.2.0 Jack 方法构建 #9 (含 p->state=0/i_state 适配)
   System.map.build5-v210-resukiSU-new : v2.1.0 + ReSukiSU 058cdc93 构建 #8 (可开机兜底)
   System.map.build4-v220-nonamei  : v2.2.0 namei 回退版 (#7) - 开不了机, 留档
   System.map.build3-v220          : v2.2.0 首版 (构建 #6) - 开不了机, 留档
   System.map.build2-hotsteel      : 用户可正常开机的旧 v2.1.0 构建 (#4) 备份
   kernel.release: 4.19.325-cip132-st16-perf-g4238ee49a84b-hotsteel
   最终刷机包: /root/ReSukiSU-kernel-instantnoodle.zip (Image 54837264 B, v2.2.0)
   兜底包: 旧 v2.1.0 zip 已覆盖, 需要时按 0001 patch (v2.1.0 存档在 README 历史说明) 重建

## 参考仓库
   - gitlab.com/simonpunk/susfs4ksu : 官方仓库 (/tmp/opencode/susfs4ksu 本地 clone)
     kernel-4.19 分支冻结在 v1.5.5 (2025-02-23); v2.1.0=2026-03-20, v2.2.0=2026-06-21 (仅 gki 分支)
     v2.2.0 源码位于 gki-android15-6.6@be7b7ef (kernel_patches/fs/susfs.c 等 3 文件 + 50_add_susfs patch)
   - ~/android_kernel_oneplus_sm8250_KSUN_SUSFS : wagamy 的 v2.1.0 4.19 backport 参考 (同 base 4238ee49a84b,
     KernelSU-Next v3.1.0 + SUSFS v2.1.0, squash 提交 ac5f7e57d3f1; 注意其独立 IDA 方式已被 v2.2.0 废弃)
   - ~/ReSukiSU_DOC, ~/ReKernel-X, ~/Droidspaces-OSS, ~/Baseband-guard
