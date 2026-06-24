# e-toys / Heaton cloud animation catalog

Reverse-engineered client for the **Animation tab** of the iDotMatrix app (`com.tech.idotmatrix`)
— the cloud library behind the *daily / holiday / emoji / creative / business* sub-tabs. RE'd from
the decompiled `com.heaton.baselib` + confirmed live. **751 32×32 animated GIFs** across 5 categories.

## The API (RE'd)

- **Endpoint:** `POST https://manage.heaton.com.cn/api/rm/getMaterialUnderCategory?sign=&timestamp=&random=`
- **Body:** `AES-256-CBC(PKCS7)` of the sorted `k=v&` param string, base64, sent as `text/plain`.
- **`sign`** = `MD5( urlencode( sorted "k=v&" of {params + random + timestamp + app_key} ) )` (lowercase).
- **Response:** base64 → `AES-256-CBC` decrypt → JSON `{status, msg, data:{records[], totalPage, …}}`.
- **Crypto (from `CloudEncipher`/`AESUtils`):** key/app_key `Jy47rzJAgKMfrcc92PamyyukQqB7wmFu`,
  IV = sixteen ASCII `0`s, `AES/CBC/PKCS7Padding`.
- **Params:** `appid=140, sort=1, page, count=10, type=动画(anim)/图片(image), width=32, height=32,
  category_name="<group>_IDM", label, filter_tags, file_lang="none,en"`. The 5 sub-tabs are the
  Chinese groups **日常/节日/表情/创意/商业**. Generic `label="ALL,"` / `filter_tags="IDM_"` returns
  everything (no device-specific id needed).
- **Assets:** each `record.file_path` is on the CDN **`https://images.heaton.com.cn/download/…`**
  (`format`, `width`, `height`, `label`, `category_name`). The file is **obfuscated, not encrypted**
  (`DecryptHelper.getDecryptedFile`): **strip the 32-char prefix + 32-char suffix, `+`→space,
  URL-decode, REVERSE the string, base64-decode → the raw GIF.** (`etoys_api.deobfuscate()`.)

## Usage

```bash
python catalog.py     # -> manifest.json  (all 5 categories, paginated, concurrent)
python download.py    # -> library/<category>/<file_id>.gif (deobfuscated) + index.csv/json
# decode.py          # deobfuscate already-downloaded raw files in place (if needed)
```

`etoys_api.py` is the reusable client (`request()`, `material_params()`, AES `enc`/`dec`, the sign).
Set `type_anim=False` in `material_params` to pull the **image** (图片) library instead of animations.

## Catalog (animations)

| category | count |
|---|---|
| daily (日常) | 212 |
| holiday (节日) | 130 |
| emoji (表情) | 163 |
| creative (创意) | 206 |
| business (商业) | 40 |
| **total** | **751** |

`library/` holds the **751 decoded 32×32 GIFs** (`<category>/<file_id>.gif`); `index.csv`/`json`
is the catalog (category, file_id, format, dims, label, source URL, local path). Re-pull/refresh
anytime with `catalog.py` + `download.py`.

## Image library (静态图片)

`python images.py` pulls the **image** tab the same way → `library_images/<category>/<file_id>.png`
+ `manifest_images.json` + `index_images.csv/json`. **352 static 32×32 PNGs:**

| category | daily | holiday | emoji | creative | business | total |
|---|---|---|---|---|---|---|
| images | 105 | 70 | 72 | 74 | 31 | **352** |

So the full e-toys catalog is **1,103 assets** (751 animations + 352 images).
