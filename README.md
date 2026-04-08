# Doc Sweeper Environment

A virtual file system and text-editing environment for OpenEnv. This environment tasks autonomous LLM agents with acting as automated documentation engineers, requiring them to navigate a directory tree, read files, and apply precise string manipulations to complete complex refactoring tasks.

## Overview

The Doc Sweeper environment provides a sandboxed, in-memory file system where agents can interact with dummy codebases and documentation. It evaluates an agent's ability to retain context, plan multi-step operations, and use tools correctly.

### Features

* **Virtual File System**: In-memory directory tree with nested files.
* **Strict Tooling**: Requires agents to explicitly `open` files before applying `edit` commands.
* **Granular Feedback**: Provides immediate terminal feedback and linter issues upon illegal actions or formatting errors.
* **Three Distinct Scenarios**: Evaluates different logic flows (global search/replace, YAML refactoring, path resolution).

### Task Rules

The environment supports three primary tasks:

* `version_bump`: The agent must find all outdated version numbers (e.g., `v1.0.0` or `v1.00`) across all files and update them to `v2.0.0`.
* `config_migration`: The agent must open docker-compose files, update the version to `3.8`, and migrate `links` keys to `networks`.
* `broken_links`: The agent must find broken relative markdown links and edit them to point to correct file paths.

---

## Quick Start

### Running the Baseline Inference (Recommended)

The easiest way to test the environment is using the provided Chain-of-Thought agent script.

```bash
# Export your required credentials
export HF_TOKEN="your_api_key_here"
export API_BASE_URL="[https://api.openai.com/v1](https://api.openai.com/v1)"
export MODEL_NAME="gpt-4o-mini"
```

# Run the inference script across all tasks
python inference.py

## Using Local Server
You can host the environment locally to manually test the API endpoints.

```bash
# Install dependencies
pip install -r requirements.txt
```


# Run server
```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```
## Actions

The action space is defined by the `DocAction` schema. The agent must provide a single JSON object with a `tool_name` and the corresponding required fields:

* **`open`**: Opens a file. Requires the `path` parameter.
* **`edit`**: Replaces text in the currently active file. Requires exact string matching via `old_str` and `new_str`.
* **`grep`**: Searches the active file (or directory). Requires `search_query`.
* **`done`**: Signals that the task is complete.

## Observations

Each observation (`DocObservation`) returned by the environment includes:

* **`active_file`**: The file currently opened by the agent.
* **`terminal_feedback`**: Error messages, success logs, or system alerts resulting from the last action.
* **`directory_tree`**: A JSON representation of the current file system hierarchy.
* **`file_content`**: The textual content of the currently active file.
* **`issues_detected`**: A list of simulated linter errors (if the agent breaks a file's formatting).

## Configuration

### Reward Structure

The environment issues rewards based on the agent's efficiency and accuracy:

* **Valid Tool Usage**: `0.0` (Neutral, but advances the state).
* **Tool Misuse Penalty**: `-0.1` (e.g., trying to edit without opening a file, or providing a bad file path).
* **Task Completion**: `1.0` (Awarded only when `done` is called and all objective checks pass).
* **Early/Failed Completion**: `-1.0` (Calling `done` before fixing all required strings).

## Building and Deployment

### Build Docker Image

From the repository root:

# Build the environment image

```bash
docker build -t doc-sweeper-env:latest .
```

The Dockerfile uses pip install with requirements.txt for maximum compatibility with Hugging Face Spaces.

# Run the container locally

```bash
docker run -p 8000:8000 doc-sweeper-env:latest
```
The FastAPI OpenEnv endpoints will be available at `http://localhost:8000/reset` and `http://localhost:8000/step`.

---

## Dependencies

The Doc Sweeper environment requires:

* **`fastapi` & `uvicorn`**: For serving the OpenEnv endpoints.
* **`pydantic`**: For strict action and observation schema validation.
* **`openai` / `groq`**: For the baseline LLM inference script.

These are automatically installed when using Docker or installing via `pip install -r requirements.txt`.

---

## Example Evaluation Log Output

When running `inference.py`, the agent emits strictly formatted logs for the automated graders:

```text
[START] task=version_bump model=gpt-4o-mini
[STEP] step=1 action=open reward=0.00 done=False thought="Opening setup.md to check for versions."
[STEP] step=2 action=edit reward=0.00 done=False thought="Replacing v1.0.0 with v2.0.0."
[STEP] step=3 action=done reward=1.00 done=True thought="All files have been checked."
[END] task=version_bump score=1.00 total_steps=3 runtime_seconds=4.2