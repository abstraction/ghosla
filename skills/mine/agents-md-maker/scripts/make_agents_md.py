#!/usr/bin/env python3
"""
make_agents_md.py

A scaffolding and compilation tool for generating optimal `agents.md` files
based on Context Engineering best practices. It guarantees perfect XML tagging, 
hierarchical organization, and the inclusion of meta-cognitive directives.
"""

import argparse
import os

DEFAULT_META = """# Agent Persona
You are an expert AI developer and architect. Your core purpose is to execute tasks with high precision, adhering strictly to the boundaries and rules defined below.

# Core Rules
- **Absolute Compliance**: You MUST adhere to all structural constraints and project standards.
- **Escape Hatch**: If context is missing, ambiguous, or confidence is low, pause and ask the user for clarification rather than guessing or proceeding blindly."""

DEFAULT_STATIC = """# Project Standards & Tech Stack
- [List tech stack, languages, and frameworks as a structured list]
- [Define architectural rules and boundaries]

# Actionable Commands
- **Setup**: `[Insert build/setup command]`
- **Test**: `[Insert test command]`
- **Lint**: `[Insert linting command]`

# Definition of Done
- [e.g., All tests pass locally]
- [e.g., Code contains no `TODO` or `FIXME` comments]
- [e.g., Types are strictly defined]"""

DEFAULT_DYNAMIC = """# Project State
<project_state>
Phase: [e.g., Initial Setup, MVP, Bugfixing]
Current Focus: [Brief description of what is currently being worked on]
Known Issues:
  - [List ongoing bugs or architectural limitations]
</project_state>"""

DEFAULT_INSTRUCTIONS = """# Task Directives
- **Plan Before Acting**: You MUST use a `<thought_process>` block to outline your strategy before generating final code or taking action.
- [Add specific declarative tasks using verbs like "Extract", "Validate", "Generate"]"""

DEFAULT_EXAMPLES = """# Examples
<example>
<task_input>
[Insert a real-world task or edge-case here]
</task_input>

<thought_process>
[Demonstrate the reasoning steps needed to solve the problem]
</thought_process>

<correct_output>
[Provide a pristine, high-quality expected output]
</correct_output>
</example>"""

def read_section(filepath: str, default: str) -> str:
    if filepath and os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return default

def compile_agents_md(output_path: str, meta_file: str, static_file: str, dynamic_file: str, instructions_file: str, examples_file: str):
    document = []

    # 1. Meta-Context
    document.append("<meta_context>")
    document.append(read_section(meta_file, DEFAULT_META))
    document.append("</meta_context>\n")

    # 2. Static Context
    document.append("<static_context>")
    document.append(read_section(static_file, DEFAULT_STATIC))
    document.append("</static_context>\n")

    # 3. Dynamic Context
    document.append("<dynamic_context>")
    document.append(read_section(dynamic_file, DEFAULT_DYNAMIC))
    document.append("</dynamic_context>\n")
    
    # 4. Instructions
    document.append("<instructions>")
    document.append(read_section(instructions_file, DEFAULT_INSTRUCTIONS))
    document.append("</instructions>\n")

    # 5. Examples
    document.append("<examples>")
    document.append(read_section(examples_file, DEFAULT_EXAMPLES))
    document.append("</examples>\n")

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(document))

    print(f"Success: Compiled structured context into '{output_path}'")

def main():
    parser = argparse.ArgumentParser(description="Scaffold or compile an agents.md file.")
    parser.add_argument("-o", "--output", default="agents.md", help="Output file path (default: agents.md).")
    parser.add_argument("--meta", help="Path to markdown file containing Meta-Context.")
    parser.add_argument("--static", help="Path to markdown file containing Static Context.")
    parser.add_argument("--dynamic", help="Path to markdown file containing Dynamic Context.")
    parser.add_argument("--instructions", help="Path to markdown file containing Instructions.")
    parser.add_argument("--examples", help="Path to markdown file containing Few-Shot Examples.")
    
    args = parser.parse_args()
    
    compile_agents_md(
        output_path=args.output,
        meta_file=args.meta,
        static_file=args.static,
        dynamic_file=args.dynamic,
        instructions_file=args.instructions,
        examples_file=args.examples
    )

if __name__ == "__main__":
    main()
