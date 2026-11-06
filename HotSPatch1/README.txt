================================================================
 HotSPatch1  —  boot.img 内核替换工具
================================================================

这是什么？
----------
本压缩包是 Pure 内核的发布包（不是 AnyKernel3 刷机包）。
它不依赖 recovery / Magisk / KernelSU，只做一件事：

    把你的 boot.img 里的 kernel 换成包内的新内核，
    生成一个新的 boot-patched.img，供 fastboot 刷入。

适用于 OnePlus 8 (instantnoodle, sm8250) 的 Android boot
header v0 / v1 / v2 镜像。GKI 的 v3 / v4 会明确报错，不会产出坏包。


使用步骤
--------
1. 解压本压缩包到一个文件夹（路径不要有中文也可以，但建议纯英文）。

2. 把你的原机 boot.img 放进这个文件夹。
   - 文件名建议就用 boot.img；
   - 如果目录里只有一个 .img 文件，脚本会自动识别，不必改名。

3. 执行替换：

   Linux / macOS:
       chmod +x patch.sh
       ./patch.sh

   Windows:
       双击 patch.bat

4. 成功后同目录会生成  boot-patched.img

5. 刷入（手机已解锁 bootloader，且已安装 platform-tools）:

       adb reboot bootloader
       fastboot flash boot boot-patched.img
       fastboot reboot

   注意：刷的是 boot 分区。不要刷到 init_boot（本机没有该分区）。


回滚
----
刷回你原来的镜像即可：

       fastboot flash boot boot.img

所以：千万不要删掉原始 boot.img，也不要拿它覆盖输出文件
（脚本会拒绝覆盖原始文件）。


包里有什么？
------------
    kernel          编译好的内核（Image.gz-dtb 或 Image）
    boot_patch.py   替换逻辑（纯 Python 标准库，无第三方依赖）
    patch.sh        Linux / macOS 启动脚本
    patch.bat       Windows 启动脚本
    README.txt      本说明


原理与保证
----------
- 只替换 boot.img 的 kernel 段；
- ramdisk / second / recovery_dtbo / dtb / cmdline / 地址字段全部原样保留；
- 按原镜像的 page_size 重新对齐，自动重算 header 的 SHA1 id；
- 若原镜像带 AVB footer，会剥离（改动 kernel 后原签名必然失效）。


常见问题
--------
Q: 提示 "header v3/v4 (GKI 格式)"？
A: 你的 boot.img 是 GKI 格式，本工具不支持。请换用对应机型的
   magiskboot / mkbootimg 流程。

Q: Windows 提示找不到 Python？
A: 安装 Python 3 并勾选 "Add Python to PATH"，或改用 WSL 执行
   ./patch.sh。

Q: 刷完开不了机？
A: 长按电源+音量下进 fastboot，刷回原始 boot.img。内核与 ROM
   版本必须匹配（本内核面向 LineageOS 23.2 / Android 16）。
   首次开机较慢，请等待 5-10 分钟再判断。

Q: 能不能直接刷这个 zip？
A: 不能。解压后按上面步骤操作；它不是 recovery 刷机包。


内核信息
--------
集成: Re:Kernel-X + DroidSpaces + Baseband Guard
      + NoMount VFS / Hybrid Mount VFS（二选一）
无 root 实现：不包含 KernelSU / BakaSU / SUSFS，
可用 Apatch / Magisk 自行修补本内核。
================================================================
