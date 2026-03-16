<!-- version: 2026-02 -->
# Placeholder Conventions

- `.template` files: `{{ lowercase_snake_case }}` (Cookiecutter standard)
- Documentation: `<angle-brackets>` for example values
- Triggers: `[UPPER_CASE]` for user-substituted values
- Bash: `${VARIABLE}` for environment variables

## Usage in Workflows

These conventions are applied throughout `.claude/workflow/` files:
- Session start triggers use `[PROJECT_NAME]` format
- Code generation examples use `<path>` and `<module>` placeholders
- Bash commands use `${TIMESTAMP}` and `${VARIABLE}` for runtime substitution
