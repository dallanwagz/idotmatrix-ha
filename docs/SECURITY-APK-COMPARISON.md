# Security comparison — Play Store vs. e-toys.cn "local server" APK

**Objective A:** Is the direct-download APK from the QR-code site
(`http://api.e-toys.cn/page/app/140`) nefarious vs. the Google Play Store build?

**Date:** 2026-06-22 · **App:** iDotMatrix `com.tech.idotmatrix` · both builds **v2.1.1 (211)**

## TL;DR

**No smoking-gun malware was found, but the e-toys build is meaningfully more
invasive *and* deliberately opaque, so there is no good reason to prefer it.**
The differences are consistent with a typical Chinese "direct-download" build —
hardened against piracy, self-updating, and analytics-heavier — rather than a
targeted trojan. But because the e-toys build is **DEX-packed (encrypted)**, static
analysis *cannot fully clear it.* **Recommendation: use the Play Store build.** It is
strictly less-privileged, unpacked/auditable, Google-scanned, and functionally
identical (same version, package, components, and native libraries).

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

## Residual gap (how to fully close it, if ever needed)
The only way to *fully* verify the packed e-toys build is **dynamic**: install it on an
isolated/monitored device and watch its traffic (mitmproxy + a DNS sink), or dump the
decrypted DEX from memory (Frida/`baiduprotect` unpacker) and re-diff. Not done here —
the user asked for static analysis only, and the recommendation above makes it moot.
