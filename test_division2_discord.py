import io
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import division2_discord as bot


TODAY = "2026-10-16"
YESTERDAY = "2026-10-15"


def source_text(day=TODAY):
    return f"""Daily Escalation Target Loot
Date: {day}

Missions:
- Grand Washington Hotel: Assault Rifles
- Jefferson Trade Center: China Light Industries Corporation
- American History Museum: Striker's Battlegear
- Air & Space Museum: Ortiz: Exuro
- ViewPoint Museum: Česká Výroba s.r.o.

Vendor Caches:
- Example vendor: Masks

Last updated: {day} 11:00:00
Source: https://prototrack.gg/target-loot/target-loot.php
"""


class TargetLootPolicyTests(unittest.TestCase):
    def setUp(self):
        stack = self.enterContext(ExitStack())
        directory = stack.enter_context(tempfile.TemporaryDirectory())
        self.state_path = Path(directory) / ".state" / "target_loot.json"
        stack.enter_context(patch.object(bot, "STATE_PATH", self.state_path))
        stack.enter_context(patch.dict(os.environ, {
            "GITHUB_EVENT_NAME": "repository_dispatch",
            "FORCE_RESEND": "false",
        }, clear=True))
        self.day = stack.enter_context(
            patch.object(bot, "target_loot_day", return_value=TODAY)
        )
        self.response = Mock(text=source_text(), status_code=200)
        self.get = stack.enter_context(
            patch.object(bot.requests, "get", return_value=self.response)
        )
        self.send = stack.enter_context(patch.object(bot, "send_webhook"))
        stack.enter_context(patch.object(
            bot.requests, "post", side_effect=AssertionError("Real posts forbidden")
        ))
        stack.enter_context(redirect_stdout(io.StringIO()))
        stack.enter_context(redirect_stderr(io.StringIO()))

    def status_contains(self, text):
        self.send.assert_called_once()
        content = self.send.call_args.args[0]
        self.assertIn(text, content)
        self.assertNotIn("**Escalation Target Loot |", content)

    def record_source(self, text):
        event = bot.select_event_snapshot(text)
        bot.save_state(event, bot.event_signature(event))

    def test_new_current_version_posts_bilingual_missions_and_records_state(self):
        self.assertEqual(bot.main(), 0)
        self.send.assert_called_once()
        content = self.send.call_args.args[0]
        self.assertIn("بندقية هجومية | Assault Rifle", content)
        self.assertIn("<:china_light:1550661406918189096>", content)
        self.assertIn("Ortiz: Exuro", content)
        self.assertNotIn("Example vendor", content)
        event = bot.select_event_snapshot(source_text())
        self.assertEqual(bot.load_state()["signature"], bot.event_signature(event))
        self.assertEqual(bot.load_state()["source_day"], TODAY)
        self.assertEqual(self.get.call_args.args[0], bot.TARGET_LOOT_URL)

    def test_same_current_version_reports_no_update(self):
        self.record_source(source_text())
        before = self.state_path.read_bytes()
        self.assertEqual(bot.main(), 0)
        self.status_contains("No new Target Loot update")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_changed_mission_loot_is_a_new_version(self):
        self.record_source(source_text())
        self.response.text = source_text().replace("Assault Rifles", "Masks")
        self.assertEqual(bot.main(), 0)
        self.assertIn("قناع | Mask", self.send.call_args.args[0])
        event = bot.select_event_snapshot(self.response.text)
        self.assertEqual(bot.load_state()["signature"], bot.event_signature(event))

    def test_last_updated_only_does_not_repeat_mission_loot(self):
        self.record_source(source_text())
        self.response.text = source_text().replace("11:00:00", "11:05:00")
        self.assertEqual(bot.main(), 0)
        self.status_contains("No new Target Loot update")

    def test_old_state_does_not_block_todays_identical_mission_loot(self):
        self.record_source(source_text(YESTERDAY))
        self.assertEqual(bot.main(), 0)
        self.assertIn("**Escalation Target Loot |", self.send.call_args.args[0])
        self.assertEqual(bot.load_state()["source_day"], TODAY)

    def test_stale_source_never_posts_loot_even_with_cached_current_data(self):
        self.record_source(source_text())
        before = self.state_path.read_bytes()
        self.response.text = source_text(YESTERDAY)
        self.assertEqual(bot.main(), 0)
        self.status_contains("Target Loot not updated yet")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_source_failure_never_uses_cached_previous_day_loot(self):
        self.record_source(source_text(YESTERDAY))
        before = self.state_path.read_bytes()
        for error in (requests.Timeout("source timeout"),
                      requests.HTTPError("503 Server Error")):
            with self.subTest(error=type(error).__name__):
                self.send.reset_mock()
                self.get.side_effect = error
                self.assertEqual(bot.main(), 1)
                self.status_contains("Target Loot update failed")
                self.assertIn(str(error), self.send.call_args.args[0])
                self.assertEqual(self.state_path.read_bytes(), before)

    def test_empty_or_changed_format_reports_failure_without_state(self):
        for text in ("", "Unexpected source format", source_text().replace(
            "- ViewPoint Museum: Česká Výroba s.r.o.\n", ""
        )):
            with self.subTest(text=text[:30]):
                self.send.reset_mock()
                self.response.text = text
                self.assertEqual(bot.main(), 1)
                self.status_contains("Target Loot update failed")
                self.assertFalse(self.state_path.exists())

    def test_manual_run_without_force_still_rejects_stale_source(self):
        os.environ["GITHUB_EVENT_NAME"] = "workflow_dispatch"
        self.response.text = source_text(YESTERDAY)
        self.assertEqual(bot.main(), 0)
        self.status_contains("Target Loot not updated yet")

    def test_explicit_manual_force_can_resend_stale_source(self):
        os.environ.update(GITHUB_EVENT_NAME="workflow_dispatch", FORCE_RESEND="true")
        self.response.text = source_text(YESTERDAY)
        self.record_source(self.response.text)
        self.assertEqual(bot.main(), 0)
        self.assertIn("**Escalation Target Loot |", self.send.call_args.args[0])
        self.assertIn(YESTERDAY, self.send.call_args.args[0])

    def test_explicit_manual_force_can_resend_duplicate_current_version(self):
        os.environ.update(GITHUB_EVENT_NAME="workflow_dispatch", FORCE_RESEND="true")
        self.record_source(source_text())
        self.assertEqual(bot.main(), 0)
        self.assertIn("**Escalation Target Loot |", self.send.call_args.args[0])

    def test_force_flag_on_nonmanual_event_cannot_bypass_stale_guard(self):
        self.response.text = source_text(YESTERDAY)
        for event_name in ("repository_dispatch", "schedule", "push", ""):
            with self.subTest(event_name=event_name):
                self.send.reset_mock()
                os.environ.update(GITHUB_EVENT_NAME=event_name, FORCE_RESEND="true")
                self.assertEqual(bot.main(), 0)
                self.status_contains("Target Loot not updated yet")

    def test_force_flag_on_nonmanual_event_cannot_bypass_duplicate_guard(self):
        self.record_source(source_text())
        os.environ["FORCE_RESEND"] = "true"
        self.assertEqual(bot.main(), 0)
        self.status_contains("No new Target Loot update")

    def test_force_does_not_override_source_failure_or_future_date(self):
        os.environ.update(GITHUB_EVENT_NAME="workflow_dispatch", FORCE_RESEND="true")
        for text, status in (("invalid", "Target Loot update failed"),
                             (source_text("2026-10-17"), "Target Loot data is invalid")):
            with self.subTest(status=status):
                self.send.reset_mock()
                self.response.text = text
                self.assertEqual(bot.main(), 1)
                self.status_contains(status)
                self.assertFalse(self.state_path.exists())

    def test_failed_discord_post_does_not_record_version(self):
        self.send.side_effect = RuntimeError("Discord webhook failed")
        with self.assertRaisesRegex(RuntimeError, "Discord webhook failed"):
            bot.main()
        self.assertFalse(self.state_path.exists())

    def test_corrupt_state_does_not_supply_cached_loot(self):
        self.state_path.parent.mkdir()
        self.state_path.write_text("{broken json", encoding="utf-8")
        self.response.text = source_text(YESTERDAY)
        self.assertEqual(bot.main(), 0)
        self.status_contains("Target Loot not updated yet")
        self.assertEqual(self.state_path.read_text(), "{broken json")


class ParserTests(unittest.TestCase):
    def test_parser_preserves_aliases_and_ignores_vendor_caches(self):
        event = bot.select_event_snapshot(source_text().replace("\n", "\r\n"))
        self.assertEqual(event["source_day"], TODAY)
        self.assertEqual(len(event["missions"]), 5)
        self.assertEqual(event["missions"][1]["loot"], "China Light Industries")
        self.assertEqual(event["missions"][3]["loot"], "Ortiz: Exuro")
        self.assertEqual(event["missions"][4]["loot"], "Ceska Vyroba s.r.o.")
        self.assertIn("11:00:00", event["source_last_updated"])

    def test_last_updated_is_optional(self):
        text = source_text().replace(f"Last updated: {TODAY} 11:00:00\n", "")
        self.assertIsNone(bot.select_event_snapshot(text)["source_last_updated"])

    def test_signature_uses_normalized_loot_not_timestamp(self):
        first = bot.select_event_snapshot(source_text())
        second = bot.select_event_snapshot(source_text().replace(
            "Assault Rifles", "Assault Rifle"
        ).replace("11:00:00", "11:30:00"))
        self.assertEqual(bot.event_signature(first), bot.event_signature(second))


if __name__ == "__main__":
    unittest.main()
