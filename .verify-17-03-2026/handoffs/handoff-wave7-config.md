---
task: validate env var documentation and docker service consistency
start: 2026-03-17T11:15:00Z
agent: wave7-config
---

## Status: IN PROGRESS

Checks to perform:
- All settings.* attribute accesses have corresponding entry in .env.example
- All os.getenv() calls reference a var documented in .env.example
- All Settings fields with no default are in .env.example
- All Docker service names referenced in code exist in docker-compose.yml
- All Docker service ports in code match docker-compose.yml definitions
