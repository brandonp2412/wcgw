import select
import sys
import termios
import tty
from typing import Literal
from pydantic import BaseModel


class CostData(BaseModel):
    cost_per_1m_input_tokens: float
    cost_per_1m_output_tokens: float


from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ParsedChatCompletionMessage,
)

History = list[ChatCompletionMessageParam]
Models = Literal["gpt-4o-2024-08-06", "gpt-4o-mini"]


def discard_input() -> None:
    try:
        fd = sys.stdin.fileno()

        old_settings = termios.tcgetattr(fd)

        try:
            tty.setcbreak(fd)

            while True:
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
                else:
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except (termios.error, ValueError) as e:
        print(f"Warning: Unable to discard input. Error: {e}")
