# iOS 16 on the Samsung Galaxy S9+ (SM-G965F, Exynos 9810) — `star2lte` branch

> ⚠️ **Experimental, AI-assisted port.** Built in one day by a human directing an AI
> (Claude, Anthropic) on real hardware, on top of the Galaxy S7 port below. It
> **erases Android's USERDATA**. No Apple software is in this repository.

**Status, 2026-11-05:** Apple's XNU kernel boots on the Exynos Galaxy S9+ and runs the
unmodified **iPhone X iOS 16.7.16 userland** to the **lock screen**: 664 processes start,
SpringBoard runs, and the Bixby key works as Home. Rendering is on the CPU, one core for now.

| Area | State |
| --- | --- |
| Boot | Samsung S-Boot loads our loader from BOOT (`shim/star2lte/`), which starts XNU. XNU RAM is 1 GiB of the second DRAM bank |
| CPU | Boot Cortex-A55 working. All 8 cores (4× A55, 4× Mongoose M3) are described and opt-in with `cpus=4` / `cpus=8`, not yet tested |
| Storage | Exynos UFS: S-Boot leaves HCE = 0 but the link up; the driver trusts HCS (`ufshce=1`). iOS root is HFSX in USERDATA, read/write |
| Display | iOS draws natively at 1440×2960 into S-Boot's scanout buffer (`0xcc000000`), copied by the CPU: about 9 fps on one core |
| Buttons | Power, volume up/down, and **Bixby as Home** |
| Touch | Samsung `sec_ts`, same chip as the S7. Its supplies are off after S-Boot; switching them on through the APM firmware (ACPM) is in the current build, untested |
| Not working | GPU (Mali-G72), Wi-Fi, Bluetooth, modem, audio, camera, sensors, sleep |

**What it took, beyond the S7 port** (details in [docs/star2lte-bringup.md](docs/star2lte-bringup.md)):

- **Board:** S9+ addresses for the GIC, framebuffer, UFS, PMU, GPIO and touch (patch `xnu/patches/0318`).
- **UFS:** the 9810 vendor registers sit at +0x1100, and HCE reads 0 after S-Boot.
- **GPIO:** the 9810 ALIVE block has an extra bank first: GPA0/1/2 are at +0x20/+0x40/+0x60.
- **PAN:** the A55 has Privileged Access Never and the S7's A53 does not. With
  `SCTLR_EL1.SPAN = 0` the CPU set PAN on every system call, so the kernel faulted forever reading
  launchd's memory. The fix sets SPAN and clears PAN at start.
- **Mongoose M3 cores:** they lack the A55's ARMv8.1/8.2 extensions, so with `cpus` > 4 the kernel
  advertises only ARMv8.0 features to iOS.

**Next:** touch, 4 and 8 cores, a scaled iPhone-size canvas for speed, Wi-Fi (BCM4361), a
jailbreak layer, and later the Mali-G72 GPU.

## How to try it (S9+)

You need an Exynos SM-G965F with an unlocked bootloader and TWRP, and the iPhone X iOS 16.7.16
IPSW from Apple. Back up BOOT, EFS and CPEFS from TWRP first and keep them off the phone.

1. **Kernel:** fork this repository and run the `xnu` workflow on the `star2lte` branch
   (`MACHINE_CONFIG` HEROLTE; the branch builds the S9+ variant, `STAR2LTE=1`).
2. **iOS root image:** in a **private** repository, push this branch as `ios-root-build`; the
   `ios-root` workflow builds a 20 GiB HFSX root and publishes it as a private release.
3. **Flash the root** from TWRP with `/data` unmounted (this erases USERDATA):
   `tools/herolte-flash-root.py adb root.img.gz.part0* --dev /dev/block/platform/11120000.ufs/by-name/USERDATA`
4. **BOOT image:** put the release's `d22ap.adt` in `research/ipsw-x/`, then
   `tools/star2lte-pack-xnu.sh kernel.development.herolte xnu-boot.img "rd=ufsroot0 ufsroot=USERDATA ufsrw=1 rootrw=1 cs_enforcement_disable=1 unentitled_ios_sim_launch=1 ignition_level=1 launchd_unsecure_cache=1 wdt_test=no_user_checkin a5fb_keep_on=1 a5fb_noconsole=1 a5fb_perf=1 sweetfb_native=1"`
   and write it to BOOT (`/dev/block/sda10` on the tested phone) from TWRP.
5. **Logs:** back in TWRP, `HEROLTE_LOG_DEV=/dev/block/platform/11120000.ufs/by-name/USERDATA tools/herolte-log-pull.py adb boot.txt`.

**Back to Android:** write your stock BOOT back and format Data in TWRP.

## Credits

This port is a fork of [wardevsa/ios-a5xelte](https://github.com/wardevsa/ios-a5xelte) (the Galaxy S7
port), itself built on [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) (MIT) by way of
[orhunnx/ios-a5xelte](https://github.com/orhunnx/ios-a5xelte). Most of the kernel work, the loader and the
tools come from them; their bring-up diaries are in that history. Also used:
[HakiOS](https://github.com/oosexgang/hackios-xnu-kernel) and Bergamota's EAGL code (`gpu/`, see their
NOTICE files), [syncmodz/ios-s9](https://github.com/syncmodz/ios-s9), Apple's open-source releases (xnu,
IOHIDFamily, libpthread, hfs), [BearSSL](https://bearssl.org),
[blacktop/darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build),
[ipsw](https://github.com/blacktop/ipsw), the [LineageOS Exynos 9810 kernel](https://github.com/LineageOS/android_kernel_samsung_universal9810)
and [uniLoader](https://github.com/ivoszbg/uniLoader) for the hardware tables. iOS itself is Apple's and is
not distributed here.

The code keeps its upstream names (`HEROLTE`, `A5XELTE`, `SWEET`): the S9+ is the `STAR2LTE` variant of the
HEROLTE kernel configuration (`xnu/patches/0318-star2lte-board.patch`).
