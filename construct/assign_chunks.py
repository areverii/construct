# from datetime import datetime, timedelta

# def assign_chunks(tasks: list, chunk_length_days: int) -> list:
#     """
#     Assign a chunk identifier to each task based on the overall schedule's baseline timespan.
#     This version uses each task’s midpoint (computed from bl_start and bl_finish)
#     to determine its chunk. The overall schedule boundaries are computed using the earliest
#     bl_start and the latest bl_finish of all tasks.
    
#     Parameters:
#         tasks (list): List of task dictionaries. Each task should have "bl_start" and, ideally, "bl_finish".
#         chunk_length_days (int): The length (in days) of each chunk.
        
#     Returns:
#         list: Sorted list of unique chunk identifiers (e.g. ["chunk_0", "chunk_1", ...]).
#     """
#     fmt = "%Y-%m-%d %H:%M:%S"
#     valid_starts = []
#     valid_finishes = []
    
#     for task in tasks:
#         # Gather baseline start/finish dates if available.
#         bs = task.get("bl_start")
#         bf = task.get("bl_finish")
#         if bs:
#             try:
#                 valid_starts.append(datetime.strptime(bs, fmt))
#             except Exception:
#                 pass
#         if bf:
#             try:
#                 valid_finishes.append(datetime.strptime(bf, fmt))
#             except Exception:
#                 pass
    
#     # If no valid baseline start is found, assign all tasks to the same chunk.
#     if not valid_starts:
#         for task in tasks:
#             task["chunk"] = "chunk_0"
#         return ["chunk_0"]
    
#     overall_start = min(valid_starts)
#     # Use overall_finish if found; otherwise default to overall_start.
#     overall_finish = max(valid_finishes) if valid_finishes else overall_start
#     total_days = (overall_finish - overall_start).days
#     # Determine the number of chunks covering the overall timespan.
#     num_chunks = (total_days // chunk_length_days) + 1
#     # Create boundaries for chunks.
#     boundaries = [overall_start + timedelta(days=i * chunk_length_days) for i in range(num_chunks + 1)]
    
#     # For each task, compute the midpoint of its baseline period and assign a chunk.
#     for task in tasks:
#         try:
#             start_dt = datetime.strptime(task.get("bl_start"), fmt)
#         except Exception:
#             start_dt = overall_start
#         try:
#             finish_dt = datetime.strptime(task.get("bl_finish"), fmt)
#         except Exception:
#             finish_dt = start_dt
        
#         mid_dt = start_dt + (finish_dt - start_dt) / 2
        
#         # Find the index such that boundaries[i] <= mid_dt < boundaries[i+1]
#         chunk_index = 0
#         for i in range(len(boundaries) - 1):
#             if boundaries[i] <= mid_dt < boundaries[i+1]:
#                 chunk_index = i
#                 break
#         task["chunk"] = f"chunk_{chunk_index}"
    
#     # Return a sorted list of unique chunk names.
#     unique_chunks = sorted({task["chunk"] for task in tasks}, key=lambda x: int(x.split("_")[1]))
#     return unique_chunks

from datetime import datetime, timedelta

def assign_chunks(tasks: list, chunk_length_days: int) -> list:
    fmt = "%Y-%m-%d %H:%M:%S"
    valid_starts = []
    valid_finishes = []

    # Gather baseline dates, trying both the baseline and start/end date fields.
    for task in tasks:
        # Use bl_start if available; otherwise, fall back to start_date.
        bs = task.get("bl_start") or task.get("start_date")
        # Use bl_finish if available; otherwise, fall back to end_date.
        bf = task.get("bl_finish") or task.get("end_date")
        if bs:
            try:
                valid_starts.append(datetime.strptime(bs, fmt))
            except Exception as e:
                print("Error parsing start date:", bs, e)
        if bf:
            try:
                valid_finishes.append(datetime.strptime(bf, fmt))
            except Exception as e:
                print("Error parsing finish date:", bf, e)

    if not valid_starts:
        # If no valid start is found, assign all tasks to the same chunk.
        for task in tasks:
            task["chunk"] = "chunk_0"
        print("No valid start date found; all tasks assigned to chunk_0")
        return ["chunk_0"]

    overall_start = min(valid_starts)
    overall_finish = max(valid_finishes) if valid_finishes else overall_start
    total_days = (overall_finish - overall_start).days

    print("Overall start date:", overall_start)
    print("Overall finish date:", overall_finish)
    print("Total days spanned:", total_days)

    # Determine the number of chunks
    num_chunks = (total_days // chunk_length_days) + 1
    boundaries = [
        overall_start + timedelta(days=i * chunk_length_days)
        for i in range(num_chunks + 1)
    ]
    print("Chunk boundaries:", boundaries)

    # For each task, compute its midpoint and assign a chunk.
    for task in tasks:
        # Try to use bl_start/finish; if missing, fallback to start_date/end_date.
        try:
            start_dt = datetime.strptime(task.get("bl_start") or task.get("start_date"), fmt)
        except Exception:
            start_dt = overall_start
        try:
            finish_dt = datetime.strptime(task.get("bl_finish") or task.get("end_date"), fmt)
        except Exception:
            finish_dt = start_dt

        duration = finish_dt - start_dt
        mid_dt = start_dt + duration / 2

        # Determine chunk based on which boundary interval the midpoint falls into.
        chunk_index = 0
        for i in range(len(boundaries) - 1):
            if boundaries[i] <= mid_dt < boundaries[i + 1]:
                chunk_index = i
                break
        task["chunk"] = f"chunk_{chunk_index}"
        print(f"Task {task.get('task_id', 'N/A')}: start={task.get('bl_start') or task.get('start_date')}, "
              f"finish={task.get('bl_finish') or task.get('end_date')}, midpoint={mid_dt} => chunk_{chunk_index}")

    unique_chunks = sorted({task["chunk"] for task in tasks}, key=lambda x: int(x.split("_")[1]))
    print("Unique chunks assigned:", unique_chunks)
    return unique_chunks