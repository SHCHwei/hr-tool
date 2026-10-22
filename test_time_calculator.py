import unittest

from time_calculator import (
    calculate_daily_overtime_and_early,
    calculate_late,
    calculate_overtime_and_early,
    is_valid_hhmm,
)


class DailyOvertimeCalculationTests(unittest.TestCase):
    def test_hhmm_validation_requires_four_valid_ascii_digits(self):
        for value in ("0000", "0830", "2359"):
            with self.subTest(value=value):
                self.assertTrue(is_valid_hhmm(value))

        for value in ("", "930", "12345", "2400", "1260", "08:30", "０８３０"):
            with self.subTest(value=value):
                self.assertFalse(is_valid_hhmm(value))

    def test_weekend_work_intervals_are_all_overtime(self):
        result = calculate_daily_overtime_and_early(
            "09:00", "12:00", "13:00", "17:00", is_weekend=True
        )

        self.assertEqual(result, ("7.0小時", ""))

    def test_weekend_overnight_interval_counts_elapsed_time(self):
        result = calculate_daily_overtime_and_early(
            "22:00", "02:00", "", "", is_weekend=True
        )

        self.assertEqual(result, ("4.0小時", ""))

    def test_weekday_uses_employee_work_off(self):
        self.assertEqual(
            calculate_daily_overtime_and_early("0800", "1200", "1300", "1630", work_off="1700"),
            ("", "0.5小時"),
        )
        self.assertEqual(
            calculate_daily_overtime_and_early("0800", "1200", "1300", "1800", work_off="1700"),
            ("0.75小時", ""),
        )
        self.assertEqual(
            calculate_daily_overtime_and_early("0800", "1200", "1300", "1710", work_off="1700"),
            ("", ""),
        )

    def test_weekday_counts_early_arrival_as_overtime(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0800", "1200", "1300", "1730", work_start="0830"
            ),
            ("0.5小時", ""),
        )
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0800", "1200", "1300", "1800", work_start="0830"
            ),
            ("0.75小時", ""),
        )

    def test_weekday_split_shift_overtime_counts_only_work_after_threshold(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0811", "1800", "1915", "2208",
                work_start="0830",
                work_off="1730",
            ),
            ("3.45小時", ""),
        )

    def test_weekday_second_shift_overtime_starts_at_later_of_threshold_or_clock_in(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0830", "1200", "1730", "1815", work_start="0830"
            ),
            ("0.5小時", ""),
        )

    def test_weekday_first_checkout_overtime_counts_without_second_checkout(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0830", "1800", "1915", "", work_start="0830"
            ),
            ("0.25小時", ""),
        )

    def test_weekday_second_shift_overtime_handles_overnight_checkout(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0830", "1200", "2300", "0100", work_start="0830"
            ),
            ("2.0小時", ""),
        )

    def test_early_arrival_overtime_does_not_require_checkout(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0800", "", "", "", work_start="0830"
            ),
            ("0.5小時", ""),
        )
        self.assertEqual(
            calculate_overtime_and_early(
                "", first_in="0800", work_start="0830"
            ),
            ("0.5小時", ""),
        )

    def test_early_arrival_overtime_adds_to_overnight_checkout_overtime(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0829", "0130", "", "", work_start="0830"
            ),
            ("7.77小時", ""),
        )

    def test_early_arrival_overtime_only_applies_on_weekdays(self):
        self.assertEqual(
            calculate_daily_overtime_and_early(
                "0800", "1200", "", "", is_weekend=True, work_start="0830"
            ),
            ("4.0小時", ""),
        )

    def test_late_when_first_in_after_work_start(self):
        self.assertEqual(calculate_late("0815", "0800"), "0.25小時")
        self.assertEqual(calculate_late("0800", "0800"), "")
        self.assertEqual(calculate_late("0750", "0800"), "")
        self.assertEqual(calculate_late("", "0800"), "")
        self.assertEqual(calculate_late("0900", ""), "")

    def test_weekday_keeps_existing_checkout_rule(self):
        result = calculate_daily_overtime_and_early(
            "09:00", "12:00", "13:00", "17:00"
        )

        self.assertEqual(result, ("", "0.5小時"))


if __name__ == "__main__":
    unittest.main()