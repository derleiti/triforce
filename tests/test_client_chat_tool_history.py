from app.routes.client_chat import ChatMessage


def test_chat_message_preserves_native_tool_call_fields():
    tool_call = {
        "id": "call_abc",
        "type": "function",
        "function": {"name": "file_tree", "arguments": '{"path":"."}'},
    }
    assistant = ChatMessage(role="assistant", content="", tool_calls=[tool_call])
    tool = ChatMessage(role="tool", content="tree", tool_call_id="call_abc", name="file_tree")

    assistant_payload = assistant.model_dump(exclude_none=True)
    tool_payload = tool.model_dump(exclude_none=True)

    assert assistant_payload["tool_calls"] == [tool_call]
    assert tool_payload["tool_call_id"] == "call_abc"
    assert tool_payload["name"] == "file_tree"
    assert tool_payload["role"] == "tool"
