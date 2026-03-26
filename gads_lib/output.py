import json

import click


def flatten(obj, prefix=""):
    """Flatten nested dict for table display."""
    items = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(flatten(v, key))
            else:
                items[key] = v
    return items


def print_table(rows, columns=None):
    """Print rows as an aligned terminal table."""
    if not rows:
        click.echo("  (no results)")
        return
    if columns is None:
        columns = list(rows[0].keys())

    widths = {c: len(c) for c in columns}
    str_rows = []
    for row in rows:
        sr = {}
        for c in columns:
            val = row.get(c, "")
            if val is None:
                val = "—"
            elif isinstance(val, float):
                val = f"{val:,.2f}"
            else:
                val = str(val)
            sr[c] = val
            widths[c] = max(widths[c], len(val))
        str_rows.append(sr)

    header = "  ".join(c.ljust(widths[c]) for c in columns)
    click.secho(header, fg="cyan", bold=True)
    click.echo("  ".join("─" * widths[c] for c in columns))
    for sr in str_rows:
        click.echo("  ".join(sr[c].ljust(widths[c]) for c in columns))


def print_json(data):
    """Pretty-print JSON to stdout."""
    click.echo(json.dumps(data, indent=2, default=str))
