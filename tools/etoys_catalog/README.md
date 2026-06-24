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

## Captions

Every asset is named + described in `captions.json` (keyed `type/category/file_id`), and those
`name` + `description` columns are merged into `index.csv` / `index_images.csv`. Built by a vision
pass over labeled montages (`build_montage.py`). 1103/1103 assets captioned.

## Other panel sizes (16×16 / 64×64)

The same API serves a **separate catalog per panel size**. The app's `category_name` rule (see
`etoys_api.category_name_for`): 16×16 and 32×32 use `<group>_IDM` for both types; 64×64 uses
`<group>_IDM` for animations but a single `iDotMatrix` pool for images. Each size lives in its own
folders (`library_16/`, `library_images_16/`, `index_16.*`, `captions_16.json`, …; 32 keeps the
unsuffixed names). **Both the 32×32 and 16×16 catalogs are fully captioned** (name + description per asset).

**16×16 catalog — 1,099 assets** (verified `totalCount` == local):

| | daily | holiday | emoji | creative | business | total |
|---|---|---|---|---|---|---|
| animations | 220 | 172 | 169 | 238 | 43 | **842** |
| images | 86 | 49 | 50 | 53 | 19 | **257** |

## Keeping it up to date — `sync.py` (size-flexible)

```bash
python sync.py                 # size 32 (default): re-query catalog, download only new, skip existing
python sync.py --size 16       # 16×16 panel  (own library_16/ folders)
python sync.py --size 64       # 64×64 panel
python sync.py --size 16 --list  # dry-run: report catalog-vs-local counts, no downloads
```

Idempotent and safe to re-run anytime: for the chosen size it compares the server catalog
(animations + images across all 5 categories) against what's on disk and fetches only `file_id`s you
don't already have, deobfuscating them in place. It rebuilds that size's indexes, preserves existing
captions, and writes newly-fetched (un-captioned) assets to `new_assets<sfx>.json`.

Verified complete: server `totalCount` == local for every size pulled
(**32×32: 751 anim + 352 image; 16×16: 842 anim + 257 image; 0 missing**).
