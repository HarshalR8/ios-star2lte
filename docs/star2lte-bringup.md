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

## Probe 1 on the phone (2026-11-05, commit `ace0abb`)

BOOT image `out/probe-boot.img` (sha256 `15659112…1e9c`, readback matched).
The user photographed the screen; the probe then rebooted into TWRP by
itself (PMU `0x14060000` INFORM2/INFORM3/SYSIP_DAT0 + SWRESET works).
The text appears over S-Boot's logo, so `0xcc000000` is the live scanout.

| Value | Reading | Meaning |
| --- | --- | --- |
| EL | 1 | entered at EL1 (as herolte) |
| SCTLR | `0x30C5183E` | MMU and caches off |
| FDT | `0x8A000000` | same as herolte |
| IMAGE | `0x800AC000` | where S-Boot placed our Image |
| MIDR | `0x410FD051` | Cortex-A55 r0p1 |
| MPIDR | `0x81000000` | **MT bit set**: affinity is Aff1/Aff2, not Aff0 |
| MMFR0 | `0x101122` | 40-bit PA, 16-bit ASID, **16 KiB granule yes**, 4 KiB yes |
| PFR0 | `0x10112222` | no GIC system registers (GICv2), RAS |
| ISAR0 | `0x10211120` | LSE atomics (A55); the M3 cores may lack them |
| ISAR1 | `0x100001` | **no pointer authentication** (APA/API = 0), LRCPC |
| CNTFRQ | 0 | S-Boot does not set it: program 26 MHz before XNU |
| TRIG | `0x3070` | DECON_F +0x70 before the probe wrote `0x1281` |
| INITRD | `0x89000000..0x891FC200` | 16 MiB gap to the FDT, as herolte |

## XNU boot 1 (2026-11-05, kernel run 41982460115, `out/xnu-boot-1.img`)

No `rd=`. Two photos: XNU reached `ASXELTE CPU: cpu=0 mpidr=0x0 came alive;
SGI1 OK`, `1/1 CPUs initialized`, a 20 ms timer test (21.02 ms: 26 MHz from
the ADT is right), VM bootstrap, zone init, IOKit, `AppleCLCD 1440x2960
stride 5760 at 0xcc000000`, MAC policies, HFS, Skywalk self-tests (all
PASSED), lo0/gif0/stf0, then stopped as expected at `Waiting on <dict>
IOMedia Apple_HFS`. Boot CPU, GICv2, timer, second-bank RAM and the
framebuffer console work on the S9+.

## iOS boots (2026-11-05, boot 8, kernel run 42008085162)

The path from XNU boot 1 to iOS, one fix per boot:

- **UFS (boot 2-3):** S-Boot hands over HCE = 0 with HCS = 0x10f; trusting
  HCS (ufshce=1, like Linux's BROKEN_HCE) works. USERDATA reads/writes.
- **GPIO (boot 3):** the 9810 ALIVE block has etc1 first: GPA0/1/2 at
  +0x20/+0x40/+0x60. Keys work, Bixby is Home.
- **PAN (boot 7):** launchd spun in mach_vm_allocate: bcopyin faulted
  forever because the A55 sets PSTATE.PAN on every exception while
  SCTLR_EL1.SPAN = 0. Fixed by setting SPAN and clearing PAN at start.

Boot 8 (`out/boot8.txt`, user photos): Apple logo, then the lock screen;
Bixby works as Home. 664 processes exec'd, SpringBoard running, one CPU
saturated (xpcproxy, SpringBoard, suggestd...), AppleCLCD at native
1440x2960: 9.3 fps, 5.5 ms per frame copy. Touch still unpowered.

## Boots 10-12: 4 cores and touch power (2026-11-06)

- **4 cores (boot 12, `cpus=4`):** `4/4 CPUs initialized, SGI1 verified`. Boot 10 hung
  because the DynamIQ A55s report the core in MPIDR Aff1 (MT set); the reset vector and
  `ml_get_cpu_number` now map MT MPIDRs to ADT ids 0..3.
- **ACPM:** the firmware's `struct ipc_channel` is 72 bytes with `channel_info` at +16 (not
  Linux's 68/+12). Channel 2 (PMIC): len 5, size 16. LDO35 read `0x2c` (1.8 V) and LDO43
  `0x30` (3.0 V), both disabled; enabling them raised SDA/SCL (`dat 0xc0 -> 0xf0`).
- **I2C:** transfers then ended in `NO_DEV_ACK`. TWRP's kernel programs `104b0000.hsi2c` with
  FS1 `0x01F0FF00`, FS2 `0x030003E0`, FS3 `0x00210000` (200 MHz, DIV 33, 400 kHz); herolte's
  values set divider 1. Fixed in the next build.

## Boots 13-15: touch works (2026-11-06)

- **Boot 13:** with the HSI2C timing fixed the IC answered (boot status 0x20, id `ac 37 61 01 00`)
  and iOS opened the touch HID service, but other reads returned 0xff.
- **Boot 14:** the IC stayed up for 3 s; only herolte's commands failed. The S9+ IC uses the newer
  sec_ts set: READ_ONE_EVENT 0x60, SENSE_ON 0x10, CLEAR_EVENT_STACK 0x62, TS_STATUS 0xAF, and
  byte 0 of an event is `eid:2 tid:4 tchsta:2` (LSB first, coordinate eid 0, tid from 1).
- **Boot 15 (`cpus=4`):** touch works (press/release with coordinates, the lock screen swipe
  opened the home screen). Then the IC dropped off the bus (NODEV, NO_DEV_ACK). The UI was
  unusable: a dozen widget extensions used 50-70% of a core each, kernel_task ~220%; 10 fps.

## Next boot (kernel run 42030602818)

Touch power-cycle recovery after 10 lost reads; `herowidgets=0` refuses every program whose name
contains `Widget`. Pack it with:

    tools/star2lte-pack-xnu.sh xnu/out/run42030602818/kernel.development.herolte out/xnu-boot-16.img \
      "$(cat out/ios-bootargs.txt) sweettop=1 cpus=4 herowidgets=0 heronoexec=vmd,bluetoothd"

Then try `cpus=8` (the M3s; iOS gets ARMv8.0-only features), and a scaled canvas for speed.
The Mali-G72 GPU is the large next project (herolte's GPU code is ~3800 lines for Midgard).

## Boot 16a (2026-11-06): blocking chronod

Kernel run 42026576192 with `cpus=4 heronoexec=vmd,bluetoothd,chronod`: SpringBoard stayed on
the Apple logo (1.2 fps, CPU nearly idle), waiting for the widget service. Touch stayed on the
bus the whole boot (`moves=335 lost_reads=0`): boot 15's dropouts came with the CPU saturated.
Block the widget extensions (`herowidgets=0`), not chronod.

## Boot 16 (2026-11-06): widgets blocked, still slow

Kernel run 42127332733, `cpus=4 herowidgets=0 heronoexec=vmd,bluetoothd`: taps work, the UI is
very slow. 20 programs refused. sweettop: PosterBoard 100-224%, backboardd 88-188%, poster
extensions 10-45% each (CollectionsPoster, EmojiPosterExtension, WeatherPoster,
UnityPosterExtension, ExtragalacticPoster, GradientPoster); 3.4-8.9 fps at native 1440x2960.
Touch stable (`lost_reads=0`).

Next (kernel with `heroposters=0`): the iPhone XR canvas (`ADT_ARGS=--scale2`, boot-args
`sweetfb_scale=1 sweetfb_lw=828 sweetfb_lh=1792` instead of `sweetfb_native=1`, saved in
`out/ios-bootargs-xr.txt`) and poster extensions blocked.

## Boot 17 and the GPU plan (2026-11-06)

Boot 17 (XR canvas, `heroposters=0`): much smoother but 10 fps with `avg_copy_us 55915`:
the kernel's scaledCopy was the limit (backboardd only 33%). Rewritten row-buffered on the copy
helpers. Taps landed low: SweetHIDTouch normalized over herolte's 1440x2560; now 1440x2960.

**Mali-G72 MP18 (Bifrost, Job Manager), from the 9810 kernel:**

- Registers `mali@17500000` (0x5000), IRQs JOB/MMU/GPU; CMU_G3D `0x17400000`.
- Power domain `pd-embedded_g3d`: pmucal `embedded_g3d_on` = PLL_CON2_PLL_G3D (+0x148)
  `0x30000003`, PLL_CON0_PLL_G3D (+0x140) bit 4, mux (+0x100) bit 4, PMU `0x14064040` = 0xf,
  wait `0x14064044` = 0xf; then `exynos_pd_tz_restore`: SMC `0x82000410` (1, `0x17410204`).
- DVFS 260-572 MHz through ACPM (`ACPM_DVFS_G3D`), default 800 mV.
- Versus herolte's Midgard code (`bsd/dev/herolte_gpu.c`, ~3800 lines with HeroGPU.cpp and
  herolte_gl.c): the Job Manager submit path should carry over; the MMU must switch from
  Mali-LPAE (`TRANSTAB | 7`, leaf `0x2c1`) to the AArch64 format with `AS_TRANSCFG`;
  power/clock/addresses are new; Mesa Panfrost must accept the G72's GPU_ID.

Stages: 1 power up and read GPU_ID (`s9gpu=1/2`, commit c1b60cd); 2 MMU (AArch64 tables) and
a null/write-value job; 3 scaling the display through the GPU (`sweetfb_gpu`); 4 iOS rendering
through Mesa/EAGL.

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
5. All 8 cores (patch 0318, `cpus=N`).
6. Wi-Fi: BCM4361 on the 9810 PCIe host (herolte's BCM4359 msgbuf driver,
   firmware from the untouched VENDOR partition).
7. Jailbreak layer as syncmodz/ios-s9 (Procursus bootstrap, ElleKit, Sileo,
   fetched from the official sources, not redistributed).
8. Mali-G72 (Bifrost) GPU; later iOS 26; at the very end, on request,
   Android + iOS dual boot.
