"""
CLI commands contributed by splent_feature_post.

These commands are auto-discovered by the framework and exposed in the
SPLENT CLI under the ``feature:post`` group.

Usage::

    splent feature:post hello
"""

import click


@click.command("hello")
def hello():
    """Example command — replace with your own."""
    click.echo("  Hello from splent_feature_post!")


cli_commands = [hello]
