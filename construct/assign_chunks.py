from datetime import datetime

def assign_chunks(tasks: list, chunk_length_days: int) -> list:
    """
    Assign a chunk identifier to each task based on its start date.
    Tasks whose start times are within chunk_length_days of the earliest start time will be grouped together.
    
    Parameters:
      tasks (list): List of task dictionaries. Each task should have either a "bl_start" or "start_date" field.
      chunk_length_days (int): The number of days that defines each chunk.
      
    Returns:
      list: A sorted list of unique chunk identifiers (e.g., ["chunk_0", "chunk_1", ...]).
    """
    fmt = "%Y-%m-%d %H:%M:%S"

    # Find the earliest start date among tasks.
    min_date = None
    for task in tasks:
        start_str = task.get("bl_start") or task.get("start_date")
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, fmt)
            except Exception:
                continue
            if (min_date is None) or (start_dt < min_date):
                min_date = start_dt

    # If no valid start date is found, default all tasks to "chunk_0"
    if min_date is None:
        for task in tasks:
            task["chunk"] = "chunk_0"
        return ["chunk_0"]

    chunks = set()
    for task in tasks:
        start_str = task.get("bl_start") or task.get("start_date")
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, fmt)
            except Exception:
                start_dt = min_date
        else:
            start_dt = min_date

        # Calculate the difference in days from the earliest date
        delta_days = (start_dt - min_date).days
        chunk_index = delta_days // chunk_length_days
        chunk_name = f"chunk_{chunk_index}"
        task["chunk"] = chunk_name
        chunks.add(chunk_name)

    # Return the sorted list of chunk names based on the numeric order in the chunk's name.
    return sorted(list(chunks), key=lambda x: int(x.split("_")[1]))