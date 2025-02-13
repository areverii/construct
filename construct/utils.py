# construct/utils.py
from datetime import datetime

def compute_duration(bl_start, bl_finish):
    """
    Compute the duration (in days) between bl_start and bl_finish.
    Returns 1 if the computed duration is 0 or negative or if an error occurs.
    """
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        start = datetime.strptime(bl_start, fmt)
        finish = datetime.strptime(bl_finish, fmt)
        duration = (finish - start).days
        return duration if duration > 0 else 1
    except Exception:
        return 1

def parse_user_date(date_str: str):
    if not date_str:
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",  # e.g., "2023-09-07 08:00:00"
        "%Y-%m-%d",           # e.g., "2023-09-07"
        "%m/%d/%y %H:%M",     # e.g., "9/7/23 8:00"
        "%m/%d/%Y %H:%M",
        "%m/%d/%y",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None