# star2lte (SM-G965F, Exynos 9810): XNU / iOS 16 port

Base: the `herolte` branch (Galaxy S7, Exynos 8890), which already boots XNU
from Samsung S-Boot with its own UFS driver, `sec_ts` touch and a GICv2
board. This document keeps **data from sources** separate from **evidence on
the phone**. Target order: iOS 16.7.16 (iPhone X userland) first, iOS 26 later.

## Device evidence (2026-11-05, read-only)

- Phone: SM-G965F, bootloader `G965FXXUGFUG4`, `ro.boot.hardware=samsungexynos9810`.
  Running a One UI 7 port (Android 15) that reports itself as SM-S721B / SM-N770F.
- `/proc/cpuinfo`: 4× CPU part `0xd05` (Cortex-A55) and 4× part `0x002` (Mongoose M3).
- MemTotal 5,782,060 kB.
- TWRP 3.7.0_9-0 (`omni_star2lte`), adb as root. UFS host `11120000.ufs`,
  also `11500000.dwmmc2` (SD card).
- Partitions (`/dev/block/platform/11120000.ufs/by-name/`): **BOOT `sda10`**,
  RECOVERY `sda11`, DTB `sda8`, DTBO `sda9`, **EFS `sda3`**, CPEFS `sdd1`,
  PARAM `sda4`, SYSTEM `sda18`, VENDOR `sda19`, **USERDATA `sda25`**.
- Stock BOOT: `ANDROID!` header, page 2048, kernel 40,657,408 bytes at
  `0x10008000`, ramdisk 2,081,280 bytes at `0x11000000`, tags `0x10000100`,
  board name `SRPQH16A013KU`, cmdline `androidboot.selinux=permissive`.
  The DTB is in its own partition (unlike herolte, where it is appended).
- Backups in `backup/` (gitignored), each SHA-256 checked against the
  partition: BOOT, RECOVERY, DTB, DTBO, EFS, CPEFS, PARAM.

## Hardware map (from sources, unverified on the phone)

Sources: `LineageOS/android_kernel_samsung_universal9810` branch
`lineage-17.1` (`exynos9810.dtsi`, `exynos9810-rmem*.dtsi`,
`exynos9810-star2lte_common.dtsi`) and `ivoszbg/uniLoader`
(`board/samsung/board-starlte.c`, the S9; same SoC and panel size).

| Item | star2lte | herolte (for comparison) |
| --- | --- | --- |
| Boot cluster | Cortex-A55 "ananke", **MPIDR 0x000..0x003** | A53, MPIDR 0x100..0x103 |
| Other cluster | 4× Mongoose M3 "meerkat", MPIDR 0x100..0x103 | 4× Mongoose M1, MPIDR 0..3 |
| SMP | PSCI via SMC, `cpu_on=0xC4000003` | same |
| GIC | GIC-400 (v2): dist `0x10101000`, CPU `0x10102000` | `0x11001000` / `0x11002000` |
| Timer | 26 MHz, PPIs 13/14/11/10, `use-physical-timer` | 26 MHz |
| UFS | `0x11120000` (`samsung,exynos-ufs`) | `0x155a0000` |
| S-Boot framebuffer | **`0xcc000000`, 1440×2960 ARGB8888** (uniLoader) | `0xe2a00000`, 1440×2560 |
| DECON | DECON_F `0x16030000`; write `0x1281` to `+0x70` (HW_SW_TRIG_CONTROL) so the panel refreshes | `0x13960000`, `0x1010` |
| Touch | Samsung LSI `sec_ts` at I²C `0x48` | same chip family and address |
| GPU | Mali-G72 MP18 (Bifrost) | Mali-T880 (Midgard) |

Known reserved memory (`exynos9810-rmem.dtsi`, `-rmem_star2.dtsi`): RKP
`0xAF800000` +32 MiB, TIMA `0xB8000000` +2 MiB, `0xC0000000` +512 KiB,
`0xE1900000` +30 MiB, `0xF0000000` +146 MiB, `0xF9200000` +32 MiB,
`0xFB200000` +40 MiB (ABOX), `0xFF800000` +8 MiB, plus the ESS log region.
The framebuffer at `0xcc000000` must also stay out of XNU's free memory.

## Open questions for the first probe

- Exception level and FDT/Image addresses at entry (S-Boot may differ from herolte).
- Whether Samsung's hypervisor (RKP/uH region above) is active at EL2 and
  what it allows at EL1.
- 16 KiB granule support on the Mongoose M3 (the A55 supports it); the
  herolte base already uses 4 KiB pages, so this only matters for later.
- Whether the A5XELTE/HEROLTE no-LSE assumptions are needed: the A55 has
  LSE, the M3 does not, so keep the no-LSE build.

## Stages

1. Boot probe (adapt `shim/herolte/probe.*`): no XNU. Shows EL, FDT and load
   addresses, MIDR/MPIDR, CNTFRQ on the `0xcc000000` framebuffer.
2. Loader + `MACHINE_CONFIG=STAR2LTE` XNU with the table above, `cpus=1`.
3. UFS root at `0x11120000`, then USERDATA `sda25`.
4. iOS display at 1440×2960 (CPU copy), buttons, `sec_ts` touch.
5. All 8 cores; later Mali-G72; later iOS 26.
