from __future__ import annotations
import sys
from loguru import logger

# Remove default loguru handler
logger.remove()


def configure_terminal_logger(trace: bool = False) -> None:
    """
    Call once at startup. Configures loguru to emit colored, agent-tagged output.
    --trace flag shows DEBUG-level tool calls in addition to INFO agent steps.
    """
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[agent]: <20}</cyan> | "
            "{message}"
        ),
        level="DEBUG" if trace else "INFO",
        colorize=True,
        filter=lambda record: "agent" in record["extra"],
    )
    # Also add a plain non-colored handler for system messages (no agent tag)
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO",
        colorize=True,
        filter=lambda record: "agent" not in record["extra"],
    )


def get_agent_logger(agent_name: str):
    """Returns a loguru logger bound to a specific agent name."""
    return logger.bind(agent=agent_name)
