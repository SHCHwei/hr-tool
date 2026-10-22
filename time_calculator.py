"""
考勤時間計算模組 (Attendance Time Calculator)

平日加班包含首次上班早於 workStart 的時間，以及各出勤段超過 workOff + 15 分鐘的時間。
週末則將完整的打卡區間工時全數計為加班。
"""

from typing import Optional, Tuple

DEFAULT_WORK_OFF = "1730"
OVERTIME_BUFFER_MINUTES = 15


def parse_time(time_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """
    解析打卡時間字串為 (hour, minute)。
    支援 "HH:MM", "HH:MM:SS", "HH.MM", "HHMM", "H:MM", "HMM" 等常見格式。
    若字串為空或格式無法解析，回傳 None。
    """
    if not time_str:
        return None
    s = str(time_str).strip()
    if not s:
        return None

    try:
        if ":" in s:
            parts = s.split(":")
            h, m = int(parts[0]), int(parts[1])
        elif "." in s:
            parts = s.split(".")
            h, m = int(parts[0]), int(parts[1])
        elif s.isdigit():
            if len(s) == 3:
                h, m = int(s[0]), int(s[1:])
            elif len(s) == 4:
                h, m = int(s[:2]), int(s[2:])
            elif len(s) in (1, 2):
                h, m = int(s), 0
            else:
                return None
        else:
            return None

        if 0 <= h < 24 and 0 <= m < 60:
            return (h, m)
    except (ValueError, IndexError):
        return None

    return None


def is_valid_hhmm(time_str: str) -> bool:
    """確認輸入是有效的四位數 24 小時制 HHMM 時間。"""
    return (
        len(time_str) == 4
        and time_str.isascii()
        and time_str.isdigit()
        and parse_time(time_str) is not None
    )


def format_duration(total_minutes: int) -> str:
    """
    將時長（分鐘）格式化為中文時數顯示，忠實對齊 GoLang main.go 的 timeFormat 行為：
    - 大於等於 60 分鐘：輸出 "X小時" (例如 60分 -> "1小時", 75分 -> "1.25小時")
    - 小於 60 分鐘且大於 0 分鐘：輸出 "Y分" (例如 15分 -> "0.25小時")
    - 小於等於 0 分鐘：輸出 ""
    """

    if total_minutes <= 0:
        return ""
    elif total_minutes < 60:
        return f"{round(total_minutes / 60, 2)}小時"
    else:
        return f"{round(total_minutes / 60, 2)}小時"


def calculate_overtime_and_early(
    checkout_str: Optional[str],
    work_off: Optional[str] = DEFAULT_WORK_OFF,
    first_in: Optional[str] = None,
    work_start: Optional[str] = None,
) -> Tuple[str, str]:
    """
    計算下班造成的加班/早退，以及可選的提早上班加班時數。

    規則（work_off 預設 17:30，可由員工個人下班時間取代）：
    - 下班時間基準點：
      - workOff (早退基準): work_off
      - workOver (加班起算): work_off + 15 分鐘
    - 跨夜下班判定：
      - 小時 < 6 (00:00 ~ 05:59) 視為跨夜至隔日凌晨，加 24 小時計算。
    - 早退計算：
      - 下班時間 < 17:30 => 早退時長 = 17:30 - 下班時間
    - 加班計算：
      - 下班時間 > 17:45 => 加班時長 = 下班時間 - 17:45
    - 正常緩衝區間：
      - 17:30 <= 下班時間 <= 17:45 => 無加班亦無早退
    - 若提供 first_in 與 work_start，首次上班早於 work_start 的差額加進加班時數。

    回傳：
        (overtime_str, early_str): (加班時數, 早退時數)
    """
    overtime_minutes, early_minutes = _calculate_overtime_and_early_minutes(
        checkout_str, work_off
    )
    actual_start = parse_time(first_in)
    expected_start = parse_time(work_start)
    if actual_start and expected_start:
        actual_start_minutes = actual_start[0] * 60 + actual_start[1]
        expected_start_minutes = expected_start[0] * 60 + expected_start[1]
        overtime_minutes += max(0, expected_start_minutes - actual_start_minutes)

    return (format_duration(overtime_minutes), format_duration(early_minutes))


def _calculate_overtime_and_early_minutes(
    checkout_str: Optional[str], work_off: Optional[str]
) -> Tuple[int, int]:
    parsed = parse_time(checkout_str)
    if not parsed:
        return (0, 0)

    h, m = parsed
    # 跨日判斷：小時 < 6 視為次日凌晨 (00:00 ~ 05:59)
    if h < 6:
        h += 24

    total_minutes = h * 60 + m
    work_off_parsed = parse_time(work_off) or parse_time(DEFAULT_WORK_OFF)
    work_off_minutes = work_off_parsed[0] * 60 + work_off_parsed[1]
    work_over_minutes = work_off_minutes + OVERTIME_BUFFER_MINUTES

    if total_minutes < work_off_minutes:
        return (0, work_off_minutes - total_minutes)
    if total_minutes > work_over_minutes:
        return (total_minutes - work_over_minutes, 0)
    return (0, 0)


def calculate_daily_overtime_and_early(
    t1_in: Optional[str],
    t1_out: Optional[str],
    t2_in: Optional[str],
    t2_out: Optional[str],
    is_weekend: bool = False,
    work_off: Optional[str] = DEFAULT_WORK_OFF,
    work_start: Optional[str] = None,
) -> Tuple[str, str]:
    """依平日/週末規則計算每日加班與早退；平日雙段出勤分段計算加班。"""
    if is_weekend:
        worked_minutes = 0
        for time_in, time_out in ((t1_in, t1_out), (t2_in, t2_out)):
            parsed_in = parse_time(time_in)
            parsed_out = parse_time(time_out)
            if not parsed_in or not parsed_out:
                continue

            start_minutes = parsed_in[0] * 60 + parsed_in[1]
            end_minutes = parsed_out[0] * 60 + parsed_out[1]
            if end_minutes < start_minutes:
                end_minutes += 24 * 60
            worked_minutes += end_minutes - start_minutes

        return (format_duration(worked_minutes), "")

    if t2_in and t2_in.strip():
        work_off_parsed = parse_time(work_off) or parse_time(DEFAULT_WORK_OFF)
        work_over_minutes = (
            work_off_parsed[0] * 60
            + work_off_parsed[1]
            + OVERTIME_BUFFER_MINUTES
        )

        first_checkout_overtime, _ = _calculate_overtime_and_early_minutes(
            t1_out, work_off
        )
        overtime_minutes = first_checkout_overtime

        parsed_t2_in = parse_time(t2_in)
        parsed_t2_out = parse_time(t2_out)
        if parsed_t2_in and parsed_t2_out:
            start_minutes = parsed_t2_in[0] * 60 + parsed_t2_in[1]
            end_minutes = parsed_t2_out[0] * 60 + parsed_t2_out[1]
            if parsed_t2_in[0] < 6:
                start_minutes += 24 * 60
            if parsed_t2_out[0] < 6:
                end_minutes += 24 * 60
            if end_minutes < start_minutes:
                end_minutes += 24 * 60
            overtime_minutes += max(
                0, end_minutes - max(start_minutes, work_over_minutes)
            )

        _, early_minutes = _calculate_overtime_and_early_minutes(t2_out, work_off)
        actual_start = parse_time(t1_in)
        expected_start = parse_time(work_start)
        if actual_start and expected_start:
            actual_start_minutes = actual_start[0] * 60 + actual_start[1]
            expected_start_minutes = expected_start[0] * 60 + expected_start[1]
            overtime_minutes += max(
                0, expected_start_minutes - actual_start_minutes
            )
        return (format_duration(overtime_minutes), format_duration(early_minutes))

    checkout_time = get_effective_checkout(t1_in, t1_out, t2_in, t2_out)
    return calculate_overtime_and_early(
        checkout_time, work_off, first_in=t1_in, work_start=work_start
    )


def calculate_late(first_in: Optional[str], work_start: Optional[str]) -> str:
    """首次上班打卡晚於員工上班時間時，回傳遲到時數；否則回傳空字串。"""
    actual = parse_time(first_in)
    expected = parse_time(work_start)
    if not actual or not expected:
        return ""
    return format_duration((actual[0] * 60 + actual[1]) - (expected[0] * 60 + expected[1]))


def get_effective_checkout(
    t1_in: Optional[str] = None,
    t1_out: Optional[str] = None,
    t2_in: Optional[str] = None,
    t2_out: Optional[str] = None,
) -> Optional[str]:
    """
    依據每日四格打卡輸入 (首次上班, 首次下班, 二次上班, 二次下班) 取得當日有效下班時間：
    1. 若有填寫二次上班 (t2_in)：
       - 表示當天有下午出勤，下班打卡應以二次下班 (t2_out) 為準。
       - 若 t2_out 未填，代表下午出勤但忘記打卡下班，視為無完整下班打卡 (回傳 None)。
    2. 若未填寫二次上班 (t2_in)：
       - 若二次下班 (t2_out) 有值，取 t2_out (例如僅填首次上班與二次下班)。
       - 否則若首次下班 (t1_out) 有值，取 t1_out (例如僅上午出勤半天，或僅填前兩格)。
       - 否則回傳 None。
    """
    t1_in_s = (t1_in or "").strip()
    t1_out_s = (t1_out or "").strip()
    t2_in_s = (t2_in or "").strip()
    t2_out_s = (t2_out or "").strip()

    if t2_in_s:
        return t2_out_s if t2_out_s else None
    if t2_out_s:
        return t2_out_s
    if t1_out_s:
        return t1_out_s
    return None
