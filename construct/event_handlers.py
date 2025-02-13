from construct.eventing import event_manager, Event
from construct.pddl_generation import generate_domain_for_target, generate_pddl_chunks_for_schedule

def schedule_ingested_handler(event: Event):
    payload = event.payload
    schedule_id = payload.get("schedule_id")
    schedule_type = payload.get("schedule_type")
    engine = payload.get("engine")
    project_folder = payload.get("project_folder")
    auto_generate = payload.get("auto_generate_pddl", False)

    if auto_generate:
        if schedule_type == "target":
            # When a target schedule is ingested, just generate the domain.
            generate_domain_for_target(schedule_id, engine, output_dir=project_folder)
            print(f"Domain PDDL generated for target schedule {schedule_id}.")
        elif schedule_type == "in-progress":
            # In-progress ingestions update the problem (chunk) files.
            generate_pddl_chunks_for_schedule(schedule_id, engine, chunk_length_days=28, output_dir=project_folder)
            print(f"Problem chunks updated for in-progress schedule {schedule_id}.")

# Register the handler
event_manager.add_listener("schedule_ingested", schedule_ingested_handler)