# Division2loot

Discord updater for **The Division 2** using the public data/pages at [hi-dep.github.io/division2](https://hi-dep.github.io/division2/).

## What it posts

- **Escalation** target loot from the Event data.
- **High Vendor Mods only** from the Vendor page.
- Vendor mods are considered high when they meet the configured roll threshold (default: **90% of max roll**).
- It stores a small state file so manual/non-forced runs do not repost unchanged data.
- Arabic + English loot names and configured Discord custom emojis are supported for Brand Sets / Gear Sets.

## Discord setup

1. In Discord open **Server Settings → Integrations → Webhooks**.
2. Create a webhook for the channel you want.
3. In this GitHub repository open **Settings → Secrets and variables → Actions**.
4. Create a repository secret named exactly:
   `DISCORD_WEBHOOK_URL`
5. Paste the webhook URL as the secret value.

> Never put the webhook URL directly in this repository.

## Run it

Open **Actions → Division 2 Discord Updater → Run workflow**.

For a test, enable **Force post** so it sends even if the current data was already posted.

Automatic schedule (Saudi Arabia time):

- **Escalation:** every day at **11:01 AM**.
- **Vendor:** every **Tuesday at 11:01 AM**.
- Tuesday uses the same workflow run, so Escalation and Vendor do not race each other when updating `state.json`.

Scheduled posts are forced for their intended cadence. Manual runs can still use **Force post** when needed.

## High-mod threshold

Edit `config.json`:

```json
{
  "high_mod_ratio": 0.9
}
```

Examples at 90%:

- Critical Hit Chance: 5.4% / 6%
- Critical Hit Damage: 10.8% / 12%
- Protection from Elites: 11.7% / 13%
- Skill Haste: 10.8% / 12%

## Brand / loot icons

Discord cannot place arbitrary tiny PNGs inline beside every line of an embed. The bot therefore supports **custom Discord emoji mappings** in `config.json`.

After you upload your preferred brand/gear icons as server emojis, add their Discord emoji strings under `loot_emojis`, for example:

```json
{
  "loot_emojis": {
    "Grupo Sombra S.A.": "<:grupo:123456789012345678>",
    "Electrique": "<:electrique:123456789012345678>"
  }
}
```

If a loot item has no configured custom emoji, the bot simply shows the bilingual text without an icon.

## Sources

- Event: https://hi-dep.github.io/division2/?view=event&lang=en
- Event JSON: https://hi-dep.github.io/division2/data/event/index.json
- Vendor: https://hi-dep.github.io/division2/?view=vendor&lang=en

The Vendor scraper opens the rendered page in Chromium and reads the visible Vendor rows. JSON responses are captured only for debugging. This avoids relying on a guessed private/internal vendor-data URL.
