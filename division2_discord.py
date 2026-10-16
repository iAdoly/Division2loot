from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / ".state" / "target_loot.json"

TARGET_LOOT_URL = "https://prototrack.gg/target-loot/target-loot-current.txt"
TARGET_LOOT_PAGE_URL = "https://prototrack.gg/target-loot/target-loot.php"
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

PROTOTRACK_LABEL_ALIASES = {
    "Assault Rifles": "Assault Rifle",
    "Assault Rifle": "Assault Rifle",
    "Light Machine Guns": "LMG",
    "LMGs": "LMG",
    "LMG": "LMG",
    "Marksman Rifles": "Marksman Rifle",
    "MMRs": "Marksman Rifle",
    "Marksman Rifle": "Marksman Rifle",
    "Pistols": "Pistol",
    "Pistol": "Pistol",
    "Rifles": "Rifle",
    "Rifle": "Rifle",
    "Shotguns": "Shotgun",
    "Shotgun": "Shotgun",
    "Submachine Guns": "SMG",
    "SMGs": "SMG",
    "SMG": "SMG",
    "Masks": "Mask",
    "Mask": "Mask",
    "Backpacks": "Backpack",
    "Backpack": "Backpack",
    "Chest Pieces": "Body Armor",
    "Chest": "Body Armor",
    "Body Armor": "Body Armor",
    "Gloves": "Gloves",
    "Holsters": "Holster",
    "Holster": "Holster",
    "Kneepads": "Kneepads",
}


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def target_loot_day() -> str:
    return datetime.now(SAUDI_TZ).strftime("%Y-%m-%d")


def event_signature(event: dict[str, Any]) -> str:
    payload = {
        "day": str(event["source_day"]),
        "missions": [
            {
                "mission": str(row["mission"]),
                "loot": str(row["loot"]),
            }
            for row in event["missions"]
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return state if isinstance(state, dict) else {}


def save_state(event: dict[str, Any], signature: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "source_day": str(event["source_day"]),
        "signature": signature,
        "source_last_updated": event.get("source_last_updated"),
        "saved_at": datetime.now(SAUDI_TZ).isoformat(timespec="seconds"),
    }
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_label(value: Any) -> str:
    raw = str(value or "").strip()
    label = TOKEN_LABELS.get(raw.lower(), raw or "N/A")
    label = PROTOTRACK_LABEL_ALIASES.get(label, label)
    return LOOT_NAME_ALIASES.get(label, label)


def bilingual_loot(label: str) -> str:
    canonical = LOOT_NAME_ALIASES.get(label, label)
    arabic = (
        LOOT_AR.get(canonical)
        or BRAND_SET_AR.get(canonical)
        or GEAR_SET_AR.get(canonical)
    )
    return f"{arabic} | {canonical}" if arabic else canonical


def fetch_event() -> str:
    # ProtoTrack exposes a public Static Text endpoint specifically suited to
    # automated consumers. Add a cache-buster so each scheduled run gets the
    # freshest published rotation.
    response = requests.get(
        TARGET_LOOT_URL,
        params={"ts": int(datetime.now(SAUDI_TZ).timestamp())},
        timeout=HTTP_TIMEOUT,
        headers={
            "User-Agent": "Division2loot/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Accept": "text/plain,*/*;q=0.8",
        },
    )
    response.raise_for_status()

    text = response.text.strip()
    if not text:
        raise RuntimeError("ProtoTrack returned an empty Target Loot response.")

    return text


def select_event_snapshot(text: str) -> dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    date_match = re.search(
        r"(?:Daily\s+)?Escalation\s+Target\s+Loot\s+Date:\s*(\d{4}-\d{2}-\d{2})",
        normalized,
        flags=re.IGNORECASE,
    )
    if not date_match:
        raise RuntimeError("Could not find the ProtoTrack Target Loot date.")

    source_day = date_match.group(1)

    section_match = re.search(
        r"Missions:\s*(.*?)\s*Vendor\s+Caches:",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        raise RuntimeError("Could not find the ProtoTrack Missions section.")

    mission_section = section_match.group(1).strip()
    parts = re.split(r"(?:^|\s)-\s+", mission_section)

    missions: list[dict[str, str]] = []
    for part in parts:
        item = part.strip()
        if not item or ":" not in item:
            continue

        mission, loot = item.split(":", 1)
        mission = mission.strip()
        loot = loot.strip()

        if mission and loot:
            missions.append({
                "mission": mission,
                "loot": normalize_label(loot),
            })

    if len(missions) != 5:
        raise RuntimeError(
            f"ProtoTrack source format changed: expected 5 missions, found {len(missions)}."
        )

    last_updated_match = re.search(
        r"Last\s+updated:\s*([^\n]+)",
        normalized,
        flags=re.IGNORECASE,
    )

    return {
        "day": source_day,
        "source_day": source_day,
        "source_last_updated": (
            last_updated_match.group(1).strip()
            if last_updated_match
            else None
        ),
        "week": "ProtoTrack",
        "missions": missions,
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

    lines.append("-# Source: ProtoTrack.gg")
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


def send_status_safely(content: str, config: dict[str, Any]) -> None:
    try:
        send_webhook(content, config)
    except Exception as status_exc:
        print(
            f"WARNING: Could not send Discord status message: {status_exc}",
            file=sys.stderr,
        )


def main() -> int:
    config = load_config()
    today = target_loot_day()
    force_resend = os.environ.get("FORCE_RESEND", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    try:
        event = select_event_snapshot(fetch_event())
    except Exception as exc:
        reason = str(exc).replace("`", "'").strip()[:350] or "Unknown error"
        send_status_safely(
            "\n".join(
                [
                    "⚠️ **Target Loot update failed**",
                    "Could not load today's Target Loot from ProtoTrack.",
                    "**No previous-day loot was posted.**",
                    f"Reason: `{reason}`",
                ]
            ),
            config,
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    source_day = str(event["source_day"])

    if source_day < today and not force_resend:
        lines = [
            "ℹ️ **Target Loot not updated yet**",
            f"ProtoTrack is still showing **{source_day}**.",
            f"Expected today: **{today}**.",
            "**No previous-day loot was posted.**",
        ]
        if event.get("source_last_updated"):
            lines.append(
                f"Source last updated: **{event['source_last_updated']}**"
            )
        send_status_safely("\n".join(lines), config)
        print(
            "Skipped stale Target Loot: "
            f"source day {source_day}, expected {today}."
        )
        return 0

    if source_day < today and force_resend:
        print(
            "FORCE_RESEND enabled: manually resending ProtoTrack source day "
            f"{source_day} although current Saudi date is {today}."
        )

    if source_day > today:
        message = (
            "ProtoTrack returned an unexpected future Target Loot date: "
            f"{source_day} (expected {today})."
        )
        send_status_safely(
            "\n".join(
                [
                    "⚠️ **Target Loot data is invalid**",
                    message,
                    "**No Target Loot was posted.**",
                ]
            ),
            config,
        )
        print(f"ERROR: {message}", file=sys.stderr)
        return 1

    signature = event_signature(event)
    state = load_state()

    if (
        not force_resend
        and state.get("source_day") == source_day
        and state.get("signature") == signature
    ):
        lines = [
            "ℹ️ **No new Target Loot update**",
            "The latest version is already loaded.",
            f"Date: **{source_day}**",
        ]
        if event.get("source_last_updated"):
            lines.append(
                f"Source last updated: **{event['source_last_updated']}**"
            )
        send_status_safely("\n".join(lines), config)
        print(
            "Skipped duplicate Target Loot version "
            f"for {source_day} ({signature[:12]})."
        )
        return 0

    send_webhook(build_message(event, config), config)
    save_state(event, signature)
    print(
        "Posted Escalation Target Loot "
        f"for {event['day']} "
        f"(source week: {event['week']}, source day: {event['source_day']}, "
        f"signature: {signature[:12]})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
