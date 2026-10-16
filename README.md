# Division2loot

Simple Discord updater for **The Division 2 Escalation Target Loot**.

It reads mission Target Loot from the public **ProtoTrack TXT endpoint** and posts a clean bilingual Arabic/English message to Discord. Vendor Caches are not posted.

## Features

- Daily Escalation Target Loot
- Arabic + English loot names
- Discord custom emojis for supported Brand Sets / Gear Sets
- Small Discord text for mission rows
- Saudi Arabia date handling (`Asia/Riyadh`)
- Automatic trigger through **cron-job.org**
- Manual runs through GitHub Actions
- Content signatures to skip already-posted Target Loot versions
- Clear Discord status messages when today's source is unavailable or not updated

## Automation

The production schedule is handled by **cron-job.org**:

- **Every day:** 11:01 AM
- **Timezone:** `Asia/Riyadh`
- Trigger: GitHub `repository_dispatch`
- Event type: `cron_job_org`

GitHub's native scheduled workflow is intentionally not used.

## Discord secret

The repository needs one GitHub Actions secret:

`DISCORD_WEBHOOK_URL`

Keep the webhook URL only in GitHub Actions Secrets. Do not put it in the repository files.

## Manual run

Open:

**Actions → Division 2 Discord Updater → Run workflow**

Select branch **main**. Leave **force_resend** unchecked for a normal run.

Checking **force_resend** explicitly resends the currently published ProtoTrack source, even if it has already been posted or is dated before today. Use this only for intentional manual recovery, such as resending a missed post from yesterday. Invalid, unavailable, or future-dated data is still rejected.

The override requires both a `workflow_dispatch` event and `force_resend=true`. Automatic `repository_dispatch` runs cannot use it.

## Source and duplicate protection

The source date is compared with the current Saudi date in `Asia/Riyadh`.

| Source result | Normal behavior |
| --- | --- |
| Today's date, new mission-loot signature | Post the loot, then save its version |
| Today's date, same recorded signature | Send "No new Target Loot update" without repeating the loot |
| Older date | Report that ProtoTrack has not updated today's loot yet |
| Timeout, HTTP error, empty response, or parsing failure | Report that today's Target Loot could not be loaded |
| Future date | Report invalid source data |

There is no fallback to previous-day loot. The parser requires exactly five missions.

The last successfully posted date and signature are stored in `.state/target_loot.json`. GitHub Actions persists `.state` using its cache. Each workflow attempt uses a unique cache key, and runs are serialized so overlapping triggers do not read the same old state and both post. Cache eviction or a cache-save failure can remove duplicate protection; the fresh source must still pass date validation.

## Custom emojis

Custom Discord emoji mappings are stored in `config.json`.

Example:

```json
{
  "loot_emojis": {
    "China Light Industries": "<:china_light:123456789012345678>"
  }
}
```

If an item has no configured emoji, the bilingual loot name is still posted normally.

See [the complete emoji coverage audit](docs/emoji-coverage.md) for all supported names, missing mappings, and source-name aliases. Missing mappings require the actual Discord emoji codes; screenshots alone do not provide those IDs.

## Files

- `division2_discord.py` — bot logic
- `config.json` — Discord username and custom emoji mappings
- `requirements.txt` — Python dependency
- `.github/workflows/update.yml` — GitHub Actions trigger
- `test_division2_discord.py` — isolated policy and parser regression tests

## Tests

```sh
python -m pip install -r requirements.txt
python -B -m unittest -v
```

Tests mock source requests and Discord delivery and use temporary state files. They do not send Discord messages.

## Data source

- Canonical source: https://prototrack.gg/target-loot/target-loot-current.txt

The application reads only this TXT endpoint. It does not scrape the ProtoTrack HTML page.
