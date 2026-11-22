"""``ragcourt prompts``: list every prompt a model is given, or print one exactly (design §6.6, D-030)."""

from __future__ import annotations

import argparse

from ragcourt.io.project import AddParser, open_project
from ragcourt.io.prompts import load_prompt, load_prompts
from ragcourt.io.terminal import table

NAME = "prompts"
HELP = "list the prompts models are given, or `prompts show NAME` to print one"


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``prompts``."""
    parser = add_parser(NAME, help=HELP, description=__doc__, parents=[common])
    parser.add_argument("action", nargs="?", choices=["show"], help="show one prompt")
    parser.add_argument("name", nargs="?", help="the prompt to show, e.g. judge.validity")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """List the prompts, or print one."""
    project = open_project(args.options)
    folder = project.config.prompts_dir
    if args.action == "show" and args.name:
        prompt = load_prompt(args.name, folder)
        origin = f"your file in {folder}" if prompt.replaced else "bundled with ragcourt"
        print(f"# {prompt.name} ({prompt.hash}, {origin})\n")
        print(prompt.text, end="" if prompt.text.endswith("\n") else "\n")
        return 0
    rows = [
        [prompt.name, prompt.hash, "yours" if prompt.replaced else "bundled"]
        for prompt in load_prompts(folder).values()
    ]
    print(table(["prompt", "hash", "from"], rows))
    print("\nPrint one with `ragcourt prompts show NAME`; replace one by putting NAME.txt in prompts_dir.")
    return 0
