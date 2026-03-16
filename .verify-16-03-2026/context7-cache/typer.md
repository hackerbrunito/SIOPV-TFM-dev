# Typer — Context7 Cache

## Current Version: typer 0.12+

## Key API Patterns

### App Creation
- `import typer`
- `app = typer.Typer(name="siopv", help="...", no_args_is_help=True)`
- `@app.command()` — register command
- `@app.callback()` — app-level callback (runs before any command)

### Command Parameters
- `def main(name: str = typer.Argument(..., help="..."))` — positional argument
- `def main(verbose: bool = typer.Option(False, "--verbose", "-v"))` — optional flag
- `Annotated[str, typer.Argument(help="...")]` — modern annotation style (preferred)
- `Annotated[bool, typer.Option("--verbose", "-v")]` — option with annotation

### Output
- `typer.echo("message")` — stdout
- `typer.secho("error", fg=typer.colors.RED, err=True)` — colored stderr
- `rich.print()` via Rich integration for complex output

### Error Handling
- `raise typer.Exit(code=1)` — clean exit with code
- `raise typer.Abort()` — abort execution

### Async Support
- Typer does NOT natively support async commands
- Use `asyncio.run()` wrapper inside command functions
- Or use `anyio.run()` for async entry points

### Subcommands
- `app.add_typer(sub_app, name="sub")` — add subcommand group

### Best Practices
- Use `Annotated` style for type hints (modern pattern)
- Use `typer.Option` with explicit `--flag` names
- Use `no_args_is_help=True` on app for better UX
