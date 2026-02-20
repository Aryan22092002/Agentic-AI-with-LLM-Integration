import argparse
import os
import textwrap
from generator import build_prompt, call_llm, parse_files_from_response, load_tokens
from validator import validate_all


def orchestrate(prompt: str, out_dir: str, max_retries: int = 3):
    tokens = load_tokens()
    system_prompt = build_prompt(prompt, tokens)

    attempt = 0
    last_response = None
    while attempt < max_retries:
        attempt += 1
        print(f"Generation attempt {attempt}...")
        resp = call_llm(system_prompt)
        last_response = resp
        files = parse_files_from_response(resp)
        if not files:
            print("No files parsed from LLM output — retrying...")
            system_prompt = (
                system_prompt
                + "\nThe previous response didn't include file markers. Return only file blocks as requested."
            )
            continue
        errors = validate_all(files, os.path.join(os.path.dirname(__file__), 'design-tokens.json'))
        if not errors:
            print("Validation passed — writing files...")
            write_files(out_dir, files)
            return files
        # prepare critic re-prompt
        err_text = '\n'.join(errors)
        critique = textwrap.dedent(f"""
        The validator found the following errors:\n{err_text}\n
        Fix the generated files so that:
        - All tokens from the design system are used (either their values or token names).
        - Syntax issues reported are corrected.
        Output the corrected files only in the same file marker format.
        """)
        system_prompt = system_prompt + "\n" + critique + "\nPrevious output:\n" + resp
        print("Validator reported errors — re-prompting LLM to fix them...")

    print("Max retries reached. Writing last attempt to disk for inspection.")
    if last_response:
        files = parse_files_from_response(last_response)
        write_files(out_dir, files)
    return None


def write_files(out_dir: str, files: dict):
    os.makedirs(out_dir, exist_ok=True)
    for path, content in files.items():
        # normalize path: if only filename provided, write directly
        filename = os.path.basename(path)
        target = os.path.join(out_dir, filename)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Wrote {target}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--prompt', '-p', help='Natural language description of component (if omitted, reads from stdin or prompts interactively)')
    p.add_argument('--out', '-o', default='generated_output', help='Output directory')
    p.add_argument('--retries', '-r', type=int, default=3, help='Max retries for self-correction')
    args = p.parse_args()
    prompt = args.prompt
    if not prompt:
        import sys
        # If piped input is present, read it
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        else:
            try:
                prompt = input("Enter component prompt: ").strip()
            except EOFError:
                prompt = ""

    if not prompt:
        print("Error: No prompt provided. Provide --prompt or pipe text into stdin.")
        p.print_help()
        return

    orchestrate(prompt, args.out, args.retries)


if __name__ == '__main__':
    main()
