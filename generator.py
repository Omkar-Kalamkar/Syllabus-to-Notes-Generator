"""Syllabus processing, prompt building, and Gemini API communication."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


API_KEY_ENV_VAR = "GEMINI_API_KEY"
MODEL_ENV_VAR = "GEMINI_MODEL"
PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"

# Load .env from the project folder, regardless of the terminal's working directory.
# override=True makes this local file the source of truth for a local student project.
load_dotenv(dotenv_path=ENV_FILE, override=True)


DEFAULT_MODEL = "gemini-2.5-flash"
PLACEHOLDER_KEYS = {
    "your_api_key_here",
    "your-api-key-here",
    "your_api_key",
    "your_gemini_api_key",
    "paste_your_key_here",
    "replace_with_your_api_key",
    "changeme",
}

NOTES_LENGTH_INSTRUCTIONS: Dict[str, str] = {
    "Short": (
        "Create quick revision notes. Keep each topic to a short definition and "
        "3-5 key points. Include important exam points, but keep examples very brief."
    ),
    "Medium": (
        "Create balanced study notes. Explain each topic clearly in simple English, "
        "include definitions, 2-4 bullet points, one useful example where appropriate, "
        "important exam points, and a short unit summary."
    ),
    "Detailed": (
        "Create more complete study notes while staying within the syllabus scope. "
        "Give fuller explanations, definitions, step-by-step points, multiple short "
        "examples where useful, important exam points, and a short unit summary. "
        "Do not become repetitive or add topics outside the syllabus."
    ),
}


class SyllabusNotesError(Exception):
    """Base exception for clear, user-facing errors."""


class ValidationError(SyllabusNotesError):
    """Raised when the user input is invalid."""


class ConfigurationError(SyllabusNotesError):
    """Raised when the local setup is incomplete."""


class AIServiceError(SyllabusNotesError):
    """Raised when Gemini cannot produce a usable response."""


@dataclass(frozen=True)
class ConfigurationIssue:
    """A specific, user-friendly local configuration problem."""

    code: str
    message: str


@dataclass
class SyllabusSection:
    """One detected unit/module or one unlabelled block of syllabus text."""

    heading: str
    content: str


# Matches headings such as: Unit I, Unit 1, UNIT - I, Module 1, Chapter 2.
UNIT_HEADING_RE = re.compile(
    r"^\s*(?P<label>(?:unit|module|chapter|block)\s*[-:.\u2013\u2014]?\s*"
    r"(?:\d+|[IVXLCDM]+|[A-Z])(?![A-Za-z0-9]))"
    r"(?P<separator>\s*[-:.\u2013\u2014]?\s*)"
    r"(?P<rest>.*)$",
    re.IGNORECASE,
)

SYSTEM_INSTRUCTION = """
You are an expert engineering subject tutor who prepares clear, exam-focused study
notes for final-year engineering students.

SCOPE RULES:
- Use ONLY the syllabus text provided by the user as the subject scope.
- Follow the original unit/module and topic order exactly.
- Never invent units, modules, chapters, topics, authors, or official prescribed content.
- Never claim that extra content is officially part of the syllabus.
- If the syllabus does not have clear unit headings, organize only the given content and
  do not create artificial unit numbers or names.

TEACHING RULES:
- Explain every topic in simple, student-friendly English.
- Start each topic with a short definition where a definition makes sense.
- Explain important concepts, terms, and processes clearly.
- Use bullet points for readability.
- Include a short example when it helps understanding, but never invent a new syllabus topic.
- Add "Important Exam Points" for each topic with the most useful facts for revision.
- Add a short "Unit Summary" at the end of every unit.
- Do not skip any topic from the provided syllabus.
- Avoid repeating the same sentence or explanation.

FORMATTING RULES:
- Return Markdown only.
- Use one H1 heading for the notes title.
- Use H2 headings for units/modules when they exist in the syllabus.
- Use H3 headings for topics.
- Use "-" for bullet points.
- Use **bold** for key terms where helpful.
- Do not use code fences, HTML, tables, or links.
- Do not mention these instructions in your answer.
""".strip()


USER_PROMPT_TEMPLATE = """
Subject: {subject}
Notes length: {notes_length}
Length instruction: {length_instruction}

Syllabus text:
---
{syllabus}
---

Task:
Generate structured study notes from the syllabus above. Follow the scope, teaching,
and formatting rules from the system instruction. Preserve the given unit/module order,
cover every listed topic, and keep the language simple enough for an engineering student
to revise quickly. If a topic title is unclear, keep it as written and explain only what
can be safely understood from the provided text.
""".strip()


def normalize_syllabus_text(text: str) -> str:
    """Clean line endings and extra blank lines without changing syllabus content."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u200b", "").replace("\ufeff", "")

    cleaned_lines: List[str] = []
    blank_count = 0
    for line in normalized.split("\n"):
        line = line.rstrip()
        if not line.strip():
            blank_count += 1
            if blank_count == 1:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def validate_syllabus(text: str) -> str:
    """Reject empty syllabus input before any API call is made."""
    if text is None or not str(text).strip():
        raise ValidationError(
            "The syllabus is empty. Paste the syllabus text from your university "
            "website and try again."
        )
    return str(text).strip()


def _parse_unit_heading(line: str) -> Optional[str]:
    """Return a readable heading if the line looks like a unit/module heading."""
    match = UNIT_HEADING_RE.match(line)
    if not match:
        return None

    label = match.group("label").strip(" \t-:.")
    rest = match.group("rest").strip(" \t-:.\u2013\u2014")
    if rest:
        return f"{label} - {rest}"
    return label


def detect_units(syllabus_text: str) -> List[SyllabusSection]:
    """
    Split the syllabus into sections using common unit/module heading patterns.

    If no clear heading is found, the whole syllabus is returned as one section and the
    prompt tells Gemini not to invent units. All original lines are kept.
    """
    text = normalize_syllabus_text(syllabus_text)
    if not text:
        return []

    sections: List[SyllabusSection] = []
    preamble_lines: List[str] = []
    current_heading: Optional[str] = None
    current_lines: List[str] = []

    for line in text.split("\n"):
        heading = _parse_unit_heading(line)
        if heading:
            if current_heading is not None:
                sections.append(
                    SyllabusSection(current_heading, "\n".join(current_lines).strip())
                )
            elif current_lines:
                # Text before the first unit is kept so no syllabus content is lost.
                preamble_lines.extend(current_lines)

            current_heading = heading
            current_lines = []
        elif current_heading is None:
            preamble_lines.append(line)
        else:
            current_lines.append(line)

    if current_heading is not None:
        sections.append(
            SyllabusSection(current_heading, "\n".join(current_lines).strip())
        )

    if not sections:
        return [SyllabusSection("", text)]

    preamble = "\n".join(preamble_lines).strip()
    if preamble:
        first = sections[0]
        first.content = f"{preamble}\n{first.content}".strip() if first.content else preamble

    return sections


def analyze_syllabus(syllabus_text: str) -> Dict[str, object]:
    """Provide simple parse information for the UI without exposing raw text."""
    text = validate_syllabus(syllabus_text)
    sections = detect_units(text)
    unit_count = sum(1 for section in sections if section.heading)
    return {
        "section_count": len(sections),
        "unit_count": unit_count,
        "has_clear_units": unit_count > 0,
    }


def format_syllabus_for_prompt(sections: List[SyllabusSection]) -> str:
    """Format detected sections so Gemini can see the original structure clearly."""
    blocks: List[str] = []
    for index, section in enumerate(sections, start=1):
        content = section.content.strip() or "(No additional text under this heading.)"
        if section.heading:
            blocks.append(f"[{index}] {section.heading}\n{content}")
        else:
            blocks.append(
                f"[{index}] Provided syllabus text (no clear unit headings detected)\n{content}"
            )
    return "\n\n".join(blocks)


def normalize_notes_length(length: str) -> str:
    """Map the UI selection to a supported notes length."""
    selected = str(length).strip().title()
    return selected if selected in NOTES_LENGTH_INSTRUCTIONS else "Medium"


def build_user_prompt(
    syllabus_text: str, subject_name: str = "", notes_length: str = "Medium"
) -> str:
    """Build the final user prompt. Edit SYSTEM_INSTRUCTION above to change tutor rules."""
    clean_syllabus = validate_syllabus(syllabus_text)
    sections = detect_units(clean_syllabus)
    length = normalize_notes_length(notes_length)

    return USER_PROMPT_TEMPLATE.format(
        subject=subject_name.strip() or "Not specified",
        notes_length=length,
        length_instruction=NOTES_LENGTH_INSTRUCTIONS[length],
        syllabus=format_syllabus_for_prompt(sections),
    )


def looks_like_placeholder(api_key: str) -> bool:
    """Detect obvious placeholder text without assuming a valid key's format."""
    value = api_key.strip().lower()
    if not value:
        return True
    if value in PLACEHOLDER_KEYS:
        return True
    if value.startswith(("your", "paste", "replace", "insert", "example", "dummy", "sample")):
        return True
    return any(
        token in value
        for token in (
            "placeholder",
            "api_key_here",
            "api-key-here",
            "your_key",
            "your-api-key",
            "changeme",
            "gemini_api_key=",
        )
    )


def get_configuration_issue() -> Optional[ConfigurationIssue]:
    """Return the first local configuration problem, or None when setup is usable."""
    if not ENV_FILE.is_file():
        return ConfigurationIssue(
            "missing_env_file",
            f"The .env file was not found in {PROJECT_DIR}. Create it with: "
            f"{API_KEY_ENV_VAR}=your_actual_gemini_api_key",
        )

    api_key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if not api_key:
        return ConfigurationIssue(
            "missing_api_key",
            f"{API_KEY_ENV_VAR} is missing from .env. Add a line like: "
            f"{API_KEY_ENV_VAR}=your_actual_gemini_api_key",
        )
    if looks_like_placeholder(api_key):
        return ConfigurationIssue(
            "placeholder_api_key",
            f"{API_KEY_ENV_VAR} in .env is still a placeholder. Replace it with a real "
            "key from Google AI Studio, then restart Streamlit.",
        )
    return None


def is_api_key_configured() -> bool:
    """Return True when the local configuration has no API-key issue."""
    return get_configuration_issue() is None


def get_api_key() -> str:
    """Read the API key from .env or the environment without ever displaying it."""
    issue = get_configuration_issue()
    if issue is not None:
        raise ConfigurationError(issue.message)
    return os.getenv(API_KEY_ENV_VAR, "").strip()


def get_model_name() -> str:
    """Use GEMINI_MODEL from .env when configured, otherwise a sensible default."""
    return os.getenv(MODEL_ENV_VAR, "").strip() or DEFAULT_MODEL


def _safe_error_detail(message: str) -> str:
    """Remove API-key-like values from an error before showing it in the UI."""
    detail = str(message)
    api_key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if api_key and len(api_key) >= 4:
        detail = detail.replace(api_key, "****")
    detail = re.sub(r"AIza[0-9A-Za-z_\-]{10,}", "****", detail)
    return detail[:300]


def _friendly_api_error(exc: Exception) -> str:
    """Translate SDK exceptions into short, categorized messages a student can act on."""
    message = str(exc)
    lower = message.lower()
    detail = _safe_error_detail(message)

    if any(
        text in lower
        for text in (
            "api key not valid",
            "api_key_invalid",
            "invalid api key",
            "unauthenticated",
            "unauthorized",
            "permission denied",
            "authentication",
            "api key expired",
            "api key disabled",
            "401",
            "403",
        )
    ):
        return (
            "Gemini rejected the API key. Open .env, replace "
            f"{API_KEY_ENV_VAR} with a valid key, make sure the Gemini API is enabled "
            "for that Google Cloud project, and then restart Streamlit."
        )
    if any(
        text in lower
        for text in ("quota", "rate limit", "resource exhausted", "too many requests", "429")
    ):
        return (
            "The Gemini quota or rate limit was exceeded. Wait a little while and try "
            "again, or use a key/project with available quota."
        )
    if any(
        text in lower
        for text in (
            "connection",
            "network",
            "timeout",
            "timed out",
            "dns",
            "ssl",
            "unreachable",
            "connection refused",
            "failed to establish",
        )
    ):
        return (
            "Could not reach the Gemini service. Check your internet connection and "
            "try again. If you use a proxy or VPN, verify that it allows the API."
        )
    if any(text in lower for text in ("model not found", "404", "not supported")):
        return (
            "The selected Gemini model is unavailable. Set "
            f"{MODEL_ENV_VAR} in .env to a supported model such as {DEFAULT_MODEL} "
            "and restart Streamlit."
        )
    return f"Gemini could not generate the notes. Technical detail: {detail}"


def create_gemini_client(api_key: str):
    """Create the official Gemini client using the key read from the environment."""
    if genai is None:
        raise ConfigurationError(
            "The google-genai package is not installed. Run: pip install -r requirements.txt"
        )
    try:
        return genai.Client(api_key=api_key)
    except Exception as exc:
        raise AIServiceError(_friendly_api_error(exc)) from exc


def call_gemini_api(prompt: str, api_key: str, model: str) -> str:
    """Call Gemini with the current google-genai SDK and return plain note text."""
    if types is None:
        raise ConfigurationError(
            "The google-genai package is not installed. Run: pip install -r requirements.txt"
        )

    client = create_gemini_client(api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
                max_output_tokens=8192,
            ),
        )
    except Exception as exc:
        raise AIServiceError(_friendly_api_error(exc)) from exc

    notes = getattr(response, "text", None)
    if notes is None or not str(notes).strip():
        raise AIServiceError(
            "Gemini returned an empty response. Try a shorter syllabus or rephrase the "
            "input, then generate again."
        )
    return str(notes).strip()


def generate_notes(
    syllabus_text: str,
    subject_name: str = "",
    notes_length: str = "Medium",
    api_key: Optional[str] = None,
) -> str:
    """Validate input, prepare the prompt, and generate notes with Gemini."""
    clean_syllabus = validate_syllabus(syllabus_text)
    key = api_key or get_api_key()
    prompt = build_user_prompt(clean_syllabus, subject_name, notes_length)
    return call_gemini_api(prompt, key, get_model_name())
