# construct/utils.py

from datetime import datetime

def parse_user_date(date_str: str):
    if not date_str:
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",  # e.g. "2023-09-07 08:00:00"
        "%Y-%m-%d",           # e.g. "2023-09-07"
        "%m/%d/%y %H:%M",     # e.g. "9/7/23 8:00"
        "%m/%d/%Y %H:%M",
        "%m/%d/%y",
        "%m/%d/%Y",
    ]
    for f in formats:
        try:
            return datetime.strptime(date_str, f)
        except ValueError:
            pass
    return None