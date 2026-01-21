---
type: reference
title: "Feedback Actions"
description: "Handles /aida feedback, /aida bug, and /aida feature-request commands"
---

# Feedback Actions

Handles `/aida feedback`, `/aida bug`, and `/aida feature-request` commands.

## Quick Start

All feedback commands follow the same pattern:

1. Collect data via `AskUserQuestion`
2. Format as JSON
3. Run script with `--json` flag
4. Display result with issue URL

---

## Progressive Disclosure

### Level 1: The Pattern

**For all feedback commands:**

```text
1. Use AskUserQuestion to collect required fields
2. Format collected data as JSON
3. Run: python3 {base_directory}/scripts/feedback.py {command} --json='{...}'
4. Parse response and display success message
```

#### JSON format

- Use single quotes around the JSON string
- Use double quotes inside the JSON
- Escape any user input that contains quotes

### Level 2: Data Collection

#### For `/aida feedback`

Use `AskUserQuestion` to collect:

- **Message** (text, required): "What feedback would you like to share?"
- **Category** (select, required): Setup/Installation, Skills, Commands, Documentation, UX, Other
- **Context** (text, optional): "Any additional context?"

Format as:

```json
{
  "message": "user's feedback here",
  "category": "User Experience",
  "context": "optional additional details"
}
```

#### For `/aida bug`

Use `AskUserQuestion` to collect:

- **Description** (text, required): "Describe the bug"
- **Steps** (text, required): "Steps to reproduce"
- **Expected** (text, required): "What should happen?"
- **Actual** (text, required): "What actually happens?"
- **Severity** (select, required): Critical, Major, Minor

Format as:

```json
{
  "description": "brief bug description",
  "steps": "1. Do this\n2. Do that",
  "expected": "should do X",
  "actual": "does Y instead",
  "severity": "Major"
}
```

#### For `/aida feature-request`

Use `AskUserQuestion` to collect:

- **Title** (text, required): "Feature title"
- **Use case** (text, required): "Why do you need this?"
- **Solution** (text, optional): "How should it work?"
- **Priority** (select, required): High, Medium, Low
- **Alternatives** (text, optional): "What alternatives did you consider?"

Format as:

```json
{
  "title": "feature title",
  "use_case": "I need this because...",
  "solution": "It should work like...",
  "priority": "Medium",
  "alternatives": "I considered..."
}
```

### Level 3: Script Execution

#### Command format

```bash
python3 {base_directory}/scripts/feedback.py {action} --json='{json_data}'
```

Where `{action}` is: `feedback`, `bug`, or `feature-request`

#### Example

```bash
python3 /path/to/scripts/feedback.py feedback --json='{"message": "Great tool!", "category": "User Experience", "context": "Love the CLI"}'
```

#### Script returns JSON

```json
{
  "success": true,
  "message": "Feedback submitted successfully",
  "issue_url": "https://github.com/oakensoul/aida-marketplace/issues/123",
  "issue_number": 123
}
```

### Level 4: Response Display

**On success:**

```text
✅ Feedback submitted successfully!

Your feedback has been created as issue #123:
https://github.com/oakensoul/aida-marketplace/issues/123

Thank you for helping improve AIDA!
```

Adjust message based on action:

- `feedback` → "Feedback submitted"
- `bug` → "Bug report submitted"
- `feature-request` → "Feature request submitted"

**On failure:**

```text
❌ Failed to submit feedback

Error: {error message from script}

You can try again or report this issue at:
https://github.com/oakensoul/aida-marketplace/issues
```

### Level 5: Error Handling

#### User cancels AskUserQuestion

- Display "Submission cancelled."
- Don't call the script

#### Invalid JSON construction

- Validate JSON before passing to script
- Escape special characters in user input
- Handle newlines in text fields (use `\n`)

#### Script errors

- Capture stderr and exit code
- Display user-friendly error
- Provide fallback: direct GitHub link

#### Network/GitHub errors

- Script will handle and return error in JSON
- Display the error message
- Suggest checking connectivity or trying later

---

## AskUserQuestion Examples

### Feedback question

```javascript
{
  "questions": [
    {
      "question": "What feedback would you like to share?",
      "header": "Feedback",
      "options": [
        {"label": "General feedback", "description": "Share your thoughts about AIDA"},
        {"label": "Suggestion", "description": "Suggest an improvement"},
        {"label": "Question", "description": "Ask a question"}
      ],
      "multiSelect": false
    }
  ]
}
```

### Bug severity

```javascript
{
  "question": "How severe is this bug?",
  "header": "Severity",
  "options": [
    {"label": "Critical", "description": "Blocks all work, no workaround"},
    {"label": "Major", "description": "Significant impact, workaround exists"},
    {"label": "Minor", "description": "Small issue, easily worked around"}
  ],
  "multiSelect": false
}
```

---

## Script Details

The `feedback.py` script:

- Accepts three commands: `feedback`, `bug`, `feature-request`
- Requires `--json` flag with properly formatted data
- Automatically includes environment info for bugs
- Creates GitHub issues via API
- Returns structured JSON response

See `docs/API.md` for complete JSON schemas and script interface.
