#!/usr/bin/env python3
"""e-toys/heaton cloud material API client — RE'd from com.heaton.baselib.
POST https://manage.heaton.com.cn/api/rm/getMaterialUnderCategory?sign=&timestamp=&random=
body = AES(sorted k=v& of params); responses AES-256-CBC/PKCS7 base64. Key/IV from CloudEncipher."""
import base64, hashlib, json, time, random, string, urllib.parse, urllib.request

KEY = b"Jy47rzJAgKMfrcc92PamyyukQqB7wmFu"; IV = b"0000000000000000"
APP_KEY = "Jy47rzJAgKMfrcc92PamyyukQqB7wmFu"
BASE = "https://manage.heaton.com.cn/api/rm/getMaterialUnderCategory"

def _aes():
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    return Cipher, algorithms, modes, padding

def enc(s):
    Cipher, algorithms, modes, padding = _aes()
    p = padding.PKCS7(128).padder(); data = p.update(s.encode()) + p.finalize()
    e = Cipher(algorithms.AES(KEY), modes.CBC(IV)).encryptor()
    return base64.b64encode(e.update(data) + e.finalize()).decode()

def dec(b64):
    Cipher, algorithms, modes, padding = _aes()
    d = Cipher(algorithms.AES(KEY), modes.CBC(IV)).decryptor()
    pt = d.update(base64.b64decode(b64)) + d.finalize()
    u = padding.PKCS7(128).unpadder()
    return (u.update(pt) + u.finalize()).decode("utf-8", "replace")

def deobfuscate(content):
    """Cloud asset 'decryption' (DecryptHelper.getDecryptedFile) — pure obfuscation, no crypto:
    strip 32-char prefix+suffix, '+'->space, URL-decode, REVERSE, base64 -> raw GIF bytes."""
    import urllib.parse
    s = content[32:len(content) - 32].replace("+", " ")
    s = urllib.parse.unquote(s)[::-1].strip().replace("\\r", "").replace("\\n", "")
    return base64.b64decode(s + "=" * (-len(s) % 4))


def encode_to_url(s):
    return urllib.parse.quote_plus(s).replace("%26", "&").replace("%3D", "=").replace("%3F", "?")

def sorted_kv(m):
    return "&".join(f"{k}={m[k]}" for k in sorted(m))

def request(params):
    ts = str(int(time.time())); rnd = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    sign_map = dict(params); sign_map.update(random=rnd, timestamp=ts, app_key=APP_KEY)
    sign = hashlib.md5(encode_to_url(sorted_kv(sign_map)).encode()).hexdigest().lower()
    body = enc(encode_to_url(sorted_kv(params)))
    url = f"{BASE}?sign={sign}&timestamp={ts}&random={rnd}"
    req = urllib.request.Request(url, data=body.encode(), method="POST",
                                 headers={"Content-Type": "text/plain; charset=utf-8", "User-Agent": "okhttp/4.12.0"})
    raw = urllib.request.urlopen(req, timeout=20).read().decode()
    return json.loads(dec(raw))

def category_name_for(group, width, height, type_anim):
    """Per the app (CloudAnimManager.getCloudMateral): 16x16 and 32x32 use "<group>_IDM" for
    BOTH types; 64x64 uses "<group>_IDM" for animations but the generic "iDotMatrix" for images;
    any other size falls back to "iDotMatrix"."""
    idm = (width, height) in ((16, 16), (32, 32)) or ((width, height) == (64, 64) and type_anim)
    return f"{group}_IDM" if idm else "iDotMatrix"

def material_params(group, page, type_anim=True, width=32, height=32, label="ALL,", filter_tags="IDM_", lang="en", category_name=None):
    return {"appid": "140", "sort": "1", "page": str(page), "count": "10",
            "category_name": category_name or category_name_for(group, width, height, type_anim),
            "type": "动画" if type_anim else "图片",
            "label": label, "width": str(width), "height": str(height),
            "filter_tags": filter_tags, "file_lang": f"none,{lang}"}

if __name__ == "__main__":
    import sys
    out = request(material_params(sys.argv[1] if len(sys.argv) > 1 else "日常", 1))
    print(json.dumps(out, ensure_ascii=False)[:1200])
