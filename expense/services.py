from datetime import date, timedelta
from django.db.models import Sum
from .models import userSetting, Expense
from .helpers import get_custom_month_range

def get_date_range(user_id, period, ref_date=None, start_param=None, end_param=None):
    """
    Determines the start and end date based on period and user settings.
    Returns (start_date, end_date, previous_start_date, previous_end_date)
    """
    if not ref_date:
        ref_date = date.today()

    # 1. Explicit Range
    if start_param and end_param:
        try:
            start = date.fromisoformat(start_param)
            end = date.fromisoformat(end_param)
            period_len = (end - start).days + 1
            prev_start = start - timedelta(days=period_len)
            prev_end = start - timedelta(days=1)
            return start, end, prev_start, prev_end
        except ValueError:
            # Fallback to monthly if invalid
            pass

    # 2. All Time
    if period == "all":
        return None, None, None, None

    # 3. Weekly
    if period == "weekly":
        start = ref_date - timedelta(days=ref_date.weekday())
        end = start + timedelta(days=6)
        prev_start = start - timedelta(days=7)
        prev_end = start - timedelta(days=1)
        return start, end, prev_start, prev_end

    # 4. Monthly (Default)
    # Get user settings for custom start day
    start_day = 1
    # Settings logic removed as month_start_date was removed from UserSetting model
    # try:
    #     settings = userSetting.objects.get(user_id=user_id)
    #     start_day = settings.month_start_date
    # except userSetting.DoesNotExist:
    #     pass

    start, end = get_custom_month_range(ref_date, start_day)
    period_len = (end - start).days + 1
    prev_start = start - timedelta(days=period_len)
    prev_end = start - timedelta(days=1)
    
    return start, end, prev_start, prev_end

def get_expense_summary(queryset):
    """
    Calculates total and category breakdown for a given queryset.
    """
    total = queryset.aggregate(total=Sum("amount"))["total"] or 0
    count = queryset.count()
    
    grouped = (
        queryset.values("category__id", "category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    by_category = [
        {
            "id": row["category__id"],
            "name": row["category__name"] or "Uncategorized",
            "total": row["total"],
        } for row in grouped
    ]

    return float(total), count, by_category
