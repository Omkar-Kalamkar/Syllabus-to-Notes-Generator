# Syllabus-to-Notes Generator

**Assessment:** Generative AI Mini Project - Assessment 03  
**Problem Statement:** 27  
**Status:** Complete beginner-friendly Streamlit application using Google Gemini.

---

## 1. Project Overview

Students often receive long, unstructured syllabus text from university websites. This
project converts that syllabus into short, simple, unit-wise study notes using the Google
Gemini API.

The app:

1. Accepts pasted syllabus text.
2. Detects common unit/module headings such as `Unit I`, `Unit 1`, `UNIT - I`,
   `Module 1`, and `Chapter 1`.
3. Builds a carefully designed prompt for Gemini.
4. Generates exam-focused notes in the original topic order.
5. Displays the notes in the browser.
6. Exports the same notes as a formatted Word `.docx` file.

The project intentionally avoids databases, authentication, Docker, and complex
architecture so it can be understood and demonstrated within 1-2 days.

---

## 2. Features

### User Interface

- Clean educational Streamlit theme with a gradient header and cards.
- Large syllabus text area.
- Optional subject name input.
- Notes length selector: **Short**, **Medium**, **Detailed**.
- Unit-detection preview before generation.
- `Generate Notes` button with a loading spinner.
- `Clear / Reset` button.
- Readable Markdown rendering of generated notes.
- Raw Markdown view for learning/debugging.
- Word document download button.
- Clear error messages for common failures.

### Syllabus Processing

- Validates empty input before calling the API.
- Preserves original text lines and order.
- Detects multiple heading styles:
  - `Unit I`
  - `Unit 1`
  - `UNIT - I`
  - `Module 1`
  - `Chapter 2`
  - `Block 3`
- Keeps text before the first unit so no content is silently lost.
- If no clear unit headings are detected, sends the whole syllabus to Gemini and
  explicitly tells it **not to invent units**.

### AI Note Generation

The generated notes include:

- Unit-wise structure when units exist.
- Topic headings in the original syllabus order.
- Simple definitions and key concepts.
- Bullet points and short examples.
- Important exam points.
- A short revision summary for each unit.
- Length adaptation:
  - **Short:** quick revision notes and key points.
  - **Medium:** balanced explanations, examples, and exam points.
  - **Detailed:** fuller explanations while staying within the syllabus.

### Security

- API key is loaded from `.env` using `python-dotenv`.
- No API key is hardcoded in source code.
- The key is not displayed in the UI or logs.
- `.env` is excluded from Git.
- `.env.example` contains only a placeholder.
- Model name is configurable through `GEMINI_MODEL`.

### Word Export

- Uses `python-docx`.
- Contains notes title, subject, generation date, unit headings, topic headings,
  paragraphs, bullet points, and summaries.
- Uses consistent fonts, heading styles, spacing, and section structure.
- Downloads the actual generated notes, not placeholder content.

---

## 3. Technologies Used

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Google Gemini API |
| SDK | `google-genai` |
| Environment variables | `python-dotenv` |
| Word export | `python-docx` |
| Language | Python 3.9+ |

---

## 4. Architecture / Workflow

```text
User pastes syllabus
        |
        v
app.py validates button click and UI state
        |
        v
generator.py
  - normalize_syllabus_text()
  - validate_syllabus()
  - detect_units()
  - build_user_prompt()
  - call_gemini_api()
        |
        v
Google Gemini API
        |
        v
Generated Markdown notes
        |
        +--> Streamlit renders notes
        |
        +--> docx_generator.py converts Markdown to .docx
                  |
                  v
             Download button
```

### File Responsibilities

| File | Responsibility |
|---|---|
| `app.py` | Streamlit UI, user interaction, loading state, error display, download button |
| `generator.py` | Syllabus parsing, validation, prompts, Gemini SDK call, friendly errors |
| `docx_generator.py` | Parses Markdown notes and creates a formatted Word document |
| `requirements.txt` | Python dependencies |
| `README.md` | Setup, usage, examples, limitations, viva explanation |
| `.env` | Local private configuration with the real API key |
| `.env.example` | Safe placeholder configuration for GitHub |
| `.gitignore` | Excludes secrets, virtual environments, caches, and generated files |
| `screenshots/` | Placeholder folder for project/demo screenshots |

---

## 5. Installation on Windows and VS Code

### Step 1: Open the project in VS Code

Open this folder in VS Code:

```text
D:\Syllabus-to-Notes-Generator
```

Open a VS Code terminal (`Ctrl + ` `).

### Step 2: Create a virtual environment

From the project folder, run:

```powershell
python -m venv .venv
```

### Step 3: Activate the virtual environment

In PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

If activation is blocked by PowerShell execution policy, run this once first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.venv\Scripts\Activate.ps1
```

You should see `(.venv)` at the start of the terminal prompt.

### Step 4: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 5: Create or edit the `.env` file

A `.env` file already exists with placeholders. Replace:

```env
GEMINI_API_KEY=your_api_key_here
```

with your real key:

```env
GEMINI_API_KEY=your_real_api_key
```

Optional model override:

```env
GEMINI_MODEL=gemini-2.5-flash
```

The default model is also `gemini-2.5-flash`. Restart Streamlit after changing `.env`.

### Step 6: Run the application

```powershell
streamlit run app.py
```

### Step 7: Open the app

Streamlit prints a local address, usually:

```text
http://localhost:8501
```

Open that address in your browser.

### Step 8: Generate and download

1. Paste a syllabus.
2. Optionally enter a subject name.
3. Select Short, Medium, or Detailed.
4. Click **Generate Notes**.
5. Read the notes in the output area.
6. Click **Download Notes as Word (.docx)**.

---

## 6. API Key Setup

1. Create a Gemini API key from Google AI Studio.
2. Make sure the Gemini API is enabled for that key/project.
3. Open `.env` in the project folder.
4. Set:

```env
GEMINI_API_KEY=paste_your_real_key_here
```

5. Save the file and restart the app.

Do not leave values such as `your_api_key_here`, `your_gemini_api_key`, or
`paste_your_key_here`. These are placeholders, not API keys. A real Gemini API key is a
long value that usually starts with `AIza`.

If you see "API key not valid":

- Confirm that `.env` contains the real key, not a placeholder.
- Restart Streamlit after saving `.env`.
- Make sure the Gemini API is enabled for the Google Cloud project that owns the key.
- Check that the key has no API restrictions blocking `generativelanguage.googleapis.com`.

Security notes:

- Do not commit `.env`.
- Do not paste the key into the Streamlit UI.
- Do not share screenshots containing the key.
- If you push to GitHub, only `.env.example` should be visible.

---

## 7. Example Input

```text
Unit I: Introduction to Data Structures
- Definition of data structure
- Arrays and linked lists
- Stack and queue operations

Unit II: Trees and Graphs
- Binary tree and traversal methods
- Graph representation and BFS/DFS

Unit III: Sorting and Searching
- Linear search and binary search
- Bubble sort, selection sort, merge sort
```

### Expected Output Shape

```markdown
# Data Structures - Study Notes

## Unit I: Introduction to Data Structures

### Definition of Data Structure
- A data structure is a way of organizing and storing data...
- Important Exam Points:
  - ...

### Arrays and Linked Lists
- ...

### Unit Summary
- ...
```

The exact wording depends on Gemini, but the structure, order, and syllabus scope should
remain faithful to the input.

---

## 8. Five Manual Test Cases

### Test Case 1: Roman numeral unit headings

```text
Unit I: Basics of Programming
- Variables, data types, operators
- Control statements

Unit II: Functions and Arrays
- Function definition and call
- One-dimensional and two-dimensional arrays
```

Expected: 2 units detected; topics explained in order.

---

### Test Case 2: `UNIT - I` style with punctuation

```text
UNIT - I
Introduction to Operating Systems
- Process, thread, and scheduling

UNIT - II
Memory Management
- Paging, segmentation, virtual memory
```

Expected: 2 units detected; heading text preserved.

---

### Test Case 3: Module headings

```text
Module 1: Database Fundamentals
- DBMS architecture
- Relational model

Module 2: SQL and Normalization
- SQL queries
- Functional dependency and normal forms
```

Expected: 2 modules detected and used as unit headings.

---

### Test Case 4: Chapter headings

```text
Chapter 1: Number Systems
- Binary, octal, decimal, hexadecimal
- Boolean algebra

Chapter 2: Logic Gates
- AND, OR, NOT, NAND, NOR
- Karnaugh map
```

Expected: 2 chapters detected and preserved.

---

### Test Case 5: No clear unit headings

```text
Computer Networks syllabus:
- OSI model layers
- TCP and UDP
- IP addressing and subnetting
- Routing basics
```

Expected: app reports that no clear unit headings were detected; Gemini organizes only
these topics and does not invent Unit I/II headings.

---

## 9. Testing Performed During Development

The following checks were completed locally:

- Python syntax check for `app.py`, `generator.py`, and `docx_generator.py`.
- All third-party imports checked after installing `requirements.txt`.
- Empty syllabus validation checked.
- Missing/placeholder API key behavior checked.
- Unit detection checked against Roman numerals, digits, modules, chapters, and
  unlabelled syllabi.
- Prompt construction checked to confirm the original syllabus text is included.
- Word document generation checked with representative Markdown notes.
- Gemini SDK call syntax checked against the current `google-genai` client pattern:
  `genai.Client(...)` and `client.models.generate_content(...)`.

**Live Gemini generation was not verified because no valid API key was available in the
workspace.** Enter a real key in `.env` to test the complete AI flow.

---

## 10. Limitations

- Requires an internet connection and a valid Gemini API key.
- Very long syllabi may hit token or output limits.
- Gemini output quality depends on how clearly the syllabus is copied.
- Unit detection is pattern-based; unusual custom heading formats may not be detected.
- Generated notes are a study aid, not a replacement for textbooks or official material.
- The app is designed for single-user local use, not production deployment.
- No database or user accounts are included by design.

---

## 11. Future Enhancements

- Upload PDF or DOCX syllabus files.
- Let students edit generated notes in the browser.
- Add PDF export in addition to Word.
- Add a topic-wise quiz generator.
- Add flashcard generation from notes.
- Save previous generations in browser storage.
- Add a "Regenerate with different wording" button.
- Add model and temperature controls in the sidebar.
- Add unit tests for parser and DOCX conversion.

---

## 12. Beginner-Friendly Viva Explanation

### What problem does the project solve?

University syllabi are usually long and unstructured. Students need short, organized
notes for revision. This project uses Gemini to convert syllabus text into simple,
unit-wise notes.

### How does the project work?

The Streamlit app is the frontend. When the user clicks **Generate Notes**, `app.py`
checks that the syllabus is not empty and that an API key exists. Then `generator.py`
cleans the text, detects unit headings, and builds a prompt. The system instruction tells
Gemini to behave like an expert engineering tutor and stay strictly inside the syllabus.
The user prompt contains the subject, selected length, and structured syllabus.

Gemini returns Markdown notes. Streamlit renders those notes directly. The same Markdown
text is passed to `docx_generator.py`, which converts headings, bullets, and paragraphs
into a formatted Word document.

### Why are there three Python files?

The code is separated by responsibility:

- `app.py` handles the user.
- `generator.py` handles AI logic.
- `docx_generator.py` handles Word export.

This makes the project easier to understand, explain, and modify.

### How is the API key protected?

The key is stored in `.env`, loaded with `python-dotenv`, and ignored by Git through
`.gitignore`. It is never hardcoded or shown in the interface.

### What happens if unit headings are missing?

The parser returns the whole syllabus as one section. The prompt tells Gemini not to
invent units and to organize only the topics actually provided.

### What happens on errors?

Empty input, missing keys, invalid keys, quota problems, network failures, empty AI
responses, and DOCX failures are converted into readable messages instead of crashing the
application.

---

## 13. GitHub Readiness

Before committing, verify:

```powershell
git status
```

`.env` should not appear in the list. `.env.example` should appear.

Do not initialize or push a Git repository unless you explicitly intend to do so.
