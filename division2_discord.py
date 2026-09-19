from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state.json"

EVENT_URL = "https://hi-dep.github.io/division2/?view=event&lang=en"
EVENT_JSON_URL = "https://hi-dep.github.io/division2/data/event/index.json"
VENDOR_URL = "https://hi-dep.github.io/division2/?view=vendor&lang=en"

TIMEOUT_MS = 45_000
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

# Gear-mod max values from div2hub/game-data.
# Values with percentages use percentage points (e.g. 12.0 = 12%).
MOD_MAX = {
    "Critical Hit Chance": 6.0,
    "Critical Hit Damage": 12.0,
    "Headshot Damage": 10.0,
    "Armor on Kill": 18935.0,
    "Protection from Elites": 13.0,
    "Burn Resistance": 10.0,
    "Bleed Resistance": 10.0,
    "Shock Resistance": 10.0,
    "Disrupt Resistance": 10.0,
    "Blind/Deaf Resistance": 10.0,
    "Disorient Resistance": 10.0,
    "Ensnare Resistance": 10.0,
    "Pulse Resistance": 10.0,
    "Incoming Repairs": 20.0,
    "Skill Haste": 12.0,
    "Skill Duration": 10.0,
    "Repair Skills": 20.0,
}

MOD_AR = {
    "Critical Hit Chance": "فرصة الضربة الحرجة",
    "Critical Hit Damage": "ضرر الضربة الحرجة",
    "Headshot Damage": "ضرر إصابة الرأس",
    "Armor on Kill": "درع عند القتل",
    "Protection from Elites": "حماية من النخبة",
    "Burn Resistance": "مقاومة الحرق",
    "Bleed Resistance": "مقاومة النزيف",
    "Shock Resistance": "مقاومة الصعق",
    "Disrupt Resistance": "مقاومة التعطيل",
    "Blind/Deaf Resistance": "مقاومة العمى/الصمم",
    "Disorient Resistance": "مقاومة التشويش",
    "Ensnare Resistance": "مقاومة التقييد",
    "Pulse Resistance": "مقاومة النبض",
    "Incoming Repairs": "الإصلاحات الواردة",
    "Skill Haste": "سرعة المهارة",
    "Skill Duration": "مدة المهارة",
    "Repair Skills": "إصلاح المهارات",
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

VENDOR_AR = {
    "White House": "البيت الأبيض",
    "Clan": "العشيرة",
    "Countdown": "كاونت داون",
    "The Campus": "الحرم",
    "The Theater": "المسرح",
    "Castle": "القلعة",
    "Cassie": "كاسي",
    "DZ East": "المنطقة المظلمة الشرقية",
    "DZ South": "المنطقة المظلمة الجنوبية",
    "DZ West": "المنطقة المظلمة الغربية",
    "Haven": "هافن",
    "Benitez": "بنيتيز",
    "Danny": "داني",
    "Vendor": "البائع",
}

ALIASES = {
    "critical hit chance": "Critical Hit Chance",
    "critical hit damage": "Critical Hit Damage",
    "headshot damage": "Headshot Damage",
    "armor on kill": "Armor on Kill",
    "protection from elites": "Protection from Elites",
    "burn resistance": "Burn Resistance",
    "bleed resistance": "Bleed Resistance",
    "shock resistance": "Shock Resistance",
    "disrupt resistance": "Disrupt Resistance",
    "blind/deaf resistance": "Blind/Deaf Resistance",
    "blind deaf resistance": "Blind/Deaf Resistance",
    "disorient resistance": "Disorient Resistance",
    "ensnare resistance": "Ensnare Resistance",
    "pulse resistance": "Pulse Resistance",
    "incoming repairs": "Incoming Repairs",
    "skill haste": "Skill Haste",
    "skill duration": "Skill Duration",
    "repair skills": "Repair Skills",
}

PERCENT_RE = re.compile(r"(?<!\d)(\d{1,2}(?:\.\d+)?)\s*%")
NUMBER_RE = re.compile(r"(?<!\d)(\d{1,5}(?:\.\d+)?)(?!\d)")

# Armor/gear mods only. These labels are used to prove that a stat belongs to
# an actual Gear Mod card/item and not to an attribute rolled on normal gear.
GEAR_MOD_MARKERS = (
    "gear mod",
    "gear-mod",
    "gear system mod",
    "gear protocol mod",
    "offensive system",
    "defensive system",
    "utility system",
    "offensive protocol",
    "defensive protocol",
    "utility protocol",
)

# Explicitly exclude mods that belong to skills themselves.
SKILL_MOD_MARKERS = (
    "skill mod",
    "skill-mod",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def saudi_now() -> datetime:
    return datetime.now(SAUDI_TZ)


def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_label(value: Any) -> str:
    raw = str(value or "").strip()
    label = TOKEN_LABELS.get(raw.lower(), raw or "N/A")
    return LOOT_NAME_ALIASES.get(label, label)


def bilingual_loot(label: str) -> str:
    canonical = LOOT_NAME_ALIASES.get(label, label)
    ar = LOOT_AR.get(canonical) or BRAND_SET_AR.get(canonical) or GEAR_SET_AR.get(canonical)
    return f"{ar} | {canonical}" if ar else canonical


def bilingual_mod(name: str) -> str:
    ar = MOD_AR.get(name)
    return f"{ar} | {name}" if ar else name


def bilingual_vendor(name: str) -> str:
    ar = VENDOR_AR.get(name)
    return f"{ar} | {name}" if ar else name


def fetch_event() -> Dict[str, Any]:
    r = requests.get(EVENT_JSON_URL, timeout=HTTP_TIMEOUT, headers={"User-Agent": "Division2loot/1.0"})
    r.raise_for_status()
    return r.json()


def select_event_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    escalation = data.get("Escalation")
    if not isinstance(escalation, list):
        raise RuntimeError("Escalation data is missing.")

    today = saudi_now().strftime("%Y-%m-%d")
    candidates: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []

    for entry in escalation:
        if not isinstance(entry, dict):
            continue
        rows = entry.get("target_loot_by_day")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                day = str(row.get("day", "")).strip()
                if day:
                    candidates.append((day, entry, row))

    if not candidates:
        raise RuntimeError("No escalation target-loot rows found.")

    exact = [x for x in candidates if x[0] == today]
    day, entry, row = exact[0] if exact else max(candidates, key=lambda x: x[0])

    missions = [str(x).strip() for x in entry.get("missions", [])]
    loot = [normalize_label(x) for x in row.get("target_loot", [])]
    pairs = []
    for idx in range(min(len(missions), len(loot))):
        pairs.append({"mission": missions[idx], "loot": loot[idx]})

    return {
        "week": str(entry.get("week", "")).strip(),
        "day": day,
        "missions": pairs,
        "prototype_gear_cache": normalize_label(row.get("prototype_gear_cache", "")),
        "prototype_weapon_cache": normalize_label(row.get("prototype_weapon_cache", "")),
    }


def canonical_mod_name(text: str) -> Optional[str]:
    lower = text.lower()
    for alias, canonical in ALIASES.items():
        if alias in lower:
            return canonical
    return None


def extract_mod_value(text: str, mod_name: str) -> Optional[float]:
    max_value = MOD_MAX[mod_name]

    if mod_name == "Armor on Kill":
        values = [float(x) for x in NUMBER_RE.findall(text.replace(",", ""))]
        valid = [v for v in values if 0 < v <= max_value * 1.15]
        return max(valid) if valid else None

    values = [float(x) for x in PERCENT_RE.findall(text)]
    valid = [v for v in values if 0 < v <= max_value * 1.15]
    return max(valid) if valid else None


def collect_from_text(text: str, ratio: float, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
    lines = [re.sub(r"\\s+", " ", line).strip() for line in text.splitlines()]
    lines = [x for x in lines if x]
    found: List[Dict[str, Any]] = []

    vendor_names = {
        "White House",
        "Clan",
        "Countdown",
        "The Campus",
        "The Theater",
        "Castle",
        "Cassie",
        "DZ East",
        "DZ South",
        "DZ West",
        "Haven",
        "Benitez",
        "Danny",
    }

    current_vendor = "Vendor"

    for i, line in enumerate(lines):
        if line in vendor_names:
            current_vendor = line
            continue

        # On the rendered vendor page, armor Gear Mods are labeled exactly
        # "MOD". Skill attachments are labeled "Drone MOD", "Turret MOD", etc.
        if line != "MOD":
            continue

        if i + 1 >= len(lines):
            continue

        stat_line = lines[i + 1]
        mod_name = canonical_mod_name(stat_line)
        if not mod_name:
            continue

        value = extract_mod_value(stat_line, mod_name)
        if value is None:
            continue

        minimum = float(thresholds.get(mod_name, MOD_MAX[mod_name] * ratio))
        if value + 1e-9 < minimum:
            continue

        found.append({
            "name": mod_name,
            "value": value,
            "max": MOD_MAX[mod_name],
            "vendor": current_vendor,
            "source": VENDOR_URL,
        })

    return found


def fetch_vendor_rendered() -> Tuple[str, List[Tuple[str, Any]]]:
    # Playwright is loaded only when Vendor is enabled, keeping daily
    # Escalation runs lightweight.
    from playwright.sync_api import sync_playwright

    json_payloads: List[Tuple[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1600})

        def capture(response: Any) -> None:
            try:
                ctype = (response.headers.get("content-type") or "").lower()
                if "json" not in ctype:
                    return
                if "hi-dep.github.io" not in response.url:
                    return
                json_payloads.append((response.url, response.json()))
            except Exception:
                pass

        page.on("response", capture)
        page.goto(VENDOR_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(2000)
        text = page.locator("body").inner_text(timeout=TIMEOUT_MS)
        browser.close()

    return text, json_payloads


def dedupe_mods(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[Tuple[str, float, str], Dict[str, Any]] = {}
    for item in items:
        vendor = re.sub(r"\s+", " ", str(item.get("vendor", "Vendor"))).strip() or "Vendor"
        key = (item["name"], round(float(item["value"]), 3), vendor.lower())
        merged[key] = {**item, "vendor": vendor}

    result = list(merged.values())
    result.sort(key=lambda x: (-(x["value"] / x["max"]), x["name"], x["vendor"]))
    return result


def format_value(value: float, mod_name: str) -> str:
    if mod_name == "Armor on Kill":
        return f"{int(round(value)):,}"

    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value))}%"
    return f"{value:.1f}%"


def loot_icon(label: str, config: Dict[str, Any]) -> str:
    canonical = LOOT_NAME_ALIASES.get(label, label)
    custom = config.get("loot_emojis", {})
    if not isinstance(custom, dict):
        return ""
    return str(custom.get(canonical) or custom.get(label) or "")


def build_event_embed(event: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    blocks = []
    for row in event["missions"]:
        icon = loot_icon(row["loot"], config)
        prefix = f"{icon} " if icon else ""
        blocks.append(
            f"### {row['mission']} — {prefix}{bilingual_loot(row['loot'])}"
        )

    description = "\n\n".join([
        f"**Target Loot Date | تاريخ الغنائم:** {event['day']}",
        *blocks,
    ])

    return {
        "title": "Escalation Target Loot | غنائم التصعيد",
        "url": EVENT_URL,
        "description": description[:4096],
        "color": int(config.get("embed_color", 15105570)),
        "footer": {"text": "Source: hi-dep Division 2"},
        "timestamp": utc_now().isoformat(),
    }
def build_mods_embed(mods: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    if mods:
        lines = []
        for mod in mods[:25]:
            lines.append(
                f"**{bilingual_mod(mod['name'])} — {format_value(mod['value'], mod['name'])}**\n"
                f"{bilingual_vendor(mod['vendor'])}"
            )
        value = "\n\n".join(lines)
    else:
        value = "لا توجد مودات دروع مرتفعة حسب الحد المحدد | No high Gear Mods matched the configured threshold."

    return {
        "title": "مودات الدروع العالية | High Gear Mods",
        "url": VENDOR_URL,
        "description": value[:4096],
        "color": int(config.get("embed_color", 15105570)),
        "footer": {"text": "مودات الدروع فقط | Gear Mods only • Source: hi-dep Division 2"},
        "timestamp": utc_now().isoformat(),
    }


def send_webhook(embeds: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        raise RuntimeError("DISCORD_WEBHOOK_URL secret is not configured.")

    payload = {
        "username": str(config.get("discord_username", "Division 2 Loot")),
        "embeds": embeds,
    }
    r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
    if r.status_code >= 400:
        raise RuntimeError(f"Discord webhook failed: HTTP {r.status_code}: {r.text[:500]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Post event and vendor even if content is unchanged")
    parser.add_argument("--force-event", action="store_true", help="Post the Escalation event even if content is unchanged")
    parser.add_argument("--force-vendor", action="store_true", help="Post vendor mods even if content is unchanged")
    parser.add_argument("--event-only", action="store_true", help="Only process/post Escalation")
    parser.add_argument("--vendor-only", action="store_true", help="Only process/post Vendor")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    config = load_json(CONFIG_PATH, {"high_mod_ratio": 0.9, "mod_thresholds": {}})
    state = load_json(STATE_PATH, {"event_hash": "", "mods_hash": ""})
    ratio = float(config.get("high_mod_ratio", 0.9))
    thresholds = config.get("mod_thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}

    if args.event_only and args.vendor_only:
        raise RuntimeError("--event-only and --vendor-only cannot be used together.")

    vendor_enabled = bool(config.get("vendor_enabled", False))
    want_event = not args.vendor_only
    want_vendor = vendor_enabled and not args.event_only

    if args.vendor_only and not vendor_enabled:
        print("Vendor is disabled in config; nothing to post.")
        return 0

    event: Optional[Dict[str, Any]] = None
    mods: List[Dict[str, Any]] = []
    vendor_text = ""
    vendor_json: List[Tuple[str, Any]] = []

    event_hash = str(state.get("event_hash", ""))
    mods_hash = str(state.get("mods_hash", ""))
    changed_event = False
    changed_mods = False

    if want_event:
        event = select_event_snapshot(fetch_event())
        event_hash = stable_hash(event)
        changed_event = event_hash != state.get("event_hash")

    if want_vendor:
        vendor_text, vendor_json = fetch_vendor_rendered()

        # Use the rendered page as the source of current vendor inventory.
        # Exact "MOD" rows are armor/gear mods; skill attachments use labels such
        # as "Drone MOD" and are therefore excluded automatically.
        mods = collect_from_text(vendor_text, ratio, thresholds)
        mods = dedupe_mods(mods)
        mods_hash = stable_hash(mods)
        changed_mods = mods_hash != state.get("mods_hash")

        if args.debug:
            (ROOT / "debug_vendor.txt").write_text(vendor_text, encoding="utf-8")
            (ROOT / "debug_vendor_json.json").write_text(
                json.dumps([{"url": u, "data": d} for u, d in vendor_json], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Captured {len(vendor_json)} JSON responses; high mods: {len(mods)}")

    embeds: List[Dict[str, Any]] = []
    if want_event and event is not None and (args.force or args.force_event or changed_event):
        embeds.append(build_event_embed(event, config))
    if want_vendor and (args.force or args.force_vendor or changed_mods):
        embeds.append(build_mods_embed(mods, config))

    if not embeds:
        print("No changes; nothing to post.")
        return 0

    send_webhook(embeds, config)

    if want_event:
        state["event_hash"] = event_hash
    if want_vendor:
        state["mods_hash"] = mods_hash
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if want_vendor:
        print(f"Posted {len(embeds)} embed(s). High vendor mods found: {len(mods)}")
    else:
        print(f"Posted {len(embeds)} Escalation embed(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
