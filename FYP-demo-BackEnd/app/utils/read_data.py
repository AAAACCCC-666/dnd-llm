import os
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SYSTEM_PROMPT_PATH = Path("assets/system_rule.json")
DEFAULT_OPTIONS_PROMPT_PATH = Path("assets/options_prompt.json")
DEFAULT_DND_DATA_PATH = Path("assets/dnd_data.json")


def _resolve_required_path(env_var: str, default_relative_path: Path) -> Path:
    """Resolve a filesystem path, falling back to repo default and enforcing existence."""

    raw_value = os.getenv(env_var)
    if raw_value and raw_value.strip():
        candidate = Path(raw_value.strip()).expanduser()
    else:
        candidate = default_relative_path

    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()

    if not candidate.exists():
        message = f"{env_var or default_relative_path} 指向的文件不存在: {candidate}"
        logger.error(message)
        raise FileNotFoundError(message)

    return candidate


def _load_prompt_from_file(env_var: str, default_path: Path, prompt_label: str) -> str:
    """Load prompt content from a required file."""

    file_path = _resolve_required_path(env_var, default_path)

    try:
        raw_content = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error(
            f"读取 {prompt_label} 文件失败（{file_path}）: {exc}",
        )
        raise

    try:
        json_data = json.loads(raw_content)
        content = json.dumps(json_data, ensure_ascii=False, separators=(",", ":"))
    except json.JSONDecodeError:
        content = raw_content
        logger.info(
            f"{prompt_label.capitalize()} file at {file_path} is not JSON. Using raw text."
        )

    logger.info(f"Successfully loaded {prompt_label} from {file_path}")
    return content


def load_system_prompt() -> str:
    """Load the system prompt from the configured or default file."""

    return _load_prompt_from_file(
        "SYSTEM_PROMPT_FILE_PATH", DEFAULT_SYSTEM_PROMPT_PATH, "system prompt"
    )


def load_options_prompt() -> str:
    """Load the options-generation system prompt from a configurable file."""

    return _load_prompt_from_file(
        "OPTIONS_PROMPT_FILE_PATH", DEFAULT_OPTIONS_PROMPT_PATH, "options prompt"
    )


DND_DATA_FILE_PATH = str(DEFAULT_DND_DATA_PATH)


def load_dnd_data() -> dict:
    """Load D&D metadata from a required JSON file."""

    file_path = _resolve_required_path("DND_DATA_FILE_PATH", DEFAULT_DND_DATA_PATH)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Successfully loaded D&D data from {file_path}")
            return data
    except json.JSONDecodeError as exc:
        logger.error(f"Error decoding JSON from D&D data file at {file_path}: {exc}")
        raise
    except Exception as exc:
        logger.error(f"Error reading D&D data file at {file_path}: {exc}")
        raise


def get_races() -> dict:
    """
    Loads D&D data and returns a dictionary of races.

    Returns:
        A dictionary mapping race ID (str) to race name (str).
    """
    dnd_data = load_dnd_data()
    return dnd_data.get("races", {})


def get_classes() -> dict:
    """
    Loads D&D data and returns a dictionary of classes.

    Returns:
        A dictionary mapping class ID (str) to class name (str).
    """
    dnd_data = load_dnd_data()
    return dnd_data.get("classes", {})


# Agent prompt loading functions
DEFAULT_SYNOPSIS_AGENT_PROMPT_PATH = Path("assets/synopsis_agent_prompt.json")
DEFAULT_REVISION_AGENT_PROMPT_PATH = Path("assets/revision_agent_prompt.json")
DEFAULT_OUTLINE_PLANNER_AGENT_PROMPT_PATH = Path(
    "assets/outline_planner_agent_prompt.json"
)


def _load_agent_prompt(env_var: str, default_path: Path, prompt_label: str) -> str:
    """Load agent prompt from JSON file, extracting and combining structured fields."""
    file_path = _resolve_required_path(env_var, default_path)

    try:
        raw_content = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error(
            f"读取 {prompt_label} 文件失败（{file_path}）: {exc}",
        )
        raise

    try:
        json_data = json.loads(raw_content)
        # Check if it's a dict with a single top-level key (agent name)
        if isinstance(json_data, dict) and len(json_data) == 1:
            agent_name = next(iter(json_data))
            agent_data = json_data[agent_name]
            if isinstance(agent_data, dict):
                # Combine structured fields into a plain text prompt
                parts = []
                if "Role" in agent_data:
                    parts.append(agent_data["Role"])
                if "Task" in agent_data:
                    parts.append(agent_data["Task"])
                if "Inputs" in agent_data:
                    inputs = agent_data["Inputs"]
                    if isinstance(inputs, list):
                        parts.append("Inputs:")
                        for i, inp in enumerate(inputs, 1):
                            parts.append(f"  {i}. {inp}")
                    else:
                        parts.append(f"Inputs: {inputs}")
                if "Guidelines" in agent_data:
                    guidelines = agent_data["Guidelines"]
                    if isinstance(guidelines, list):
                        parts.append("Guidelines:")
                        for i, guideline in enumerate(guidelines, 1):
                            parts.append(f"  {i}. {guideline}")
                    else:
                        parts.append(f"Guidelines: {guidelines}")
                if "Output" in agent_data:
                    parts.append(f"Output: {agent_data['Output']}")
                if "Outcome" in agent_data:
                    parts.append(f"Outcome: {agent_data['Outcome']}")
                content = "\n\n".join(parts)
                logger.info(f"Combined structured prompt for {agent_name}")
                return content
        # Fallback: extract system_prompt field if present
        if isinstance(json_data, dict) and "system_prompt" in json_data:
            content = json_data["system_prompt"]
        else:
            # Fallback to whole JSON string
            content = json.dumps(json_data, ensure_ascii=False, separators=(",", ":"))
            logger.warning(
                f"{prompt_label} file at {file_path} does not contain structured agent data, using full JSON."
            )
    except json.JSONDecodeError:
        # Not JSON, use raw text
        content = raw_content
        logger.info(
            f"{prompt_label.capitalize()} file at {file_path} is not JSON. Using raw text."
        )

    logger.info(f"Successfully loaded {prompt_label} from {file_path}")
    return content


def load_synopsis_agent_prompt() -> str:
    """Load the synopsis agent system prompt from a configurable file."""
    return _load_agent_prompt(
        "SYNOPSIS_AGENT_PROMPT_FILE_PATH",
        DEFAULT_SYNOPSIS_AGENT_PROMPT_PATH,
        "synopsis agent prompt",
    )


def load_revision_agent_prompt() -> str:
    """Load the revision agent system prompt from a configurable file."""
    return _load_agent_prompt(
        "REVISION_AGENT_PROMPT_FILE_PATH",
        DEFAULT_REVISION_AGENT_PROMPT_PATH,
        "revision agent prompt",
    )


def load_outline_planner_agent_prompt() -> str:
    """Load the outline planner agent system prompt from a configurable file."""
    return _load_agent_prompt(
        "OUTLINE_PLANNER_AGENT_PROMPT_FILE_PATH",
        DEFAULT_OUTLINE_PLANNER_AGENT_PROMPT_PATH,
        "outline planner agent prompt",
    )
