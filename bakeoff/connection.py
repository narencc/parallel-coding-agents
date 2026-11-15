"""Step 2: one model requests a harmless tool, and we return its result."""

import json

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from .credentials import load_credentials

CONNECTION_MODEL = "gpt-6-luna"
CONNECTION_OUTPUT_LIMIT = 1024
CHECK_TOOL = {
    "type": "function",
    "name": "connection_check",
    "description": "Check that the local learning app can handle a tool request. No files are changed.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {"message": {"type": "string", "enum": ["hello"]}},
        "required": ["message"],
        "additionalProperties": False,
    },
}


class ConnectionCheckFailed(Exception):
    """A readable, secret-free explanation of an unsuccessful check."""


def handle_check(call) -> str:
    """Accept only the one harmless action offered in this lesson."""
    if call.name != "connection_check":
        raise ConnectionCheckFailed("The model requested an unexpected tool. Nothing was executed.")
    try:
        arguments = json.loads(call.arguments)
    except (TypeError, json.JSONDecodeError):
        raise ConnectionCheckFailed("The tool request was not valid JSON. Nothing was executed.") from None
    if arguments != {"message": "hello"}:
        raise ConnectionCheckFailed("The tool arguments did not match the lesson. Nothing was executed.")
    return json.dumps({"ok": True, "message": "Your Python app received and handled the tool request."})


def status_message(error: APIStatusError) -> str:
    # Never print raw exception bodies: authentication errors may quote credentials.
    messages = {
        400: "OpenAI rejected the request settings. Check model and Responses API compatibility.",
        401: "OpenAI rejected the key. Check the active key source shown above and replace it locally.",
        403: "This API project is not permitted to use the requested model or operation.",
        404: "The requested model is unavailable to this API project. No other model was substituted.",
        429: "OpenAI reports a rate or quota limit. Check this project's API billing and limits.",
    }
    return messages.get(error.status_code, f"OpenAI returned HTTP {error.status_code}. The connection check stopped.")


def run_handshake(client, model: str = CONNECTION_MODEL) -> dict:
    """At most two bounded requests, no automatic retries or generated code execution."""
    conversation = [{"role": "user", "content": (
        "We are learning how an app connects to a GPT model. Call connection_check with "
        "message hello. After you receive its result, acknowledge success in one short sentence."
    )}]
    settings = {
        "model": model,
        "reasoning": {"effort": "low"},
        "max_output_tokens": CONNECTION_OUTPUT_LIMIT,
        "store": False,
        "include": ["reasoning.encrypted_content"],
        "tools": [CHECK_TOOL],
        "parallel_tool_calls": False,
    }
    used = {"input_tokens": 0, "output_tokens": 0}

    def record(response):
        if response.usage:
            used["input_tokens"] += response.usage.input_tokens
            used["output_tokens"] += response.usage.output_tokens
            print(f"   Request usage: {response.usage.input_tokens} input tokens, "
                  f"{response.usage.output_tokens} output tokens.", flush=True)
        if response.status != "completed":
            raise ConnectionCheckFailed("The response did not complete within the check's limits. No automatic retry.")

    print("2. Asking the model to request our connection_check tool...", flush=True)
    first = client.responses.create(
        **settings, input=conversation,
        tool_choice={"type": "function", "name": "connection_check"},
    )
    record(first)
    calls = [item for item in first.output if item.type == "function_call"]
    if len(calls) != 1:
        raise ConnectionCheckFailed("Expected one tool request but did not receive exactly one.")
    result = handle_check(calls[0])
    print('3. Received connection_check({"message": "hello"}).', flush=True)
    print("   Our Python app handled it locally. No generated code was run.", flush=True)
    # Preserve all response items, including reasoning context, for the next turn.
    conversation.extend(first.output)
    conversation.append({"type": "function_call_output", "call_id": calls[0].call_id, "output": result})
    print("4. Sending the tool result back to the same model...", flush=True)
    second = client.responses.create(**settings, input=conversation, tool_choice="none")
    record(second)
    if not second.output_text.strip():
        raise ConnectionCheckFailed("The model returned no final text acknowledgment.")
    return {"model": model, "reply": second.output_text.strip(), **used}


def connect() -> int:
    try:
        credentials = load_credentials()
    except ValueError as error:
        print(f"Not connected: {error}")
        return 1
    print(f"1. Key loaded from {credentials.source}. Its value stays private.", flush=True)
    print(f"   Testing {CONNECTION_MODEL} with at most 2 API requests, "
          f"{CONNECTION_OUTPUT_LIMIT} output tokens each. API usage is billable.", flush=True)
    try:
        with OpenAI(
            api_key=credentials.key, base_url="https://api.openai.com/v1",
            timeout=30.0, max_retries=0,
        ) as client:
            result = run_handshake(client)
    except APITimeoutError:
        print("Not connected: the request timed out. No automatic retry; usage may still be billed.")
        return 1
    except APIConnectionError:
        print("Not connected: could not reach OpenAI. Check the network and proxy settings.")
        return 1
    except APIStatusError as error:
        print(f"Not connected: {status_message(error)}")
        return 1
    except ConnectionCheckFailed as error:
        print(f"Check incomplete: {error}")
        return 1
    # Defensive redaction before displaying external text, even though the key is not in the prompt.
    reply = result["reply"].replace(credentials.key, "[redacted]")
    print(f"5. Model reply: {reply}")
    print(f"\nCONNECTED: {result['model']} completed the tool round trip.")
    print(f"Total reported usage: {result['input_tokens']} input tokens, "
          f"{result['output_tokens']} output tokens.")
    print("This verifies this model only. The other four lanes have not been checked.")
    return 0
