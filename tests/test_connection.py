"""Offline checks of the connection flow; never read the real key or call OpenAI."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bakeoff import credentials
from bakeoff.connection import ConnectionCheckFailed, handle_check, run_handshake


def response(*, output=(), text="", status="completed"):
    return SimpleNamespace(
        output=list(output), output_text=text, status=status,
        usage=SimpleNamespace(input_tokens=12, output_tokens=8),
    )


def call(**overrides):
    values = {"type": "function_call", "name": "connection_check",
              "arguments": '{"message":"hello"}', "call_id": "test-call"}
    return SimpleNamespace(**(values | overrides))


def test_dotenv_loads_independently_of_working_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(credentials, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=offline-test-secret\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    result = credentials.load_credentials()
    assert result.key == "offline-test-secret"
    assert result.source == "project .env file"
    assert "offline-test-secret" not in repr(result)
    assert "OPENAI_API_KEY" not in __import__("os").environ


def test_exported_key_takes_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(credentials, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=file-test-secret\n")
    monkeypatch.setenv("OPENAI_API_KEY", "environment-test-secret")
    result = credentials.load_credentials()
    assert result.key == "environment-test-secret"
    assert result.source == "process environment"


def test_placeholder_is_not_a_credential(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "replace_with_your_openai_api_key")
    with pytest.raises(ValueError, match="placeholder"):
        credentials.load_credentials()


def test_tool_round_trip_preserves_context_and_links_result():
    reasoning = SimpleNamespace(type="reasoning", encrypted_content="opaque-test-context")
    client = Mock()
    client.responses.create.side_effect = [
        response(output=[reasoning, call()]), response(text="Connection confirmed."),
    ]
    result = run_handshake(client)
    assert result["input_tokens"] == 24
    assert result["output_tokens"] == 16
    assert client.responses.create.call_count == 2
    second = client.responses.create.call_args.kwargs
    assert reasoning in second["input"]
    assert second["input"][-1]["call_id"] == "test-call"
    assert second["input"][-1]["type"] == "function_call_output"
    assert second["tool_choice"] == "none"


@pytest.mark.parametrize("bad_call", [
    call(name="write_file"), call(arguments="not-json"),
    call(arguments='{"message":"hello","path":"unexpected"}'),
])
def test_only_the_harmless_action_is_accepted(bad_call):
    with pytest.raises(ConnectionCheckFailed):
        handle_check(bad_call)


@pytest.mark.parametrize("first", [
    response(status="incomplete"), response(), response(output=[call(), call()]),
])
def test_bad_first_response_never_triggers_a_second_paid_request(first):
    client = Mock()
    client.responses.create.return_value = first
    with pytest.raises(ConnectionCheckFailed):
        run_handshake(client)
    assert client.responses.create.call_count == 1
