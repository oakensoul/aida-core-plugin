"""Interactive questionnaire system for AIDA.

This module provides functionality to load questionnaires from YAML files
and interactively collect user responses with validation, navigation, and
progress tracking.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sys

try:
    import yaml
except ImportError:
    yaml = None

from .errors import FileOperationError, ConfigurationError
from .files import read_file


def filter_questions(questions: List['Question'], inferred: Dict[str, Any]) -> List['Question']:
    """Filter questions based on inferred data.

    Questions whose IDs are present in the inferred dict will be excluded,
    as they don't need user input.

    Args:
        questions: List of all questions
        inferred: Dictionary of inferred answers

    Returns:
        List of questions that still need user input

    Example:
        >>> questions = load_questionnaire(Path("install.yml"))
        >>> inferred = {"coding_standards": "Black, flake8"}
        >>> filtered = filter_questions(questions, inferred)
        >>> # Returns all questions except coding_standards
    """
    return [q for q in questions if q.id not in inferred]


def questions_to_dict(questions: List['Question']) -> List[Dict[str, Any]]:
    """Convert Question objects to JSON-serializable dictionaries.

    This format is suitable for returning to AIDA or other callers
    who need to present questions to users.

    Args:
        questions: List of Question objects

    Returns:
        List of question dictionaries

    Example:
        >>> questions = load_questionnaire(Path("install.yml"))
        >>> question_dicts = questions_to_dict(questions)
        >>> # Returns: [{"id": "...", "question": "...", "type": "...", ...}, ...]
    """
    result = []
    for q in questions:
        question_dict = {
            "id": q.id,
            "question": q.question,
            "type": q.type,
            "required": q.required,
        }

        if q.default is not None:
            question_dict["default"] = q.default
        if q.help:
            question_dict["help"] = q.help
        if q.options:
            question_dict["options"] = q.options

        result.append(question_dict)

    return result


# Question type constants
QUESTION_TYPE_TEXT = "text"
QUESTION_TYPE_CHOICE = "choice"
QUESTION_TYPE_MULTILINE = "multiline"
QUESTION_TYPE_BOOLEAN = "boolean"

VALID_QUESTION_TYPES = {
    QUESTION_TYPE_TEXT,
    QUESTION_TYPE_CHOICE,
    QUESTION_TYPE_MULTILINE,
    QUESTION_TYPE_BOOLEAN,
}

# Input validation constants
MAX_INPUT_LENGTH = 10000  # Maximum characters for any input
MAX_MULTILINE_LENGTH = 50000  # Maximum characters for multiline input


class Question:
    """Represents a single question in a questionnaire.

    Attributes:
        id: Unique identifier for the question
        question: The question text to display
        type: Question type (text, choice, multiline, boolean)
        required: Whether the question is required
        default: Default value (optional)
        help: Help text to display (optional)
        options: List of options for choice questions (optional)
    """

    def __init__(self, data: Dict[str, Any]):
        """Initialize a Question from dictionary data.

        Args:
            data: Question data from YAML

        Raises:
            ConfigurationError: If question data is invalid
        """
        self.id = data.get("id")
        self.question = data.get("question")
        self.type = data.get("type", QUESTION_TYPE_TEXT)
        self.required = data.get("required", True)
        self.default = data.get("default")
        self.help = data.get("help")
        self.options = data.get("options", [])

        # Validate required fields
        if not self.id:
            raise ConfigurationError("Question missing required field: id")
        if not self.question:
            raise ConfigurationError(f"Question '{self.id}' missing required field: question")
        if self.type not in VALID_QUESTION_TYPES:
            raise ConfigurationError(
                f"Question '{self.id}' has invalid type: {self.type}",
                f"Valid types: {', '.join(VALID_QUESTION_TYPES)}"
            )
        if self.type == QUESTION_TYPE_CHOICE and not self.options:
            raise ConfigurationError(
                f"Question '{self.id}' is type 'choice' but has no options"
            )

    def format_prompt(self, current: int, total: int) -> str:
        """Format the question prompt for display.

        Args:
            current: Current question number (1-indexed)
            total: Total number of questions

        Returns:
            Formatted prompt string
        """
        lines = []

        # Progress indicator
        lines.append(f"\n[Question {current} of {total}]")
        lines.append("=" * 60)

        # Question text
        lines.append(f"\n{self.question}")

        # Help text if available
        if self.help:
            lines.append(f"ℹ️  {self.help}")

        # Type-specific formatting
        if self.type == QUESTION_TYPE_CHOICE:
            lines.append("\nOptions:")
            for i, option in enumerate(self.options, 1):
                lines.append(f"  {i}. {option}")
        elif self.type == QUESTION_TYPE_BOOLEAN:
            lines.append("(yes/no)")
        elif self.type == QUESTION_TYPE_MULTILINE:
            lines.append("(Enter blank line when done)")

        # Default value if available
        if self.default is not None:
            lines.append(f"\n[Default: {self.default}]")

        # Required/optional indicator
        if not self.required:
            lines.append("(Optional - press 's' to skip)")

        lines.append("")  # Blank line before input

        return "\n".join(lines)

    def validate_response(self, response: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate a user response.

        Args:
            response: User's response string

        Returns:
            Tuple of (is_valid, validated_value, error_message)

        Security:
            - Validates input length to prevent resource exhaustion
            - Checks for null bytes to prevent filesystem attacks
            - Enforces type-specific validation rules
        """
        # Security: Check for null bytes (filesystem attack vector)
        if '\x00' in response:
            return (False, None, "Invalid characters in response")

        # Security: Check input length limits
        max_length = MAX_MULTILINE_LENGTH if self.type == QUESTION_TYPE_MULTILINE else MAX_INPUT_LENGTH
        if len(response) > max_length:
            return (False, None, f"Response too long (max {max_length} characters)")

        # Empty response - use default or reject if required
        if not response.strip():
            if self.default is not None:
                return (True, self.default, None)
            elif not self.required:
                return (True, None, None)
            else:
                return (False, None, "This question is required")

        # Type-specific validation
        if self.type == QUESTION_TYPE_TEXT:
            return (True, response.strip(), None)

        elif self.type == QUESTION_TYPE_MULTILINE:
            return (True, response, None)

        elif self.type == QUESTION_TYPE_BOOLEAN:
            normalized = response.strip().lower()
            if normalized in ["y", "yes", "true", "1"]:
                return (True, True, None)
            elif normalized in ["n", "no", "false", "0"]:
                return (True, False, None)
            else:
                return (False, None, "Please enter yes or no")

        elif self.type == QUESTION_TYPE_CHOICE:
            # Accept number or exact text match
            try:
                choice_num = int(response.strip())
                if 1 <= choice_num <= len(self.options):
                    return (True, self.options[choice_num - 1], None)
                else:
                    return (False, None, f"Please enter a number between 1 and {len(self.options)}")
            except ValueError:
                # Try exact text match
                if response.strip() in self.options:
                    return (True, response.strip(), None)
                else:
                    return (False, None, "Please enter a number from the list or exact option text")

        return (False, None, "Invalid response")


def load_questionnaire(questionnaire_file: Path) -> List[Question]:
    """Load and parse a questionnaire from a YAML file.

    Args:
        questionnaire_file: Path to YAML questionnaire file

    Returns:
        List of Question objects

    Raises:
        FileOperationError: If file cannot be read
        ConfigurationError: If YAML is invalid or questionnaire format is wrong
    """
    # Check if PyYAML is available
    if yaml is None:
        raise ConfigurationError(
            "PyYAML is not installed",
            "Install with: pip install PyYAML"
        )

    # Read file content
    try:
        content = read_file(questionnaire_file)
    except FileOperationError:
        raise

    # Parse YAML
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in questionnaire file: {questionnaire_file}",
            f"YAML error: {e}"
        ) from e

    # Validate structure
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Invalid questionnaire format in {questionnaire_file}",
            "Questionnaire must be a YAML dictionary with 'questions' key"
        )

    if "questions" not in data:
        raise ConfigurationError(
            f"Questionnaire missing 'questions' key in {questionnaire_file}",
            "Add a 'questions' list to your YAML file"
        )

    if not isinstance(data["questions"], list):
        raise ConfigurationError(
            f"'questions' must be a list in {questionnaire_file}",
            "Format: questions:\n  - id: ...\n    question: ..."
        )

    # Parse questions
    questions = []
    for i, question_data in enumerate(data["questions"]):
        try:
            questions.append(Question(question_data))
        except ConfigurationError as e:
            raise ConfigurationError(
                f"Invalid question at index {i}: {e.message}",
                e.suggestion
            ) from e

    if not questions:
        raise ConfigurationError(
            f"No questions found in {questionnaire_file}",
            "Add at least one question to the questionnaire"
        )

    return questions


def get_multiline_input() -> str:
    """Get multi-line input from user.

    Returns:
        Multi-line input as single string
    """
    lines = []
    print("(Enter a blank line to finish)")
    while True:
        try:
            line = input()
            if not line.strip():
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines)


def display_navigation_help():
    """Display navigation help message."""
    print("\n" + "─" * 60)
    print("Navigation commands:")
    print("  b - Go back to previous question")
    print("  s - Skip this question (if optional)")
    print("  q - Quit questionnaire")
    print("  ? - Show this help")
    print("─" * 60 + "\n")


def run_questionnaire(questionnaire_file: Path) -> Dict[str, Any]:
    """Load questionnaire from YAML and interactively collect responses.

    This function presents questions to the user one at a time, validates
    responses, and allows navigation between questions. Progress is displayed
    as "Question X of Y" for each question.

    Args:
        questionnaire_file: Path to YAML questionnaire file

    Returns:
        dict: Question IDs mapped to user responses

    Raises:
        KeyboardInterrupt: User cancelled questionnaire (Ctrl+C)
        FileOperationError: Questionnaire file cannot be read
        ConfigurationError: Invalid questionnaire format

    Example:
        >>> responses = run_questionnaire(Path("install.yml"))
        >>> print(responses["coding_standards"])
        'PEP 8, Google style docstrings'
    """
    # Load questions
    questions = load_questionnaire(questionnaire_file)
    total_questions = len(questions)

    # Display header
    print("\n" + "═" * 60)
    print("📋 Questionnaire")
    print("═" * 60)
    print(f"\nThis questionnaire has {total_questions} questions.")
    print("You can navigate back, skip optional questions, or quit at any time.")
    display_navigation_help()

    # Collect responses
    responses = {}
    current_index = 0

    while current_index < total_questions:
        question = questions[current_index]
        current_num = current_index + 1

        # Display question
        print(question.format_prompt(current_num, total_questions))

        # Get response
        try:
            if question.type == QUESTION_TYPE_MULTILINE:
                response = get_multiline_input()
            else:
                response = input("> ").strip()

            # Check for navigation commands
            if response.lower() == 'q':
                print("\n✋ Questionnaire cancelled.")
                raise KeyboardInterrupt()

            elif response.lower() == 'b':
                if current_index > 0:
                    current_index -= 1
                    print("\n← Going back to previous question...")
                    continue
                else:
                    print("\n⚠️  Already at first question")
                    continue

            elif response.lower() == 's':
                if not question.required:
                    print("\n⏭️  Skipped")
                    current_index += 1
                    continue
                else:
                    print("\n⚠️  This question is required and cannot be skipped")
                    continue

            elif response == '?':
                display_navigation_help()
                continue

            # Validate response
            is_valid, value, error_msg = question.validate_response(response)

            if is_valid:
                # Store response (skip if None from optional question)
                if value is not None:
                    responses[question.id] = value
                    print(f"✓ Saved: {value}")
                else:
                    print("✓ Skipped")

                # Move to next question
                current_index += 1
            else:
                print(f"\n❌ {error_msg}")
                print("Please try again.\n")

        except EOFError:
            print("\n\n✋ Questionnaire cancelled (EOF)")
            raise KeyboardInterrupt()

    # Display summary
    print("\n" + "═" * 60)
    print("✅ Questionnaire Complete!")
    print("═" * 60)
    print(f"\nCollected {len(responses)} responses:")
    for qid, value in responses.items():
        # Find question for display
        q = next((q for q in questions if q.id == qid), None)
        if q:
            display_value = str(value)
            if len(display_value) > 60:
                display_value = display_value[:57] + "..."
            print(f"  • {q.question[:50]}: {display_value}")
    print()

    return responses
