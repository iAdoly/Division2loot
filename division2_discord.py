from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state.json"

EVENT_URL = "https://hi-dep.github.io/division2/?view=event&lang=en"
EVENT_JSON_URL = "https://hi-dep.github.io/division2/data/event/index.json"
VENDOR_URL = "https://hi-dep.github.io/division2/?view=vendor&lang=en"

TIMEOUT_MS = 45_000
HTTP_TIMEOUT = 30

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

ALIASES = {
    "critical hit chance": "Critical Hit Chance",
    "critical hit damage": "Critical Hit Damage",
    "headshot damage": "Headshot Damage",
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_label(value: Any) -> str:
    raw = str(value or "").strip()
    return TOKEN_LABELS.get(raw.lower(), raw or "N/A")


def fetch_event() -> Dict[str, Any]:
    r = requests.get(EVENT_JSON_URL, timeout=HTTP_TIMEOUT, headers={"User-Agent": "Division2loot/1.0"})
    r.raise_for_status()
    return r.json()


def select_event_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    escalation = data.get("Escalation")
    if not isinstance(escalation, list):
        raise RuntimeError("Escalation data is missing.")

    today = utc_now().strftime("%Y-%m-%d")
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


def walk_json(value: Any, path: Tuple[str, ...] = ()) -> Iterable[Tuple[Tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for k, v in value.items():
            yield from walk_json(v, path + (str(k),))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk_json(v, path + (str(i),))


def canonical_mod_name(text: str) -> Optional[str]:
    lower = text.lower()
    for alias, canonical in ALIASES.items():
        if alias in lower:
            return canonical
    return None


def extract_percent(text: str, mod_name: str) -> Optional[float]:
    max_value = MOD_MAX[mod_name]
    values = [float(x) for x in PERCENT_RE.findall(text)]
    valid = [v for v in values if 0 < v <= max_value * 1.15]
    return max(valid) if valid else None


def vendor_hint_from_path(path: Tuple[str, ...]) -> str:
    words = [p for p in path if not p.isdigit()]
    if not words:
        return "Vendor"
    return " › ".join(words[-3:])


def collect_from_json(payloads: List[Tuple[str, Any]], ratio: float, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for source_url, payload in payloads:
        for path, node in walk_json(payload):
            if not isinstance(node, dict):
                continue
            blob = json.dumps(node, ensure_ascii=False)
            mod_name = canonical_mod_name(blob)
            if not mod_name:
                continue
            value = extract_percent(blob, mod_name)
            if value is None:
                continue
            minimum = float(thresholds.get(mod_name, MOD_MAX[mod_name] * ratio))
            if value + 1e-9 < minimum:
                continue

            vendor = "Vendor"
            for key in ("vendor", "vendor_name", "location", "source", "name"):
                val = node.get(key)
                if isinstance(val, str) and val.strip() and canonical_mod_name(val) is None:
                    vendor = val.strip()
                    break
            if vendor == "Vendor":
                vendor = vendor_hint_from_path(path)

            found.append({
                "name": mod_name,
                "value": value,
                "max": MOD_MAX[mod_name],
                "vendor": vendor,
                "source": source_url,
            })
    return found


def collect_from_text(text: str, ratio: float, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [x for x in lines if x]
    found: List[Dict[str, Any]] = []

    for i, line in enumerate(lines):
        mod_name = canonical_mod_name(line)
        if not mod_name:
            continue
        window = " | ".join(lines[max(0, i - 2): min(len(lines), i + 4)])
        value = extract_percent(window, mod_name)
        if value is None:
            continue
        minimum = float(thresholds.get(mod_name, MOD_MAX[mod_name] * ratio))
        if value + 1e-9 < minimum:
            continue

        # Usually the vendor/card heading is immediately above the item.
        vendor = "Vendor"
        for candidate in reversed(lines[max(0, i - 8):i]):
            if len(candidate) <= 80 and not PERCENT_RE.search(candidate) and canonical_mod_name(candidate) is None:
                vendor = candidate
                break

        found.append({
            "name": mod_name,
            "value": value,
            "max": MOD_MAX[mod_name],
            "vendor": vendor,
            "source": VENDOR_URL,
        })
    return found


def fetch_vendor_rendered() -> Tuple[str, List[Tuple[str, Any]]]:
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


def format_value(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value))}%"
    return f"{value:.1f}%"


def loot_icon(label: str, config: Dict[str, Any]) -> str:
    custom = config.get("loot_emojis", {})
    if isinstance(custom, dict) and label in custom:
        return str(custom[label])
    low = label.lower()
    if any(x in low for x in ("rifle", "smg", "shotgun", "pistol", "lmg")):
        return "🔫"
    if any(x in low for x in ("armor", "mask", "gloves", "holster", "kneepads", "backpack")):
        return "🛡️"
    return "🎯"


def build_event_embed(event: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    lines = []
    for row in event["missions"]:
        icon = loot_icon(row["loot"], config)
        lines.append(f"**{row['mission']}**\n{icon} {row['loot']}")

    vendor_lines = [
        f"📦 Prototype Gear Cache — **{event['prototype_gear_cache']}**",
        f"🔫 Prototype Weapon Cache — **{event['prototype_weapon_cache']}**",
    ]

    return {
        "title": "🟠 Escalation Target Loot",
        "url": EVENT_URL,
        "description": f"**Week:** {event['week']}\n**Target Loot Date:** {event['day']}",
        "color": int(config.get("embed_color", 15105570)),
        "fields": [
            {"name": "Escalations", "value": "\n\n".join(lines)[:1024] or "No data", "inline": False},
            {"name": "Escalation Requisition Vendor", "value": "\n".join(vendor_lines)[:1024], "inline": False},
        ],
        "footer": {"text": "Source: hi-dep Division 2"},
        "timestamp": utc_now().isoformat(),
    }


def build_mods_embed(mods: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    if mods:
        lines = []
        for mod in mods[:25]:
            pct = mod["value"] / mod["max"] * 100
            lines.append(
                f"🔥 **{mod['name']} — {format_value(mod['value'])}** "
                f"({pct:.0f}% of max)\n📍 {mod['vendor']}"
            )
        value = "\n\n".join(lines)
    else:
        value = "No vendor gear mods met the configured high-roll threshold."

    return {
        "title": "🔥 High Vendor Mods",
        "url": VENDOR_URL,
        "description": value[:4096],
        "color": int(config.get("embed_color", 15105570)),
        "footer": {"text": "Vendor mods only • Source: hi-dep Division 2"},
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
    parser.add_argument("--force", action="store_true", help="Post even if content is unchanged")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    config = load_json(CONFIG_PATH, {"high_mod_ratio": 0.9, "mod_thresholds": {}})
    state = load_json(STATE_PATH, {"event_hash": "", "mods_hash": ""})
    ratio = float(config.get("high_mod_ratio", 0.9))
    thresholds = config.get("mod_thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}

    event = select_event_snapshot(fetch_event())
    vendor_text, vendor_json = fetch_vendor_rendered()

    mods = collect_from_json(vendor_json, ratio, thresholds)
    mods.extend(collect_from_text(vendor_text, ratio, thresholds))
    mods = dedupe_mods(mods)

    if args.debug:
        (ROOT / "debug_vendor.txt").write_text(vendor_text, encoding="utf-8")
        (ROOT / "debug_vendor_json.json").write_text(
            json.dumps([{"url": u, "data": d} for u, d in vendor_json], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Captured {len(vendor_json)} JSON responses; high mods: {len(mods)}")

    event_hash = stable_hash(event)
    mods_hash = stable_hash(mods)
    changed_event = event_hash != state.get("event_hash")
    changed_mods = mods_hash != state.get("mods_hash")

    embeds: List[Dict[str, Any]] = []
    if args.force or changed_event:
        embeds.append(build_event_embed(event, config))
    if args.force or changed_mods:
        embeds.append(build_mods_embed(mods, config))

    if not embeds:
        print("No changes; nothing to post.")
        return 0

    send_webhook(embeds, config)

    state["event_hash"] = event_hash
    state["mods_hash"] = mods_hash
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Posted {len(embeds)} embed(s). High vendor mods found: {len(mods)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
