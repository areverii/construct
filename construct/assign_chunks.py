from datetime import datetime, timedelta

def assign_chunks(tasks: list, chunk_length_days: int) -> list:
    """
    Assign a chunk identifier to each task based on the overall schedule's baseline timespan.
    
    For each task:
      - If both baseline dates (or start/end fallback fields) are missing, the task is assumed to have a duration of 0.
      - If only one is provided, a ValueError is raised.
      
    The overall schedule boundaries are computed from the tasks that have valid baseline dates.
    Tasks without any baseline dates will have their dates assumed to be the overall start date.
    
    Returns a sorted list of unique chunk identifiers.
    """
    fmt = "%Y-%m-%d %H:%M:%S"
    valid_starts = []
    valid_finishes = []
    
    # Validate tasks and accumulate valid baseline dates.
    for task in tasks:
        bs = task.get("bl_start") or task.get("start_date")
        bf = task.get("bl_finish") or task.get("end_date")
        
        # Throw an error if exactly one date is provided.
        if (bs and not bf) or (bf and not bs):
            raise ValueError(
                f"Task {task.get('task_id', 'N/A')} has only one baseline date: start: {bs}, finish: {bf}"
            )
        
        if bs and bf:
            try:
                start_dt = datetime.strptime(bs, fmt)
                valid_starts.append(start_dt)
            except Exception as e:
                raise ValueError(f"Error parsing start date '{bs}' for task {task.get('task_id', 'N/A')}: {e}")
            try:
                finish_dt = datetime.strptime(bf, fmt)
                valid_finishes.append(finish_dt)
            except Exception as e:
                raise ValueError(f"Error parsing finish date '{bf}' for task {task.get('task_id', 'N/A')}: {e}")
    
    # If no valid baseline dates exist, assign all tasks to the same chunk.
    if not valid_starts:
        for task in tasks:
            task["chunk"] = "chunk_0"
        print("No valid baseline dates found; all tasks assigned to chunk_0")
        return ["chunk_0"]
    
    overall_start = min(valid_starts)
    overall_finish = max(valid_finishes) if valid_finishes else overall_start
    total_days = (overall_finish - overall_start).days

    print("Overall start date:", overall_start)
    print("Overall finish date:", overall_finish)
    print("Total days spanned:", total_days)
    
    num_chunks = (total_days // chunk_length_days) + 1
    boundaries = [
        overall_start + timedelta(days=i * chunk_length_days)
        for i in range(num_chunks + 1)
    ]
    print("Chunk boundaries:", boundaries)
    
    # Assign each task to a chunk.
    for task in tasks:
        start_str = task.get("bl_start") or task.get("start_date")
        finish_str = task.get("bl_finish") or task.get("end_date")
        
        if not start_str and not finish_str:
            # Both missing: assume a duration of 0.
            start_dt = overall_start
            finish_dt = overall_start
        else:
            start_dt = datetime.strptime(start_str, fmt)
            finish_dt = datetime.strptime(finish_str, fmt)
        
        mid_dt = start_dt + (finish_dt - start_dt) / 2
        
        # Determine the appropriate chunk based on the midpoint.
        chunk_index = 0
        for i in range(len(boundaries) - 1):
            if boundaries[i] <= mid_dt < boundaries[i + 1]:
                chunk_index = i
                break
        task["chunk"] = f"chunk_{chunk_index}"
        print(f"Task {task.get('task_id', 'N/A')}: start={start_dt}, finish={finish_dt}, midpoint={mid_dt} => chunk_{chunk_index}")
    
    unique_chunks = sorted({task["chunk"] for task in tasks}, key=lambda x: int(x.split("_")[1]))
    print("Unique chunks assigned:", unique_chunks)
    return unique_chunks