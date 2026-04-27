# ISE AI Agentic Workflow

ISE AI should operate as a general programming assistant rather than a collection of hardcoded demos.

## Execution contract

1. Understand the user's request and infer the deliverable type.
2. Create a concrete roadmap with files, commands, verification steps, and export criteria.
3. Work inside an isolated sandbox.
4. Generate code dynamically from the request context.
5. Verify with the relevant commands, such as frontend builds or backend tests.
6. Repair failures by changing strategy, command, file path, or implementation.
7. Export the verified deliverable as a ZIP artifact.
8. Keep merge into the local project optional and backed up.

## Dynamic generation rule

The project builder must not depend on fixed examples for a single business type. A request for a restaurant, doctor, travel agency, CMS, dashboard, or another project should be handled through the same dynamic flow: infer the domain and requirements, generate suitable files, verify, then export.
