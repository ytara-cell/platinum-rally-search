"""
プラチナマップ スポット画像取得ツール

指定したスポットの詳細を公開APIから取得し、含まれる画像をすべてダウンロードします。

使い方:
    python3 fetch_spot_images.py 667607              # マップ151（プラチナラリー）で検索
    python3 fetch_spot_images.py 667607 --map 151 --map 200
    python3 fetch_spot_images.py 667607 --out spot_images
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_URL = "https://platinumaps.jp"
CDN_URL = "https://cdn.platinumaps.jp/"
SPOT_DETAIL_URL = f"{BASE_URL}/map/api/maps/{{map_id}}/spot/{{spot_id}}?culture=ja"
REFERER = f"{BASE_URL}/d/platinarally"
HEADERS = {"Referer": REFERER, "User-Agent": "Mozilla/5.0", "Accept": "application/json"}

IMAGE_EXT = re.compile(r"\.(jpe?g|png|gif|webp|avif|bmp|svg)(\?|$)", re.IGNORECASE)
IMAGE_KEY = re.compile(r"image|photo|thumb|picture|icon|banner", re.IGNORECASE)


def fetch_detail(map_id: int, spot_id: int) -> dict | None:
    url = SPOT_DETAIL_URL.format(map_id=map_id, spot_id=spot_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  GET {url} -> {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  失敗: {e}")
        return None
    return data.get("spot") if isinstance(data, dict) and "spot" in data else data


def collect_image_urls(obj, key: str = "") -> list[str]:
    """JSON を再帰的に走査し、画像らしき URL を集める（出現順・重複なし）"""
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            found += collect_image_urls(v, k)
    elif isinstance(obj, list):
        for v in obj:
            found += collect_image_urls(v, key)
    elif isinstance(obj, str) and obj:
        if obj.startswith("assets/"):
            # bannerUri / thumbUri などは CDN からの相対パス
            if IMAGE_EXT.search(obj) or IMAGE_KEY.search(key) or key.endswith("Uri"):
                found.append(urljoin(CDN_URL, obj))
        elif obj.startswith(("http://", "https://", "/")) and (IMAGE_EXT.search(obj) or IMAGE_KEY.search(key)):
            found.append(urljoin(BASE_URL, obj))
    return list(dict.fromkeys(found))


def main():
    parser = argparse.ArgumentParser(description="スポット画像を取得")
    parser.add_argument("spot_id", type=int)
    parser.add_argument("--map", type=int, action="append", dest="maps",
                        help="検索するマップID（複数指定可、既定: 151）")
    parser.add_argument("--out", default="spot_images", help="保存先ディレクトリ")
    args = parser.parse_args()
    maps = args.maps or [151]

    detail, map_id = None, None
    for m in maps:
        print(f"マップ {m} でスポット {args.spot_id} を検索")
        detail = fetch_detail(m, args.spot_id)
        if detail:
            map_id = m
            break
    if not detail:
        print(f"スポット {args.spot_id} が見つかりませんでした（検索したマップ: {maps}）")
        sys.exit(1)

    out_dir = Path(args.out) / str(args.spot_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "detail.json").write_text(
        json.dumps({"mapId": map_id, "spot": detail}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"タイトル: {detail.get('title', '')}")

    urls = collect_image_urls(detail)
    print(f"画像URL: {len(urls)} 件")
    saved = []
    for i, url in enumerate(urls, 1):
        name = Path(urlparse(url).path).name or f"image_{i}"
        dest = out_dir / f"{i:02d}_{name}"
        try:
            resp = requests.get(url, headers={"Referer": REFERER, "User-Agent": "Mozilla/5.0"}, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            saved.append({"url": url, "file": dest.name})
            print(f"  保存: {dest.name} <- {url}")
        except Exception as e:
            saved.append({"url": url, "file": None, "error": str(e)})
            print(f"  失敗: {url} ({e})")

    (out_dir / "images.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
