from datetime import date, timedelta
import calendar


def _clamp_day(year: int, month: int, day: int) -> int:
    # Ensure the day is not bigger than the last day of that month.

    last_day = calendar.monthrange(year, month)[1]
    return min(day, last_day)


def _add_month(year: int, month: int) -> tuple[int, int]:
    # Return (year, month) for the next month.
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _subtract_month(year: int, month: int) -> tuple[int, int]:
    # Return (year, month) for the previous month.
    if month == 1:
        return year - 1, 12
    return year, month - 1


def get_custom_month_range(ref_date: date, start_day: int) -> tuple[date, date]:
    
    if start_day < 1:
        start_day = 1
    if start_day > 28:
        start_day = 28

    y, m, d = ref_date.year, ref_date.month, ref_date.day

    if d >= start_day:
        # current period started this month
        start = date(y, m, _clamp_day(y, m, start_day))
        ny, nm = _add_month(y, m)
        next_period_start = date(ny, nm, _clamp_day(ny, nm, start_day))
        end = next_period_start - timedelta(days=1)
    else:
        # current period started last month
        py, pm = _subtract_month(y, m)
        start = date(py, pm, _clamp_day(py, pm, start_day))
        this_period_start = date(y, m, _clamp_day(y, m, start_day))
        end = this_period_start - timedelta(days=1)

    return start, end
