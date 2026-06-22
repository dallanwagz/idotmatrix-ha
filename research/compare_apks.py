#!/usr/bin/env python3
"""Compare two iDotMatrix APKs (Play Store vs e-toys.cn local server) for tamper/malware signals."""
import sys, hashlib
from loguru import logger
logger.remove()
from androguard.core.apk import APK

PS = "/Users/dallan/repo/idm/apks/playstore/playstore-base.apk"
ET = "/Users/dallan/repo/idm/apks/etoys/etoys-idotmatrix-2.1.1.apk"


def certs(a):
    out = []
    schemes = [
        ("v1", "get_certificates_der_v1"),
        ("v2", "get_certificates_der_v2"),
        ("v3", "get_certificates_der_v3"),
    ]
    for scheme, meth in schemes:
        g = getattr(a, meth, None)
        if g is None:
            continue
        try:
            ders = g() or []
        except Exception:
            ders = []
        if isinstance(ders, (bytes, bytearray)):
            ders = [ders]
        for d in ders:
            out.append((scheme, hashlib.sha256(d).hexdigest()))
    return out


def info(path):
    a = APK(path)
    return {
        "package": a.get_package(),
        "versionName": a.get_androidversion_name(),
        "versionCode": a.get_androidversion_code(),
        "minSdk": a.get_min_sdk_version(),
        "targetSdk": a.get_target_sdk_version(),
        "perms": set(a.get_permissions()),
        "activities": set(a.get_activities()),
        "services": set(a.get_services()),
        "receivers": set(a.get_receivers()),
        "providers": set(a.get_providers()),
        "certs": certs(a),
        "app": a,
    }


ps, et = info(PS), info(ET)

print("="*70)
print(f"{'FIELD':<14} {'PLAY STORE':<28} {'E-TOYS.CN':<28}")
print("="*70)
for k in ("package", "versionName", "versionCode", "minSdk", "targetSdk"):
    print(f"{k:<14} {str(ps[k]):<28} {str(et[k]):<28}")

print("\n--- SIGNING CERTS (sha256 of DER) ---")
for label, d in (("PlayStore", ps), ("E-toys", et)):
    print(f"  {label}:")
    for scheme, h in d["certs"]:
        print(f"    {scheme}: {h}")
print("  SAME signer? ", set(h for _, h in ps["certs"]) & set(h for _, h in et["certs"]) or "NO OVERLAP")

for comp in ("perms", "activities", "services", "receivers", "providers"):
    p, e = ps[comp], et[comp]
    only_e = e - p
    only_p = p - e
    print(f"\n--- {comp.upper()}  (PS={len(p)} ET={len(e)}) ---")
    if only_e:
        print(f"  ONLY in E-TOYS ({len(only_e)}):")
        for x in sorted(only_e):
            print(f"    + {x}")
    if only_p:
        print(f"  ONLY in PLAY STORE ({len(only_p)}):")
        for x in sorted(only_p):
            print(f"    - {x}")
    if not only_e and not only_p:
        print("  identical")
