#!/usr/bin/env python3
"""Build the star2lte (SM-G965F, Exynos 9810) ADT for the STAR2LTE XNU build.

The herolte ADT (mkadt_herolte.py) with the S9+ board: boot A55 only,
GIC-400 at 0x10101000/0x10102000, UFS at 0x11120000, the S-Boot scanout at
0xcc000000 (1440x2960) and XNU RAM in the second DRAM bank. Sources and
device evidence: docs/star2lte-bringup.md.
"""
import argparse
import os
import sys
from pathlib import Path

import adt
import mkadt
import mkadt_herolte
from mkadt_herolte import child, set_prop

# Live DT: memory@880000000 (2 GiB) and memory@900000000 (2 GiB), no
# reserved-memory node in either. herolte boots with 1 GiB of its bank 2.
BANK2_BASE, BANK2_SIZE = 0x880000000, 0x80000000
FB_BASE, FB_WIDTH, FB_HEIGHT = 0xcc000000, 1440, 2960
GICD, GICC = 0x10101000, 0x10102000
UFS_BASE = 0x11120000


def build(dram):
    if not os.path.exists(mkadt.D22AP_ADT):
        # Enough for the kernel; SpringBoard needs the real /product.
        mkadt.d22ap_product = lambda path=None: [('artwork-display-gamut', mkadt.cstr('sRGB'))]
    root = mkadt_herolte.build((FB_WIDTH, FB_HEIGHT), dram, 3)
    set_prop(root, 'compatible', mkadt.cstr('D22AP') + mkadt.cstr('iPhone10,3') +
             mkadt.cstr('samsung,a5xelte') + mkadt.cstr('samsung,star2lte') +
             mkadt.cstr('samsung,exynos9810') + mkadt.cstr('AppleARM'))
    chosen = child(root, 'chosen')
    set_prop(chosen, 'firmware-version', mkadt.cstr('star2lte-entry'))
    set_prop(chosen, 'system-firmware-version', mkadt.cstr('star2lte-entry'))
    # Live DT /cpus: A55 "ananke" reg 0x0..0x3 (boot cluster; the boot CPU
    # reads MPIDR 0x81000000, XNU compares Aff1/Aff0), Mongoose M3 "meerkat"
    # reg 0x100..0x103. The herolte nodes keep their order (logical 0..3 the
    # boot cluster, 4..7 the big cores); only reg, names and clocks change.
    # SweetCPU matches IONameMatch 'arm,cortex-a53', so that stays listed.
    cpus = child(root, 'cpus')
    for logical, cpu in enumerate(cpus.children):
        big = logical >= 4
        set_prop(cpu, 'reg', mkadt.u32(0x100 + logical - 4 if big else logical))
        set_prop(cpu, 'compatible', (mkadt.cstr('samsung,mongoose-m3') if big else
                                     mkadt.cstr('arm,cortex-a55')) +
                 mkadt.cstr('arm,cortex-a53') + mkadt.cstr('ARM,v8'))
        set_prop(cpu, 'clock-frequency', mkadt.u32(2704000000 if big else 1794000000))
    arm_io = child(root, 'arm-io')
    set_prop(arm_io, 'device_type', mkadt.cstr('star2lte-io'))
    set_prop(arm_io, 'compatible', mkadt.cstr('samsung,exynos9810-io') + mkadt.cstr('arm-io'))
    soc = mkadt_herolte.SOC_BASE
    set_prop(child(arm_io, 'gic'), 'reg', mkadt.u64(GICD - soc, 0x1000, GICC - soc, 0x1000))
    # exynos9810.dtsi ufs@0x11120000 (HCI +0); its vendor register layout
    # differs from the 8890 and is not used until the UFS driver is ported.
    set_prop(child(root, 'herolte-ufs'), 'reg', mkadt.u64(UFS_BASE, 0x3000))
    fbcon = child(root, 'a5xelte-fbcon')
    set_prop(fbcon, 'reg', mkadt.u64(FB_BASE, FB_WIDTH * FB_HEIGHT * 4))
    set_prop(fbcon, 'height', mkadt.u32(FB_HEIGHT))
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--bank2-mb', type=int, default=1024,
                        help='MiB of the second bank for XNU (as herolte, 1024)')
    args = parser.parse_args()
    if not 0 < args.bank2_mb <= BANK2_SIZE >> 20:
        sys.exit('--bank2-mb out of range')
    blob = adt.serialize(build((BANK2_BASE, args.bank2_mb << 20)))
    args.output.write_bytes(blob)
    print(f'{args.output}: {len(blob)} bytes')
