TODO:
- [ ] Overhaul .cproj format
    - [ ] Switch to local sqlite cache
    - [ ] Build protobuf format
    - [ ] Build protobuf compiler
    - [ ] Handle automatic syncing with remote db

- [ ] Fix pytest dependencies not working

- [ ] Overhaul database architecture (Ontology)
    - [ ] SQL db
    - [ ] objects? like Palantir Foundry... allow for generalized ingestion?
    - [ ] Neo4j
    - [ ] Vector

- [ ] Check w/ tj to revise SQL part of ontology

- [ ] Hybrid ontology retrieval

- [ ] Define agentic architecture
    - [ ] Progressive retrieval algorithm


- [ ] split regression tests:
    test project creation - creates a project and validates the cproj file that is generated
    test target ingestion - ingests the target schedule and validates that a PDDL domain was generated
    test in_progress ingestion - ingests an in-progress schedule update and validates that PDDL problem chunks were created.
    validate_pddl_domain- validate the structure of the domain PDDL file
    validate_pddl_problems - validate the structure of the problem PDDL chunks
    validate_pddl_mapping - validate the mapping of SQL to PDDL and that we have the correct number of chunks, etc.