import os
import re
import json
from typing import Dict, Tuple

try:
    import openai
except Exception:
    openai = None

TOKENS_PATH = os.path.join(os.path.dirname(__file__), "design-tokens.json")


def load_tokens(path: str = TOKENS_PATH) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tokens", {})


def build_prompt(user_prompt: str, tokens: Dict[str, str]) -> str:
    # Prompt engineering: ask for raw file sections only
    token_lines = "\n".join([f"{k}: {v}" for k, v in tokens.items()])
    system = (
        "You are a code generator that outputs files only. Never include explanation text."
        " Output files in this exact format:\n"
        "--- FILE: path/filename.ext ---\n"
        "<file contents>\n"
        "--- FILE: path/other.ext ---\n"
        "<file contents>\n"
        "Use the design tokens below exactly (use their values or CSS variables matching them)."
    )
    user = (
        f"Design tokens:\n{token_lines}\n\nGenerate an Angular component (TypeScript+HTML+SCSS) for: {user_prompt}\n"
        "Use Tailwind classes or Angular Material as appropriate, but ensure colors and other visual tokens"
        " come from the provided tokens. Output files only using the file marker format above."
    )
    return system + "\n\n" + user


def parse_files_from_response(text: str) -> Dict[str, str]:
    pattern = r"^--- FILE: (.+?) ---\n([\s\S]*?)(?=^--- FILE: |\Z)"
    parts = re.findall(pattern, text, flags=re.M)
    files = {}
    for path, content in parts:
        files[path.strip()] = content.lstrip("\n")
    return files


def call_llm(prompt_text: str, model: str = None, temperature: float = 0.0) -> str:
    model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
    if openai and os.environ.get("OPENAI_API_KEY"):
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": prompt_text}],
            temperature=temperature,
            max_tokens=2500,
        )
        return resp["choices"][0]["message"]["content"]
    # Fallback mock generator if no API key present
    return mock_generate(prompt_text)


def mock_generate(prompt_text: str) -> str:
    # Very small mock: returns a simple Angular component using design token values found in prompt
    # This is only for local testing when no LLM key is available.
    m = re.search(r"primary-color:\s*(#?[0-9a-fA-F(),.%\s]+)", prompt_text)
    primary = m.group(1) if m else "#6366f1"
    content_ts = (
        "import { Component } from '@angular/core';\n\n"
        "@Component({\n  selector: 'app-generated',\n  templateUrl: './generated.component.html',\n"
        "  styleUrls: ['./generated.component.scss']\n})\nexport class GeneratedComponent {}\n"
    )
    content_html = (
        "<div class=\"generated-card\">\n  <h2>Generated Component</h2>\n  <button class=\"primary\">Sign in</button>\n</div>\n"
    )
    content_scss = (
        f".generated-card {{\n  background: {primary};\n  border-radius: 8px;\n  padding: 1.25rem;\n}}\n.primary {{\n  background: white;\n  color: {primary};\n  border-radius: 6px;\n}}\n"
    )
    out = (
        "--- FILE: generated.component.ts ---\n" + content_ts + "\n"
        "--- FILE: generated.component.html ---\n" + content_html + "\n"
        "--- FILE: generated.component.scss ---\n" + content_scss + "\n"
    )
    return out


if __name__ == "__main__":
    # quick local test
    tokens = load_tokens()
    p = build_prompt("A login card with a glassmorphism effect", tokens)
    print(call_llm(p))
