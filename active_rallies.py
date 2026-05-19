"""
プラチナラリー 開催中スタンプラリー取得ツール

現在開催中のスタンプラリーの一覧とリンクを取得します。

使い方:
    python3 active_rallies.py          # 開催中のみ表示
    python3 active_rallies.py --days 7 # 7日以内に開始/終了も含む
    python3 active_rallies.py --json   # JSON形式で出力

仕組み:
    1. platinumaps.jp の platinarally マップAPI からスポット一覧を取得
    2. 各スポットの詳細（開催日・URL）を並行取得
    3. 今日の日付でフィルタリングして表示
"""
import asyncio
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import requests as _requests
    _SESSION = _requests.Session()
    def fetch_url(url: str) -> dict | None:
        try:
            resp = _SESSION.get(url, headers={"Referer": REFERER, "User-Agent": "Mozilla/5.0"}, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None
except ImportError:
    import urllib.request
    import ssl
    _SSL_CTX = ssl.create_default_context()
    try:
        import certifi
        _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        _SSL_CTX.check_hostname = False
        _SSL_CTX.verify_mode = ssl.CERT_NONE

    def fetch_url(url: str) -> dict | None:
        req = urllib.request.Request(
            url, headers={"Referer": REFERER, "User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

# ─── API エンドポイント ────────────────────────────────────────
BASE_URL = "https://platinumaps.jp"
SPOTS_URL = f"{BASE_URL}/map/maps/151/spots?culture=ja"
SPOT_DETAIL_URL = f"{BASE_URL}/map/api/maps/151/spot/{{spot_id}}?culture=ja"
REFERER = f"{BASE_URL}/d/platinarally"
SHOWCASE_URL = f"{BASE_URL}/d/platinarally?spot={{spot_id}}"

# カスタムプロパティID
PROP_ORGANIZER = 45   # 主催
PROP_DATE = 46        # 開催日
PROP_REWARD = 47      # 特典方式
PROP_URL = 48         # URL
PROP_STAMP = 49       # スタンプ方式

CONCURRENCY = 20  # 並行リクエスト数



def parse_event_dates(text: str) -> tuple[date | None, date | None]:
    """
    開催日テキストをパースして (開始日, 終了日) を返す。

    対応フォーマット:
      "2026年5月1日 - 2026年6月30日"
      "2026年8月20日 - 11月30日"    ← 終了年省略パターン
      "2026月3月4日 - 2026年3月31日" ← 月/年の誤記にも対応
      "2025年3月1日〜2025年5月6日"
      "2026/5/1〜2026/6/30"
    """
    if not text:
        return None, None

    # 区切り文字を統一
    text = text.replace("〜", " - ").replace("～", " - ").replace("–", " - ").replace("—", " - ")

    import calendar

    def to_date(y, m, d):
        try:
            y, m, d = int(y), int(m), int(d)
            # 無効な日（例: 6月31日 → 6月30日に丸める）
            last_day = calendar.monthrange(y, m)[1]
            d = min(d, last_day)
            return date(y, m, d)
        except (ValueError, TypeError):
            return None

    # YYYY年M月D日 + （YYYY年）M月D日 の組み合わせ
    # まず完全な日付（年月日）を探す
    full_jp = r'(\d{4})[年月](\d{1,2})[月日](\d{1,2})日?'
    # 年なし終了日パターン: M月D日
    short_jp = r'(\d{1,2})月(\d{1,2})日?'

    full_matches = list(re.finditer(full_jp, text))

    if len(full_matches) >= 2:
        start = to_date(*full_matches[0].groups())
        end = to_date(*full_matches[1].groups())
        return start, end

    if len(full_matches) == 1:
        start = to_date(*full_matches[0].groups())
        start_year = full_matches[0].group(1)
        # 区切り文字より後の部分で年なし終了日を探す
        after = text[full_matches[0].end():]
        short = re.search(short_jp, after)
        if short:
            end = to_date(start_year, short.group(1), short.group(2))
            return start, end
        # 単独日付 → その日のみの1日イベント
        return start, start

    # スラッシュ形式 YYYY/M/D
    slash_pattern = r'(\d{4})/(\d{1,2})/(\d{1,2})'
    slash_matches = re.findall(slash_pattern, text)
    if len(slash_matches) >= 2:
        return to_date(*slash_matches[0]), to_date(*slash_matches[1])
    if len(slash_matches) == 1:
        return to_date(*slash_matches[0]), None

    return None, None


def is_active(start: date | None, end: date | None, today: date, margin_days: int = 0) -> bool:
    """今日がイベント期間内かどうかを判定"""
    if start is None and end is None:
        return False
    margin = timedelta(days=margin_days)
    if start and today < start - margin:
        return False
    if end is None:
        # 終了日不明だが開始日あり → 開始日が未来なら含める（進行中かもしれない）
        return start is not None and today >= start
    if today > end + margin:
        return False
    return True


async def fetch_spot_detail_async(spot_id: int, semaphore: asyncio.Semaphore) -> dict | None:
    """非同期でスポット詳細を取得"""
    async with semaphore:
        loop = asyncio.get_event_loop()
        url = SPOT_DETAIL_URL.format(spot_id=spot_id)
        data = await loop.run_in_executor(None, fetch_url, url)
        if data and "spot" in data:
            return data["spot"]
        return None


def extract_custom_props(spot: dict) -> dict:
    """カスタムプロパティを辞書に変換"""
    props = {}
    for cp in spot.get("customProperties") or []:
        pid = cp.get("customPropertyId")
        val = cp.get("textValue") or ""
        props[pid] = val
    return props


async def get_active_rallies(margin_days: int = 0) -> list[dict]:
    """
    現在開催中のスタンプラリー一覧を返す。
    margin_days: 終了から何日以内まで含めるか（デフォルト0）
    """
    today = date.today()
    print(f"基準日: {today}", file=sys.stderr)

    # Step 1: スポット一覧取得
    print("スポット一覧を取得中...", file=sys.stderr)
    data = fetch_url(SPOTS_URL)
    if not data:
        print("ERROR: スポット一覧の取得に失敗しました", file=sys.stderr)
        return []

    all_spots = data.get("spots", [])
    print(f"  {len(all_spots)} スポット取得", file=sys.stderr)

    # Step 2: 最近更新されたスポットのみ詳細取得（速度最適化）
    # 直近3年以内に更新されたもののみ対象
    cutoff_year = today.year - 3
    candidate_spots = [
        s for s in all_spots
        if s.get("updatedAt", "")[:4] >= str(cutoff_year)
    ]
    print(f"  直近更新 {len(candidate_spots)} 件の詳細を取得中...", file=sys.stderr)

    # Step 3: 並行で詳細取得
    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [
        fetch_spot_detail_async(s["id"], semaphore)
        for s in candidate_spots
    ]
    results = await asyncio.gather(*tasks)

    # Step 4: 期間フィルタリング
    active = []
    no_date_count = 0

    for spot, detail in zip(candidate_spots, results):
        if detail is None:
            continue

        props = extract_custom_props(detail)
        date_str = props.get(PROP_DATE, "")
        start, end = parse_event_dates(date_str)

        if start is None and end is None:
            no_date_count += 1
            continue

        if not is_active(start, end, today, margin_days):
            continue

        organizer = re.sub(r"\s*様\s*$", "", props.get(PROP_ORGANIZER, "")).strip()
        url = props.get(PROP_URL, "")
        stamp_method = props.get(PROP_STAMP, "")
        reward_method = props.get(PROP_REWARD, "")

        # カスタムボタンのリンク（事例紹介URL）
        case_url = ""
        for btn in detail.get("customButtons") or []:
            link = btn.get("linkUrl", "")
            if link and "stamprally.digital" in link:
                case_url = link
                break

        # ショーケースページへのリンク（このラリーの詳細マップ）
        showcase_link = SHOWCASE_URL.format(spot_id=spot["id"])

        active.append({
            "id": spot["id"],
            "title": detail.get("title", spot.get("title", "")),
            "organizer": organizer,
            "startDate": start.isoformat() if start else "",
            "endDate": end.isoformat() if end else "",
            "dateText": date_str,
            "stampMethod": stamp_method,
            "rewardMethod": reward_method,
            "url": url,              # 主催者サイトURL（property 48）
            "caseUrl": case_url,     # 事例紹介URL
            "mapLink": showcase_link,  # プラチナラリーマップ上での表示リンク
            "address": detail.get("address", ""),
        })

    # 開始日順にソート
    active.sort(key=lambda x: (x["startDate"], x["endDate"]))

    print(f"  開催中: {len(active)} 件 / 日付なし: {no_date_count} 件", file=sys.stderr)
    return active


def format_rally(r: dict, idx: int) -> str:
    """1件のラリーを整形テキストで返す"""
    lines = [f"\n[{idx}] {r['title']}"]
    if r["organizer"]:
        lines.append(f"  主催: {r['organizer']}")
    lines.append(f"  期間: {r['dateText']}")
    if r["stampMethod"]:
        lines.append(f"  スタンプ: {r['stampMethod']}")
    if r["rewardMethod"]:
        lines.append(f"  特典: {r['rewardMethod']}")
    if r["address"]:
        lines.append(f"  場所: {r['address'][:60]}")
    lines.append(f"  マップ: {r['mapLink']}")
    if r["url"]:
        lines.append(f"  URL: {r['url']}")
    if r["caseUrl"]:
        lines.append(f"  事例: {r['caseUrl']}")
    return "\n".join(lines)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="プラチナラリー 開催中スタンプラリー取得ツール")
    parser.add_argument("--days", type=int, default=0,
                        help="終了後何日以内まで含めるか (デフォルト: 0)")
    parser.add_argument("--json", action="store_true",
                        help="JSON形式で出力")
    parser.add_argument("--save", type=str, default="",
                        help="結果をファイルに保存 (例: --save output.json)")
    args = parser.parse_args()

    rallies = await get_active_rallies(margin_days=args.days)

    if args.json or args.save:
        output = {
            "fetchedAt": datetime.now().isoformat(),
            "today": date.today().isoformat(),
            "total": len(rallies),
            "rallies": rallies,
        }
        if args.save:
            path = Path(args.save)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"保存しました: {path}")
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        if not args.json:
            print(f"\n{len(rallies)} 件のスタンプラリーを {args.save} に保存しました。")
    else:
        print(f"\n{'='*60}")
        print(f"現在開催中のプラチナラリー: {len(rallies)} 件")
        print(f"基準日: {date.today().isoformat()}")
        print('='*60)
        for i, r in enumerate(rallies, 1):
            print(format_rally(r, i))
        print(f"\n{'='*60}")
        print(f"合計 {len(rallies)} 件")


if __name__ == "__main__":
    asyncio.run(main())
