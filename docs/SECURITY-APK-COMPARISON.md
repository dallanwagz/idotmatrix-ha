# Security comparison — Play Store vs. e-toys.cn "local server" APK

**Objective A:** Is the direct-download APK from the QR-code site
(`http://api.e-toys.cn/page/app/140`) nefarious vs. the Google Play Store build?

**Date:** 2026-06-22 · **App:** iDotMatrix `com.tech.idotmatrix` · both builds **v2.1.1 (211)**

## TL;DR

**No smoking-gun malware was found, but the e-toys build is meaningfully more
invasive *and* deliberately opaque, so there is no good reason to prefer it.**
The differences are consistent with a typical Chinese "direct-download" build —
hardened against piracy, self-updating, and analytics-heavier — rather than a
targeted trojan. But because the e-toys build is **DEX-packed (encrypted) with active
anti-tamper**, static analysis cannot fully clear it and a runtime DEX dump was blocked.
**Recommendation: use the Play Store build.** It is strictly less-privileged,
unpacked/auditable, Google-scanned, and functionally identical.

**The one concrete risk** (see "What the 4 extra permissions actually do" below): the
e-toys build ships an **unverified self-updater** — at startup it fetches a server-chosen
`app_url` from `api.e-toys.cn` and installs that APK with **no signature/checksum/TLS-pin
check**. A MITM or compromised vendor server could push an arbitrary APK. This is why it
requests `REQUEST_INSTALL_PACKAGES`; the other 3 extra permissions trace to the
packer/Bugly, not app logic. (The Play build delegates updates to Google Play and is the
safe choice — though note *both* builds send the same telemetry to e-toys.cn / heaton.com.cn
/ ip138 / Bugly.)

## How they were obtained

| | Play Store | e-toys.cn "local server" |
|---|---|---|
| Source | pulled off the paired RG556 (`pm path` → `adb pull`); `installerPackageName=com.android.vending` | `https://api.e-toys.cn/resources/upload/files/20260603/761294e26fe1e95faec64cec0ec5d1ed.apk` (the page's 3rd "希顿/heaton" button) |
| Form | split APK (base + arm64_v8a + xxhdpi) | single universal APK (109 MB) |
| base.apk sha256 | `1183def14dee2f99…` | `6b49b7475c306d4b…` (whole apk) |

## What is the SAME (reassuring)

- **Identical version** — versionName `2.1.1`, versionCode `211`, minSdk 26, targetSdk 35.
- **Same package** `com.tech.idotmatrix`.
- **Identical components** — 31 activities, 2 services, 1 receiver, 3 providers; the
  sets match exactly (no extra service/receiver/provider declared in e-toys).
- **Native libs identical** except the packer — both ship the same
  `libjl_*`/`libjlspeex` (JieLi BT-SoC), `libAES`, `libBugly_Native`, `libucrop`,
  `libyuv-decoder`, `libpl_droidsonroids_gif`, `libint16fft`. The **only** extra
  `.so` in e-toys is `libbaiduprotect.so` (the packer).
- **No new network domain** appears in the e-toys build's analyzable parts.

## What is DIFFERENT (the scrutiny list)

### 1. Different signer (expected, not by itself proof of tampering)
- **Play Store:** v2+v3 signed by Google's Play App Signing key
  `sha256 bb538ede27d289cdd73a3fde03825e8c38d9b5bfa5f2265c99e9071597e52785`.
- **e-toys:** v1+v2+v3 signed by the vendor's own self-signed dev key
  `sha256 1d162e9d55fccb570d99c0e04252d2f9a0b510f467e41d732faf9b7ff85a2bf2`
  — `CN=DDL, OU=bestway, O=佰微, L=成都 (Chengdu), ST=四川, C=CN`, valid 2014→**3012**.

A mismatch here is **expected**: Google re-signs every Play delivery, so the on-device
Play cert can never equal a direct-download vendor key. The cert difference is therefore
*not* evidence of tampering — it just means "this is the vendor's own build, not Play's."

### 2. e-toys requests 4 extra permissions the Play build does NOT
| Permission | Why it matters |
|---|---|
| `REQUEST_INSTALL_PACKAGES` | Can install other APKs (self-update / sideload). **Play policy bans it — which is exactly why the Play build omits it.** |
| `READ_PHONE_STATE` | Device identifiers / phone state (privacy-sensitive). |
| `GET_TASKS` | Enumerate other running apps (deprecated, privacy-ish). |
| `RECEIVE_BOOT_COMPLETED` | Auto-start on boot. |

The e-toys manifest also wires the self-update channel: `REQUEST_INSTALL_PACKAGES` +
`FileProvider "com.tech.idotmatrix.android7.fileprovider"` — the textbook
"download an APK → prompt to install it" path. The Play build keeps the FileProvider
but **lacks the install permission**, so that path is dormant there.

### 3. e-toys is DEX-packed with Baidu Protect (百度加固) — the app's code is encrypted
- Evidence: `assets/baiduprotect{,1,2,3,4}.{jar,i.dex}`, `assets/baiduprotect.md`,
  `lib/arm64-v8a/libbaiduprotect.so`, and a decryptor stub `com.sagittarius.v6.StubApplication`
  (XOR-obfuscated strings + anti-debug) that loads the real app `com.tech.idotmatrix.App`
  at runtime (`AppInfo.APPNAME="com.tech.idotmatrix.App"`, `LIBNAME="baiduprotect"`).
- Effect: the app's own classes are **not statically visible** — `com/tech/idotmatrix`
  decompiles to **1** class in e-toys vs **508** in the (unpacked) Play build.
- Packing is **dual-use**: legitimate anti-piracy/anti-tamper, but it also defeats static
  malware review. The real endpoints and the consumers of the extra permissions live
  inside the encrypted payload and **could not be audited**.

### 4. Real endpoints (from the unpacked Play build — same app logic)
The app talks to: `manage.heaton.com.cn` (vendor backend), `api.e-toys.cn` /
`tapi.e-toys.cn` (vendor API), `api.ip138.com` (public-IP geolocation lookup), and
Tencent **Bugly** (`*.bugly.qcloud.com`, `android.bugly.qq.com`, `h.trace.qq.com`) for
crash/analytics — plus Google/Github/library URLs. These are the genuine destinations;
the e-toys build's same code is packed, so its destinations could not be re-confirmed
statically (no *additional* domain was observed in its analyzable parts).

## Verdict & recommendation

- **Nefarious?** No definitive malware indicator (no extra components, no extra native
  payload beyond the packer, no new domains in the clear). The deltas read as a standard
  hardened/self-updating Chinese direct-download build.
- **But riskier and unauditable:** it is signed by a non-Google key, requests
  self-install + read-phone-state + boot + get-tasks, and **hides its real code behind a
  packer** so those capabilities cannot be cleared statically.
- **Use the Play Store build.** Identical version/function, strictly fewer permissions,
  unpacked and Google-scanned, and it cannot silently self-update outside Play.

## What the 4 extra permissions actually do

The e-toys build is packed, so its own bytecode can't be read directly. But both builds
are the **same version (2.1.1)** and the same code — they differ only by a build *channel*
(`HEATON_CHANNEL`: `google` for Play, `server` for e-toys). So the unpacked Play build is
the e-toys app's twin, and tracing it answers what each permission is for:

### `REQUEST_INSTALL_PACKAGES` — an **unverified self-updater** (the real risk) — DEFINITIVE
On the `server` channel, **at `MainActivity` startup**, the app runs
`UpdateManager.versionUpdate()` (`com/heaton/baselib/manager/UpdateManager.java`):
1. POSTs `app_id`/`platform` to **`https://api.e-toys.cn/api/app/lastUpdate`**.
2. Reads a **server-controlled `app_url`** from the JSON response.
3. Downloads that APK over plain `HttpURLConnection` to external storage.
4. Installs it via `ACTION_VIEW` + `application/vnd.android.package-archive` through the
   `com.tech.idotmatrix.android7.fileprovider` provider.

There is **no signature pinning, no checksum/hash check, and no TLS pinning** on this path.
A network MITM or a compromised `api.e-toys.cn` can return an arbitrary `app_url` and the
app will prompt the user to install it. This is exactly why the e-toys build needs
`REQUEST_INSTALL_PACKAGES`; the Play build delegates updates to Google Play and never does.

### `READ_PHONE_STATE`, `GET_TASKS`, `RECEIVE_BOOT_COMPLETED` — packer/Bugly, not app logic
In the e-toys manifest these three are appended **after `</application>`** (outside the app
element) — the signature of a **manifest-merge injection by the Baidu-Protect packer / the
native Tencent Bugly SDK** (`libBugly_Native.so`, shipped in e-toys). In the unpacked twin:
- **No live app-code consumer** of `READ_PHONE_STATE` (all IMEI/device-id readers in
  `blankj` utils / `AppUtils` are dead code with zero callers). The live reader is **Bugly**,
  pulling network-operator/network-type for crash-report context — not IMEI harvesting.
- **`GET_TASKS`** uses are own-process foreground checks (Bugly + utils) — no app enumeration.
- **No app-code `BOOT_COMPLETED` receiver** exists; it's the packer/Bugly keep-alive layer.
- **No Chinese push/ad SDKs** anywhere (no Umeng/Getui/JPush/Pangle/GDT). Only tracker = Bugly.

### Both builds are equally chatty (not just e-toys)
The telemetry is **not** channel-gated — even the Play build talks to `api.e-toys.cn`
(`/api/app/count`, `/App/add_app_status_info`, `/app/bluetoothFilter`, …),
`manage.heaton.com.cn` (firmware/cloud), `api.ip138.com` (public-IP geolocation), and
Tencent **Bugly** (appId `ab35efd421`). Only the **updater** differs between the two builds.

## Dynamic-unpack attempt (to confirm the packed-only items) — BLOCKED by anti-tamper
To confirm the packer-attributed items (exact boot-receiver class, native phone-state/task
readers, any hidden branches in the `server` DEX), the packed DEX must be dumped at runtime.
Attempted on the available hardware:
- The rooted Amlogic TV box is **Android 7.1 (API 25)** — below the app's `minSdk 26`, can't install.
- The Anbernic RG556 is **Android 13** but **not actually rooted** (inert AOSP `su`).
- **BlackDex** (non-root unpacker) on the RG556 got to "Unpacking classes.dex (1/1)…" then
  **failed with an environment-detection error** — Baidu Protect's **anti-debug/anti-tamper
  defeated the dump**. (The genuine Play app was restored afterward from the saved splits.)

This is itself a finding: the vendor enabled **active runtime anti-analysis** on the e-toys
build. Fully closing the gap would need a **rooted Android 8–12 device + Frida-DEXDump with
an anti-anti-debug hook**, or a custom unpacking ROM (FART/Youpk) — beyond the hardware on
hand. The static-twin analysis above already establishes the one finding that matters (the
unverified self-updater), so the recommendation — **use the Play Store build** — stands.
