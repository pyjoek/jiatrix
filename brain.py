from openai import OpenAI
import os
import json

client = OpenAI(
    api_key="PUT YOUR API HERE FROM GROQ WEBSITE FREE ACCOUNT",
    base_url="https://api.groq.com/openai/v1"
)

# --- Safety boundary -------------------------------------------------------
# Jiatrix is only allowed to touch files inside this folder (and subfolders).
# Change it to wherever your project lives. Keeping a hard boundary means a
# bad model response (or a bad prompt from you) can't walk off into the rest
# of your filesystem.
ALLOWED_DIR = os.path.abspath(os.path.expanduser("~/jiatrix_workspace"))
os.makedirs(ALLOWED_DIR, exist_ok=True)

MAX_READ_BYTES = 20_000  # don't dump huge files into the context window


def _resolve(path: str) -> str:
    """Turn a user-supplied relative path into an absolute one, and make
    sure it's actually inside ALLOWED_DIR. Raises ValueError if not."""
    candidate = os.path.abspath(os.path.join(ALLOWED_DIR, path))
    if not candidate.startswith(ALLOWED_DIR):
        raise ValueError(f"'{path}' is outside the allowed workspace")
    return candidate


# --- Tool implementations ---------------------------------------------------

def tool_list_dir(path: str = ".") -> str:
    target = _resolve(path)
    if not os.path.isdir(target):
        return f"error: '{path}' is not a directory"
    entries = []
    for name in sorted(os.listdir(target)):
        full = os.path.join(target, name)
        kind = "dir" if os.path.isdir(full) else "file"
        entries.append(f"{kind}: {name}")
    return "\n".join(entries) if entries else "(empty directory)"


def tool_read_file(path: str) -> str:
    target = _resolve(path)
    if not os.path.isfile(target):
        return f"error: '{path}' is not a file"
    with open(target, "r", errors="replace") as f:
        content = f.read(MAX_READ_BYTES + 1)
    if len(content) > MAX_READ_BYTES:
        content = content[:MAX_READ_BYTES] + "\n...[truncated]"
    return content


def tool_write_file(path: str, content: str) -> str:
    target = _resolve(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w") as f:
        f.write(content)
    return f"wrote {len(content)} bytes to {path}"


TOOL_IMPLS = {
    "list_dir": tool_list_dir,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
}

# Schema Groq/OpenAI need to know these tools exist and what args they take.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and folders inside a directory of the workspace, so you can see what's there before reading anything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path relative to the workspace root. Use '.' for the top level.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the text contents of a file in the workspace, e.g. to inspect a traceback, a log, or source code while debugging an error.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file, relative to the workspace root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file in the workspace, e.g. to save a fix or a patch. Only use this when the user has clearly asked for a file to be written.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write, relative to the workspace root."},
                    "content": {"type": "string", "description": "Full contents to write to the file."},
                },
                "required": ["path", "content"],
            },
        },
    },
]

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are Jiatrix, a terminal assistant. You can list, read, and write "
        f"files inside the sandboxed workspace at {ALLOWED_DIR}. Use list_dir "
        "and read_file to look at logs, tracebacks, or source files whenever "
        "that would help diagnose an error the user describes. Only use "
        "write_file when the user explicitly wants a file created or changed, "
        "and tell them what you wrote."
    ),
}

chat_history = [SYSTEM_PROMPT]


def ask(user, confirm_writes=True, verbose=False):
    global chat_history

    chat_history.append({"role": "user", "content": user})

    while True:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=chat_history,
            tools=TOOLS,
            stream=False,  # always wait for the complete response, never stream partial tokens
        )
        msg = response.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if not tool_calls:
            reply = msg.content
            chat_history.append({"role": "assistant", "content": reply})
            # Only the finished, full answer gets shown - nothing partial.
            print(f"[x] Jiatrix: {reply}")
            return

        # The model wants to call one or more tools. Record its request,
        # run each tool, and feed the results back before asking again.
        chat_history.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            if name == "write_file" and confirm_writes:
                path = args.get("path", "?")
                print(f"[!] Jiatrix wants to write to '{path}'. Allow? (y/n)")
                if input("[?] ").strip().lower() != "y":
                    result = "write denied by user"
                    chat_history.append(
                        {"role": "tool", "tool_call_id": tc.id, "content": result}
                    )
                    continue

            impl = TOOL_IMPLS.get(name)
            if impl is None:
                result = f"error: unknown tool '{name}'"
            else:
                try:
                    result = impl(**args)
                except Exception as e:
                    result = f"error running {name}: {e}"

            if verbose:
                # Opt-in only: shows each tool step as it happens. Off by
                # default so you never see half-formed progress, just the
                # final reply once everything is done.
                print(f"[~] {name}({args}) -> {result[:200]}")
            chat_history.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )
        # loop again silently so the model can use the tool results in its
        # reply - nothing is printed to the user until a final, tool-free
        # answer comes back above.


def clear_memory():
    global chat_history
    chat_history = [SYSTEM_PROMPT]
