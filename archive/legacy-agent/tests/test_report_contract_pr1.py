import unittest

from config import REPORT_APP_ID, get_chart_metrics_by_group


class ReportContractPR1Test(unittest.TestCase):
    def test_activation_v1_contract_has_required_group_sizes(self) -> None:
        grouped = get_chart_metrics_by_group("activation_v1")

        self.assertEqual(len(grouped["core"]), 5)
        self.assertEqual(len(grouped["supplemental"]), 3)

    def test_activation_v1_contains_required_metric_keys(self) -> None:
        grouped = get_chart_metrics_by_group("activation_v1")
        metric_keys = [metric.metric_key for metric in grouped["core"] + grouped["supplemental"]]

        expected_keys = [
            "core_composite_activation_14d",
            "core_signup_to_any_dent_created",
            "core_signup_to_calendar_connect_completed",
            "core_signup_to_appliance_added",
            "core_signup_to_hive_member_invited",
            "supp_dent_action_mix_breakdown",
            "supp_calendar_started_to_completed",
            "supp_14d_repeat_after_activation_proxy",
        ]
        self.assertEqual(metric_keys, expected_keys)

    def test_all_contract_metrics_are_locked_to_prod_app_id(self) -> None:
        for chart_set in ("legacy", "activation_v1"):
            grouped = get_chart_metrics_by_group(chart_set)
            for metric in grouped["core"] + grouped["supplemental"]:
                self.assertEqual(metric.app_id, REPORT_APP_ID)


if __name__ == "__main__":
    unittest.main()
