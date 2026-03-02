import unittest

from clients.slack import MAX_SECTION_TEXT_CHARS, build_weekly_blocks


class SlackBlocksTest(unittest.TestCase):
    def test_truncates_section_text_to_slack_safe_limit(self) -> None:
        long_text = "x" * 12000
        blocks = build_weekly_blocks(
            headline=long_text,
            kpi_status=long_text,
            top_movers=[long_text] * 5,
            explanations=[long_text] * 5,
            actions=[long_text] * 5,
            supplemental_diagnostics=[long_text] * 10,
        )

        section_texts = [block["text"]["text"] for block in blocks if block.get("type") == "section"]
        self.assertTrue(section_texts)
        for text in section_texts:
            self.assertLessEqual(len(text), MAX_SECTION_TEXT_CHARS)

    def test_builds_concise_structure_and_link_formatting(self) -> None:
        blocks = build_weekly_blocks(
            headline="Weekly headline",
            kpi_status="North Star target 40-50%: 43.00% (43/100) vs 39.00% (39/100) (+4.00 pp).",
            top_movers=[
                "Activation KPI: Signup Completed -> Any High-Value Action: 43.00% (43/100) vs 39.00% (39/100) (+10.26%). <https://app.amplitude.com/analytics/tenant/chart/abc123|Any High-Value Action>",
                "Signup Completed -> Any DENT Created: 21.00% (21/100) vs 14.00% (14/100) (+50.00%). <https://app.amplitude.com/analytics/tenant/chart/def456|Any DENT Created>",
                "Repeat Behavior After Activation Proxy: 11 vs 8 (+37.50% WoW). <https://app.amplitude.com/analytics/tenant/chart/ghi789|Repeat Behavior>",
            ],
            explanations=["*Claim:* Explanation mentions v2.3.2 release\n*Evidence:* Supporting chart trend"],
            actions=["Action | Owner: PM | Expected impact: improve activation."],
            supplemental_diagnostics=["Supp 1", "Supp 2"],
            ios_release_context={"recent_releases": [{"version": "2.3.2", "release_date": "2026-02-04"}]},
            all_charts=[
                "*<https://app.amplitude.com/analytics/tenant/chart/abc123|Activation KPI: Signup Completed -> Any High-Value Action>*\n"
                "  _Change:_ +17.40% | _Latest:_ 23.48% | _Previous:_ 20.00% | _Type:_ funnel",
                "*<https://app.amplitude.com/analytics/tenant/chart/def456|Repeat Behavior After Activation Proxy>*\n"
                "  _Change:_ +147.06% | _Latest:_ 42.00 | _Previous:_ 17.00 | _Type:_ retention",
            ],
        )

        headers = [block["text"]["text"] for block in blocks if block.get("type") == "header"]
        contexts = [
            element["text"]
            for block in blocks
            if block.get("type") == "context"
            for element in block.get("elements", [])
            if element.get("type") == "mrkdwn"
        ]
        section_texts = [block["text"]["text"] for block in blocks if block.get("type") == "section"]
        joined_sections = "\n".join(section_texts)

        self.assertGreaterEqual(len(headers), 5)
        self.assertTrue(headers[0].startswith("User Insights Digest -"))
        self.assertIn("Executive Summary", headers)
        self.assertIn("Top Movers", headers)
        self.assertIn("Insights & Actions", headers)
        self.assertIn("All Charts", headers)
        self.assertIn(
            "_Cohort: Users excluding tenant team | Trailing 4 weeks vs previous 4 weeks | Report release: Mondays_",
            contexts[0],
        )
        self.assertNotIn("*Chart Set:*", joined_sections)
        self.assertNotIn("North Star Snapshot", joined_sections)
        self.assertNotIn("North Star Metric", joined_sections)
        self.assertNotIn("Supplemental Diagnostics Appendix", joined_sections)

        top_mover_sections = [
            text
            for text in section_texts
            if text.startswith("*Activation KPI:") and "\n*Change:* " in text
        ]
        self.assertEqual(len(top_mover_sections), 1)
        top_mover = top_mover_sections[0]
        self.assertIn("*Change:* :large_green_circle: +10.26%", top_mover)
        self.assertIn("*Latest:* 43.00% (43/100)", top_mover)
        self.assertIn("*Previous:* 39.00% (39/100)", top_mover)
        self.assertTrue(top_mover.rstrip().endswith("<https://app.amplitude.com/analytics/tenant/chart/abc123|chart>"))
        self.assertRegex(
            joined_sections,
            r"\*[A-Za-z0-9][A-Za-z0-9 ]+\*\n• _Insight:_ .+\n• _Action:_ Action",
        )
        self.assertIn("v2.3.2 (released Feb 4, 2026)", joined_sections)
        self.assertNotIn("Owner:", joined_sections)
        self.assertIn("_Type:_ funnel | <https://app.amplitude.com/analytics/tenant/chart/abc123|chart>", joined_sections)
        self.assertIn(
            "_Type:_ retention | <https://app.amplitude.com/analytics/tenant/chart/def456|chart>",
            joined_sections,
        )


if __name__ == "__main__":
    unittest.main()
