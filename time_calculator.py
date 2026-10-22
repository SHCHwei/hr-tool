"""
考勤時間計算模組 (Attendance Time Calculator)

參考 /home/awei/develop/SideProject/GoLang_practise/HR/main.go 核心規則：
1. 基準下班時間 (workOff): 17:30:00 (Go 代碼中以 17:29:59 判斷)
2. 加班起算時間 (workOver): 17:45:00
3. 跨日判定: 下班時間小時數 < 6 (00:00 ~ 05:59) 視為跨夜加班至隔日 (加24小時)
4. 早退計算: 下班時間早於 17:30，早退時長 = 17:30 - 下班時間
5. 加班計算: 下班時間晚於 17:45，加班時長 = 下班時間 - 17:45
6. 正常緩衝區間: 17:30 <= 下班時間 <= 17:45，不計早退亦不計加班
7. 時間格式化:
   - 滿小時: "X小時Y分" (例如 "1小時0分", "1小時15分")
   - 未滿小時: "Y分" (例如 "15分", "30分")
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
    checkout_str: Optional[str], work_off: Optional[str] = DEFAULT_WORK_OFF
) -> Tuple[str, str]:
    """
    依據 GoLang HR/main.go 規則計算加班時數與早退時數。

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

    回傳：
        (overtime_str, early_str): (加班時數, 早退時數)
    """
    parsed = parse_time(checkout_str)
    if not parsed:
        return ("", "")

    h, m = parsed
    # 跨日判斷：小時 < 6 視為次日凌晨 (00:00 ~ 05:59)
    if h < 6:
        h += 24

    total_minutes = h * 60 + m

    work_off_parsed = parse_time(work_off) or parse_time(DEFAULT_WORK_OFF)
    work_off_minutes = work_off_parsed[0] * 60 + work_off_parsed[1]
    work_over_minutes = work_off_minutes + OVERTIME_BUFFER_MINUTES

    overtime_str = ""
    early_str = ""

    if total_minutes < work_off_minutes:
        early_diff = work_off_minutes - total_minutes
        early_str = format_duration(early_diff)
    elif total_minutes > work_over_minutes:
        over_diff = total_minutes - work_over_minutes
        overtime_str = format_duration(over_diff)

    return (overtime_str, early_str)


def calculate_daily_overtime_and_early(
    t1_in: Optional[str],
    t1_out: Optional[str],
    t2_in: Optional[str],
    t2_out: Optional[str],
    is_weekend: bool = False,
    work_off: Optional[str] = DEFAULT_WORK_OFF,
) -> Tuple[str, str]:
    """依平日/週末規則計算當日加班與早退時數。"""
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

    checkout_time = get_effective_checkout(t1_in, t1_out, t2_in, t2_out)
    return calculate_overtime_and_early(checkout_time, work_off)


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
