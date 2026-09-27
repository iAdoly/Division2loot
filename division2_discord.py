from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

EVENT_JSON_URL = "https://hi-dep.github.io/division2/data/event/index.json"
HTTP_TIMEOUT = 30
SAUDI_TZ = ZoneInfo("Asia/Riyadh")

TOKEN_LABELS = {
    "ar": "Assault Rifle",
    "lmg": "LMG",
    "mmr": "Marksman Rifle",
    "pistol": "Pistol",
    "rifle": "Rifle",
    "shotgun": "Shotgun",
    "smg": "SMG",
    "mask": "Mask",
    "backpack": "Backpack",
    "chest": "Body Armor",
    "gloves": "Gloves",
    "holster": "Holster",
    "kneepads": "Kneepads",
}

LOOT_AR = {
    "Assault Rifle": "بندقية هجومية",
    "LMG": "رشاش خفيف",
    "Marksman Rifle": "بندقية قنص",
    "Pistol": "مسدس",
    "Rifle": "بندقية",
    "Shotgun": "شوتجن",
    "SMG": "رشاش خفيف صغير",
    "Mask": "قناع",
    "Backpack": "حقيبة ظهر",
    "Body Armor": "درع الصدر",
    "Gloves": "قفازات",
    "Holster": "حافظة",
    "Kneepads": "واقيات الركبة",
}

BRAND_SET_AR = {
    "5.11 Tactical": "5.11 تكتيكي",
    "Badger Tuff": "بادجر تاف",
    "Belstone Armory": "مستودع أسلحة Belstone",
    "Brazos de Arcabuz": "«برازوس دي أركابوس»",
    "Gila Guard": "غيلا غارد",
    "Improvised": "مرتجل",
    "Golan Gear Ltd": "شركة غولان المحدودة",
    "Habsburg Guard": "حرس هابسبورغ",
    "Lengmo": "لينغمو",
    "Palisade Steelworks": "مصانع الصلب الحاجز",
    "Uzina Getica": "أوزينا جيتيكا",
    "Yaahl Gear": "عتاد ياهل",
    "Alps Summit Armaments": "تسليح قمة جبال الألب",
    "China Light Industries": "شركة الصناعات الصينية الخفيفة",
    "Edelweiss GPz": "«إيدلفايس» GPz",
    "Electrique": "الكهربائي",
    "Empress International": "الإمبراطورة العالمية",
    "Hana-U Corporation": "مؤسسة هانا-يو",
    "Murakami Industries": "مصانع موراكامي",
    "Richter & Kaiser GmbH": "«ريختر وكايزر» GmbH",
    "Shiny Monkey": "عتاد القرد اللامع",
    "Wyvern Wear": "وايفرن وير",
    "Airaldi Holdings": "إيرالدي هولدينغز",
    "Unit Alloys": "سبائك الوحدة",
    "Ceska Vyroba s.r.o.": "شركة الإنتاج التشيكي المحدودة",
    "Douglas & Harding": "«دوغلاس وهاردينغ»",
    "Fenris Group AB": "مجموعة فينريس AB",
    "Grupo Sombra S.A.": "المجموعة العامة المحدودة سومبرا",
    "Imminence Armaments": "«إيمينينس أرمامنتس» (AI)",
    "Legatus S.p.A": "«ليغاتوس» S.p.A",
    "Overlord Armaments": "أوفرلورد أرمامنتس",
    "Petrov Defense Group": "مجموعة بتروف للدفاع",
    "Providence Defense": "بروفيدانس ديفينس",
    "Sokolov Concern": "تهديد «سكولفو»",
    "Urban Lookout": "المراقب المدني",
    "Royal Works": "المشروعات الملكية",
    "Walker, Harris & Co.": "ووكر وهاريس وشركائهما",
    "Zwiadowka Sp. z o.o.": "Zwiadowka Sp. z o.o.",
}

GEAR_SET_AR = {
    "Aces & Eights": "آحاد وثمانيات",
    "Aegis": "إيجيس",
    "Breaking Point": "حد الانهيار",
    "Cavalier": "الفارس",
    "Concentrated Company": "المجموعة المركزية",
    "Core Strength": "قوة السمة الأساسية",
    "Eclipse Protocol": "بروتوكول الكسوف",
    "Ember Engine": "محرك الجمر",
    "Foundry Bulwark": "الدرع المحصن المسبك",
    "Future Initiative": "مبادرة مستقبلية",
    "Hard Wired": "غير قابل للتعديل",
    "Heartbreaker": "محطم القلوب",
    "Hotshot": "إصابة في الرأس",
    "Hunter's Fury": "غضب الصياد",
    "Measured Assembly": "التجمع المدروس (MA)",
    "Negotiator's Dilemma": "معضلة المفاوض",
    "Ongoing Directive": "التوجيهات الحالية",
    "Ortiz: Exuro": "إكسورو",
    "Ortiz: Reficere": "«أورتيز»: إعادة الترميم",
    "Refactor": "إعادة تنظيم",
    "Rigger": "عامل فني",
    "Striker's Battlegear": "عتاد سترايكر القتالي",
    "Tip of the Spear": "رأس الحربة",
    "Tipping Scales": "اختلال الموازين",
    "True Patriot": "الوطني الحق",
    "Umbra Initiative": "مبادرة «أومبرا»",
    "Virtuoso": "فيرتشوسو",
}

LOOT_NAME_ALIASES = {
    "China Light Industries Corporation": "China Light Industries",
    "Legatus S.p.A.": "Legatus S.p.A",
    "Česká Výroba s.r.o.": "Ceska Vyroba s.r.o.",
}


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def target_loot_day() -> str:
    return datetime.now(SAUDI_TZ).strftime("%Y-%m-%d")


def normalize_label(value: Any) -> str:
    raw = str(value or "").strip()
    label = TOKEN_LABELS.get(raw.lower(), raw or "N/A")
    return LOOT_NAME_ALIASES.get(label, label)


def bilingual_loot(label: str) -> str:
    canonical = LOOT_NAME_ALIASES.get(label, label)
    arabic = (
        LOOT_AR.get(canonical)
        or BRAND_SET_AR.get(canonical)
        or GEAR_SET_AR.get(canonical)
    )
    return f"{arabic} | {canonical}" if arabic else canonical


def fetch_event() -> dict[str, Any]:
    # Avoid stale GitHub Pages/CDN responses when the daily loot rotates.
    cache_buster = int(datetime.now(SAUDI_TZ).timestamp())
    response = requests.get(
        EVENT_JSON_URL,
        params={"_": cache_buster},
        timeout=HTTP_TIMEOUT,
        headers={
            "User-Agent": "Division2loot/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    response.raise_for_status()
    return response.json()


def _parse_day(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    return None


def _entry_week_key(entry: dict[str, Any]) -> datetime | None:
    return _parse_day(entry.get("week"))


def select_event_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    escalation = data.get("Escalation")
    if not isinstance(escalation, list):
        raise RuntimeError("Escalation data is missing.")

    expected_day = target_loot_day()
    expected_dt = _parse_day(expected_day)
    if expected_dt is None:
        raise RuntimeError(f"Could not parse expected target-loot day: {expected_day}")

    valid_entries: list[dict[str, Any]] = []

    for entry in escalation:
        if not isinstance(entry, dict):
            continue

        missions = entry.get("missions")
        rows = entry.get("target_loot_by_day")
        if not isinstance(missions, list) or not missions:
            continue
        if not isinstance(rows, list) or not rows:
            continue

        usable_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            loot = row.get("target_loot")
            if not isinstance(loot, list) or not loot:
                continue
            usable_rows.append(row)

        if usable_rows:
            valid_entries.append({**entry, "_usable_rows": usable_rows})

    if not valid_entries:
        raise RuntimeError("No usable escalation blocks found.")

    # 1) If today's row exists, use the newest block that contains it.
    exact_matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for entry in valid_entries:
        for row in entry["_usable_rows"]:
            if str(row.get("day", "")).strip() == expected_day:
                exact_matches.append((entry, row))

    if exact_matches:
        entry, row = max(
            exact_matches,
            key=lambda item: (
                _entry_week_key(item[0]) or datetime.min,
                max(
                    (
                        _parse_day(r.get("day")) or datetime.min
                        for r in item[0]["_usable_rows"]
                    ),
                    default=datetime.min,
                ),
            ),
        )
    else:
        # 2) No exact row: choose the CURRENT/LATEST escalation block first.
        #    Never select a loot row globally and then combine it with another block's missions.
        dated_entries = [
            entry
            for entry in valid_entries
            if _entry_week_key(entry) is not None
            and _entry_week_key(entry) <= expected_dt
        ]

        if dated_entries:
            entry = max(dated_entries, key=lambda item: _entry_week_key(item) or datetime.min)
        else:
            # Fallback when the source omits/unparseably formats "week":
            # choose the block whose own latest row is newest.
            entry = max(
                valid_entries,
                key=lambda item: max(
                    (
                        _parse_day(r.get("day")) or datetime.min
                        for r in item["_usable_rows"]
                    ),
                    default=datetime.min,
                ),
            )

        # Once the block is chosen, select loot ONLY from that same block.
        dated_rows = [
            row
            for row in entry["_usable_rows"]
            if _parse_day(row.get("day")) is not None
        ]
        eligible_rows = [
            row
            for row in dated_rows
            if (_parse_day(row.get("day")) or datetime.min) <= expected_dt
        ]

        if eligible_rows:
            row = max(
                eligible_rows,
                key=lambda item: _parse_day(item.get("day")) or datetime.min,
            )
        elif dated_rows:
            row = max(
                dated_rows,
                key=lambda item: _parse_day(item.get("day")) or datetime.min,
            )
        else:
            row = entry["_usable_rows"][-1]

    missions = [str(item).strip() for item in entry.get("missions", [])]
    loot = [normalize_label(item) for item in row.get("target_loot", [])]

    if len(missions) != len(loot):
        raise RuntimeError(
            "Escalation source mismatch: "
            f"{len(missions)} missions but {len(loot)} target-loot entries "
            f"in week {entry.get('week', 'unknown')} / day {row.get('day', 'unknown')}."
        )

    return {
        "day": expected_day,
        "source_day": str(row.get("day", "")).strip() or "missing",
        "week": str(entry.get("week", "")).strip() or "missing",
        "missions": [
            {"mission": mission, "loot": target}
            for mission, target in zip(missions, loot)
        ],
    }

def loot_icon(label: str, config: dict[str, Any]) -> str:
    emojis = config.get("loot_emojis", {})
    if not isinstance(emojis, dict):
        return ""

    canonical = LOOT_NAME_ALIASES.get(label, label)
    return str(emojis.get(canonical) or emojis.get(label) or "")


def build_message(event: dict[str, Any], config: dict[str, Any]) -> str:
    lines = [
        "**Escalation Target Loot | غنائم التصعيد**",
        f"**Target Loot Date | تاريخ الغنائم:** {event['day']}",
        "",
    ]

    for row in event["missions"]:
        icon = loot_icon(row["loot"], config)
        prefix = f"{icon} " if icon else ""
        lines.append(
            f"**{row['mission']}** — {prefix}{bilingual_loot(row['loot'])}"
        )
        lines.append("")

    lines.append("-# Source: hi-dep Division 2")
    return "\n".join(lines).strip()[:2000]


def send_webhook(content: str, config: dict[str, Any]) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL secret is not configured.")

    response = requests.post(
        webhook_url,
        json={
            "username": str(config.get("discord_username", "Division 2 Loot")),
            "content": content,
        },
        timeout=HTTP_TIMEOUT,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Discord webhook failed: HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )


def main() -> int:
    config = load_config()
    event = select_event_snapshot(fetch_event())
    send_webhook(build_message(event, config), config)
    print(
        "Posted Escalation Target Loot "
        f"for {event['day']} "
        f"(source week: {event['week']}, source day: {event['source_day']})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
