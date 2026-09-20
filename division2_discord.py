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


def saudi_today() -> str:
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
    response = requests.get(
        EVENT_JSON_URL,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "Division2loot/1.0"},
    )
    response.raise_for_status()
    return response.json()


def select_event_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    escalation = data.get("Escalation")
    if not isinstance(escalation, list):
        raise RuntimeError("Escalation data is missing.")

    candidates: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    for entry in escalation:
        if not isinstance(entry, dict):
            continue

        rows = entry.get("target_loot_by_day")
        if not isinstance(rows, list):
            continue

        for row in rows:
            if not isinstance(row, dict):
                continue

            day = str(row.get("day", "")).strip()
            if day:
                candidates.append((day, entry, row))

    if not candidates:
        raise RuntimeError("No escalation target-loot rows found.")

    today = saudi_today()
    exact = [item for item in candidates if item[0] == today]
    day, entry, row = exact[0] if exact else max(candidates, key=lambda item: item[0])

    missions = [str(item).strip() for item in entry.get("missions", [])]
    loot = [normalize_label(item) for item in row.get("target_loot", [])]

    return {
        "day": day,
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
            f"-# **{row['mission']}** — {prefix}{bilingual_loot(row['loot'])}"
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
    print(f"Posted Escalation Target Loot for {event['day']}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
