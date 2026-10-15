import unittest

from time_calculator import calculate_daily_overtime_and_early, is_valid_hhmm


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

    def test_weekday_keeps_existing_checkout_rule(self):
        result = calculate_daily_overtime_and_early(
            "09:00", "12:00", "13:00", "17:00"
        )

        self.assertEqual(result, ("", "0.5小時"))


if __name__ == "__main__":
    unittest.main()