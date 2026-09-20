# Division2loot

Simple Discord updater for **The Division 2 Escalation Target Loot**.

It reads the current Escalation data from the public **hi-dep Division 2** dataset and posts a clean bilingual Arabic/English message to Discord.

## Features

- Daily Escalation Target Loot
- Arabic + English loot names
- Discord custom emojis for supported Brand Sets / Gear Sets
- Small Discord text for mission rows
- Saudi Arabia date handling (`Asia/Riyadh`)
- Automatic trigger through **cron-job.org**
- Manual runs through GitHub Actions

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

The workflow fetches the current Escalation Target Loot and posts it directly to Discord.

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

## Files

- `division2_discord.py` — bot logic
- `config.json` — Discord username and custom emoji mappings
- `requirements.txt` — Python dependency
- `.github/workflows/update.yml` — GitHub Actions trigger

## Data source

- Event page: https://hi-dep.github.io/division2/?view=event&lang=en
- Event JSON: https://hi-dep.github.io/division2/data/event/index.json
