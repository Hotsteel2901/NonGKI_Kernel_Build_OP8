#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HotSPatch1 - Android boot.img kernel 替换工具
==============================================

用途:
    把一个编译好的内核 (kernel / Image.gz-dtb / Image.gz / Image) 替换进
    现有的 boot.img，输出可直接 fastboot 刷入的新 boot 镜像。

支持:
    - Android boot image header v0 / v1 / v2 (非 GKI，含 OnePlus 8 / sm8250)
    - 自动识别页大小、保留 ramdisk / second / recovery_dtbo / dtb / cmdline
    - 自动重算 header 的 SHA1 id
    - 检测并剥离失效的 AVB footer (重打包后原签名必然失效)

不支持:
    - header v3 / v4 (GKI boot.img)，遇到会明确报错退出，不会产出坏镜像

用法:
    python3 boot_patch.py                    # 自动找 boot.img + kernel
    python3 boot_patch.py --boot boot.img --kernel kernel -o new-boot.img
    python3 boot_patch.py --verify new-boot.img --kernel kernel
"""

import argparse
import hashlib
import os
import struct
import sys

BOOT_MAGIC = b"ANDROID!"
AVB_MAGIC = b"AVBf"
VENDOR_BOOT_MAGIC = b"VNDRBOOT"

# header 结构大小 (不含第一页剩余 padding)
HDR_V0_SIZE = 1632
HDR_V1_SIZE = 1648
HDR_V2_SIZE = 1660


class PatchError(Exception):
    pass


def align(value, page_size):
    """向上对齐到 page_size 的整数倍。"""
    if page_size <= 0:
        raise PatchError("page_size 非法: %d" % page_size)
    return (value + page_size - 1) // page_size * page_size


def u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def u64(buf, off):
    return struct.unpack_from("<Q", buf, off)[0]


def put_u32(buf, off, val):
    struct.pack_into("<I", buf, off, val)


def parse_header(data):
    """解析 boot header，返回 dict。"""
    if len(data) < HDR_V0_SIZE:
        raise PatchError("文件太小，不是有效的 boot.img (%d 字节)" % len(data))

    if data[:8] == VENDOR_BOOT_MAGIC:
        raise PatchError("这是 vendor_boot.img，不是 boot.img。请提供 boot 分区镜像。")
    if data[:8] != BOOT_MAGIC:
        raise PatchError("找不到 ANDROID! 魔数，不是 Android boot 镜像。")

    hdr = {
        "kernel_size": u32(data, 8),
        "kernel_addr": u32(data, 12),
        "ramdisk_size": u32(data, 16),
        "ramdisk_addr": u32(data, 20),
        "second_size": u32(data, 24),
        "second_addr": u32(data, 28),
        "tags_addr": u32(data, 32),
        "page_size": u32(data, 36),
        "header_version": u32(data, 40),
        "os_version": u32(data, 44),
        "name": data[48:64].split(b"\x00", 1)[0].decode("ascii", "replace"),
        "cmdline": data[64:576].split(b"\x00", 1)[0].decode("ascii", "replace"),
        "id": data[576:608],
        "extra_cmdline": data[608:1632].split(b"\x00", 1)[0].decode("ascii", "replace"),
    }

    ver = hdr["header_version"]
    if ver > 2:
        raise PatchError(
            "检测到 header v%d (GKI 格式)，HotSPatch1 只支持 v0/v1/v2。\n"
            "      v3/v4 的 boot.img 需要 mkbootimg/magiskboot 处理。" % ver
        )

    if ver >= 1:
        hdr["recovery_dtbo_size"] = u32(data, 1632)
        hdr["recovery_dtbo_offset"] = u64(data, 1636)
        hdr["header_size"] = u32(data, 1644)
    else:
        hdr["recovery_dtbo_size"] = 0
        hdr["recovery_dtbo_offset"] = 0
        hdr["header_size"] = HDR_V0_SIZE

    if ver >= 2:
        hdr["dtb_size"] = u32(data, 1648)
        hdr["dtb_addr"] = u64(data, 1652)
    else:
        hdr["dtb_size"] = 0
        hdr["dtb_addr"] = 0

    ps = hdr["page_size"]
    if ps not in (2048, 4096, 8192, 16384, 65536):
        raise PatchError("page_size=%d 不合理，镜像可能已损坏。" % ps)

    hdr_size = HDR_V0_SIZE if ver == 0 else (HDR_V1_SIZE if ver == 1 else HDR_V2_SIZE)
    layout = {
        "header": (0, hdr_size),
        "kernel": (ps, hdr["kernel_size"]),
        "ramdisk": (ps + align(hdr["kernel_size"], ps), hdr["ramdisk_size"]),
    }
    off = layout["ramdisk"][0] + align(hdr["ramdisk_size"], ps)

    layout["second"] = (off, hdr["second_size"])
    off += align(hdr["second_size"], ps)

    if ver >= 1 and hdr["recovery_dtbo_size"]:
        layout["recovery_dtbo"] = (off, hdr["recovery_dtbo_size"])
        off += align(hdr["recovery_dtbo_size"], ps)

    if ver >= 2 and hdr["dtb_size"]:
        layout["dtb"] = (off, hdr["dtb_size"])
        off += align(hdr["dtb_size"], ps)

    hdr["layout"] = layout
    hdr["data_end"] = off
    return hdr


def extract(data, hdr, name):
    off, size = hdr["layout"][name]
    if size == 0:
        return b""
    if off + size > len(data):
        raise PatchError(
            "镜像被截断: %s 段需要 %d 字节，但文件只剩 %d 字节"
            % (name, off + size, len(data))
        )
    return data[off:off + size]


def build(data, hdr, new_kernel):
    """用 new_kernel 重组 boot.img。"""
    ps = hdr["page_size"]
    ver = hdr["header_version"]
    layout = hdr["layout"]

    ramdisk = extract(data, hdr, "ramdisk")
    second = extract(data, hdr, "second")
    rec_dtbo = extract(data, hdr, "recovery_dtbo") if "recovery_dtbo" in layout else b""
    dtb = extract(data, hdr, "dtb") if "dtb" in layout else b""

    # 保留原 header 的全部字段，只改 kernel_size / recovery_dtbo_offset / id
    hdr_size = HDR_V0_SIZE if ver == 0 else (HDR_V1_SIZE if ver == 1 else HDR_V2_SIZE)
    header = bytearray(data[:hdr_size])
    put_u32(header, 8, len(new_kernel))

    if ver >= 1 and rec_dtbo:
        # recovery_dtbo_offset 必须指向它在文件中的真实位置
        rec_off = ps + align(len(new_kernel), ps) + align(len(ramdisk), ps) \
            + align(len(second), ps)
        struct.pack_into("<Q", header, 1636, rec_off)

    # 计算 id: SHA1(kernel + kernel_size + ramdisk + ramdisk_size + second
    #              + second_size [+ recovery_dtbo + size] [+ dtb + size])
    sha = hashlib.sha1()
    sha.update(new_kernel)
    sha.update(struct.pack("<I", len(new_kernel)))
    sha.update(ramdisk)
    sha.update(struct.pack("<I", len(ramdisk)))
    sha.update(second)
    sha.update(struct.pack("<I", len(second)))
    if ver >= 1:
        sha.update(rec_dtbo)
        sha.update(struct.pack("<I", len(rec_dtbo)))
    if ver >= 2:
        sha.update(dtb)
        sha.update(struct.pack("<I", len(dtb)))
    digest = sha.digest()
    header[576:608] = digest.ljust(32, b"\x00")

    out = bytearray()
    out += bytes(header).ljust(ps, b"\x00")
    out += new_kernel.ljust(align(len(new_kernel), ps), b"\x00")
    out += ramdisk.ljust(align(len(ramdisk), ps), b"\x00")
    out += second.ljust(align(len(second), ps), b"\x00")
    if ver >= 1 and rec_dtbo:
        out += rec_dtbo.ljust(align(len(rec_dtbo), ps), b"\x00")
    if ver >= 2 and dtb:
        out += dtb.ljust(align(len(dtb), ps), b"\x00")

    # 原文件尾部可能还有 AVB footer / 其它数据。AVB 签名在改动 kernel 后必然
    # 失效，保留一个"签名对不上"的 footer 会让部分设备直接拒绝启动，故剥离。
    tail = data[hdr["data_end"]:]
    stripped_avb = False
    if tail:
        # AVB footer 固定在文件最后 64 字节
        if len(data) >= 64 and data[-64:-60] == AVB_MAGIC:
            stripped_avb = True
            tail = b""
        elif len(tail) >= 64 and tail[-64:-60] == AVB_MAGIC:
            stripped_avb = True
            tail = tail[:-64]
    out += tail
    return bytes(out), stripped_avb


def check_kernel(kernel, hdr):
    """粗检内核格式，避免把明显错误的文件塞进 boot。"""
    if len(kernel) < 1024:
        raise PatchError("kernel 文件只有 %d 字节，太小了。" % len(kernel))
    if kernel[:2] == b"\x1f\x8b":
        return "gzip"
    if kernel[:4] == b"\xfd7zXZ\x00"[:4]:
        return "xz"
    if kernel[:4] == b"\x28\xb5\x2f\xfd":
        return "zstd"
    if kernel[:4] == b"\x02\x21\x4c\x18":
        return "lz4"
    if kernel[:3] == b"\x7fELF":
        return "ELF (未压缩 Image)"
    if kernel[:4] == b"\xd0\x0d\xfe\xed" or kernel[:4] == b"\xed\xfe\x0d\xd0":
        return "dtb?"
    # QCDT / appended dtb 的 Image.gz-dtb 一般是 gzip 开头，已经命中。
    return "未知格式（仍继续，可能是自定义容器）"


def human(n):
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return "%.1f %s" % (n, unit) if unit != "B" else "%d B" % n
        n /= 1024.0


def find_file(names, desc):
    for n in names:
        if os.path.isfile(n):
            return n
    raise PatchError("当前目录找不到 %s (查找: %s)" % (desc, ", ".join(names)))


def find_boot_image():
    """优先 boot.img；否则若目录里只有一个 .img 就用它。"""
    for n in ("boot.img", "original-boot.img"):
        if os.path.isfile(n):
            return n
    cands = [
        f for f in os.listdir(".")
        if f.lower().endswith(".img")
        and os.path.isfile(f)
        and f not in ("boot-patched.img", "new-boot.img")
    ]
    if len(cands) == 1:
        return cands[0]
    if len(cands) > 1:
        raise PatchError(
            "目录里有多个 .img，无法判断哪个是 boot：%s\n"
            "      请改名为 boot.img，或用 --boot 指定。" % ", ".join(sorted(cands))
        )
    raise PatchError("当前目录没有 boot.img，请把你的 boot.img 放到本文件夹后重试。")


def do_patch(args):
    boot_path = args.boot or find_boot_image()
    kernel_path = args.kernel or find_file(
        ["kernel", "Image.gz-dtb", "Image.gz", "Image"], "内核文件"
    )
    out_path = args.output or "boot-patched.img"

    if not os.path.isfile(boot_path):
        raise PatchError("找不到 boot 镜像: %s" % boot_path)
    if not os.path.isfile(kernel_path):
        raise PatchError("找不到内核文件: %s" % kernel_path)
    if os.path.abspath(boot_path) == os.path.abspath(out_path):
        raise PatchError("输出文件不能覆盖原始 boot.img，请换一个文件名。")

    with open(boot_path, "rb") as f:
        data = f.read()
    with open(kernel_path, "rb") as f:
        kernel = f.read()

    hdr = parse_header(data)
    kfmt = check_kernel(kernel, hdr)

    print("[i] boot     : %s (%s)" % (boot_path, human(len(data))))
    print("[i] kernel   : %s (%s, %s)" % (kernel_path, human(len(kernel)), kfmt))
    print("[i] header   : v%d, page_size=%d" % (hdr["header_version"], hdr["page_size"]))
    print("[i] cmdline  : %s" % (hdr["cmdline"] or "(空)"))
    print("[i] 原 kernel: %s -> 新 kernel: %s" % (human(hdr["kernel_size"]), human(len(kernel))))

    if len(kernel) > 256 * 1024 * 1024:
        raise PatchError("kernel 超过 256 MiB，显然不对，已中止。")

    new_img, stripped = build(data, hdr, kernel)

    with open(out_path, "wb") as f:
        f.write(new_img)
    print("[+] 已生成: %s (%s)" % (out_path, human(len(new_img))))
    if stripped:
        print("[!] 检测到 AVB footer，已剥离（原签名对新内核无效）。")
    print("[!] 刷入前请确认 bootloader 已解锁；建议保留原始 boot.img 以便回滚。")
    print("[+] 完成。")


def do_verify(args):
    """校验: 新镜像里的 kernel 段是否与给定内核逐字节一致。"""
    img_path = args.verify
    kernel_path = args.kernel or find_file(
        ["kernel", "Image.gz-dtb", "Image.gz", "Image"], "内核文件"
    )
    with open(img_path, "rb") as f:
        data = f.read()
    with open(kernel_path, "rb") as f:
        kernel = f.read()

    hdr = parse_header(data)
    embedded = extract(data, hdr, "kernel")

    ok = True
    if embedded != kernel:
        ok = False
        print("[-] kernel 段与源文件不一致 (embedded=%d, source=%d)"
              % (len(embedded), len(kernel)))
    else:
        print("[+] kernel 段一致 (%s)" % human(len(kernel)))

    # 校验 SHA1 id
    if hdr["header_version"] >= 1:
        print("[i] header id: %s" % hdr["id"].hex())

    # 校验各段边界
    for name in ("ramdisk", "second", "recovery_dtbo", "dtb"):
        if name in hdr["layout"]:
            off, size = hdr["layout"][name]
            if off + size > len(data):
                ok = False
                print("[-] %s 段越界" % name)

    if not ok:
        raise PatchError("校验失败")
    print("[+] 校验通过。")


def main():
    ap = argparse.ArgumentParser(
        description="HotSPatch1 - 把 kernel 替换进 boot.img (支持 header v0/v1/v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--boot", help="原始 boot.img (默认自动查找 boot.img)")
    ap.add_argument("--kernel", help="新内核 (默认自动查找 kernel / Image.gz-dtb)")
    ap.add_argument("-o", "--output", help="输出文件名 (默认 boot-patched.img)")
    ap.add_argument("--verify", metavar="IMG", help="校验模式: 检查 IMG 内 kernel 段")
    args = ap.parse_args()

    try:
        if args.verify:
            do_verify(args)
        else:
            do_patch(args)
    except PatchError as e:
        print("[-] 错误: %s" % e, file=sys.stderr)
        return 1
    except OSError as e:
        print("[-] 文件操作失败: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
