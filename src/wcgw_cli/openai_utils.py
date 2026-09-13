from typing import cast

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ParsedChatCompletionMessage,
)

from wcgw.client.common import CostData, History


def estimate_tokens(text: str) -> int:
    """Estimate token count assuming ~3 characters per token."""
    return len(text) // 3


def get_input_cost(cost_map: CostData, history: History) -> tuple[float, int]:
    input_tokens = 0
    for msg in history:
        content = msg["content"]
        refusal = msg.get("refusal")
        if isinstance(content, list):
            for part in content:
                if "text" in part:
                    input_tokens += estimate_tokens(part["text"])
        elif content is None:
            if refusal is None:
                raise ValueError("Expected content or refusal to be present")
            input_tokens += estimate_tokens(str(refusal))
        elif not isinstance(content, str):
            raise ValueError(f"Expected content to be string, got {type(content)}")
        else:
            input_tokens += estimate_tokens(content)
    cost = input_tokens * cost_map.cost_per_1m_input_tokens / 1_000_000
    return cost, input_tokens


def get_output_cost(
    cost_map: CostData,
    item: ChatCompletionMessage | ChatCompletionMessageParam,
) -> tuple[float, int]:
    if isinstance(item, ChatCompletionMessage):
        content = item.content
        if not isinstance(content, str):
            raise ValueError(f"Expected content to be string, got {type(content)}")
    else:
        if not isinstance(item["content"], str):
            raise ValueError(
                f"Expected content to be string, got {type(item['content'])}"
            )
        content = item["content"]
        if item["role"] == "tool":
            return 0, 0
    output_tokens = estimate_tokens(content)

    if "tool_calls" in item:
        item = cast(ChatCompletionAssistantMessageParam, item)
        toolcalls = item["tool_calls"]
        for tool_call in toolcalls or []:
            if tool_call["type"] == "function":
                output_tokens += estimate_tokens(tool_call["function"]["arguments"])
            else:
                output_tokens += estimate_tokens(tool_call["custom"]["input"])
    elif isinstance(item, ParsedChatCompletionMessage):
        if item.tool_calls:
            for tool_callf in item.tool_calls:
                output_tokens += estimate_tokens(tool_callf.function.arguments)

    cost = output_tokens * cost_map.cost_per_1m_output_tokens / 1_000_000
    return cost, output_tokens
