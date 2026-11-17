# Jiatrix

Terminal agent powered by your offline Ollama. Run it in any folder; it can list, search and read files there, and write files or run shell commands only after you approve each one.

## Files

| File | Purpose |
|---|---|
| `agent.py` | the agent |
| `Dockerfile` | image (python + ollama client) |
| `compose-service.yml` | service block for your `docker-compose.yml` |
| `setup.sh` | one-shot installer |

## Install

```bash
cd jiatrix            # this folder
./setup.sh            # assumes ~/Documents/SLM
./setup.sh /other/path/to/SLM
exec zsh              # reload shell so aliases load
```

`setup.sh` will:
1. copy `agent.py` and `Dockerfile` to `SLM/jiatrix/`
2. insert the service into `docker-compose.yml` (backup at `docker-compose.yml.bak`)
3. build the image
4. pull `qwen2.5:7b` if the `olama` container is running
5. add the `jiatrix` and `jiatrix3` aliases to `~/.zshrc` / `~/.bashrc`

### Manual install

1. `mkdir SLM/jiatrix` and copy `agent.py` and `Dockerfile` into it.
2. Paste `compose-service.yml` under `services:` in `docker-compose.yml`.
3. `docker compose build jiatrix`
4. `docker exec olama ollama pull qwen2.5:7b`
5. Add to `~/.zshrc`:
   ```bash
   alias jiatrix='JIATRIX_UID=$(id -u) JIATRIX_GID=$(id -g) JIATRIX_WORK="$PWD" docker compose -f ~/Documents/SLM/docker-compose.yml run --rm jiatrix'
   alias jiatrix3='JIATRIX_MODEL=qwen2.5:3b jiatrix'
   ```

## Use

```bash
cd ~/Documents/dollar-stock-system
jiatrix        # qwen2.5:7b
jiatrix3       # qwen2.5:3b, faster, weaker at multi-step
```

In the prompt: `/new` clears history, `ctrl-c` quits.

Examples:
- `where is the voucher expiry handled?`
- `read app/Exports/UsersExport.php and explain it`
- `create a README for this folder`

## Config (env vars)

| Variable | Default | Meaning |
|---|---|---|
| `JIATRIX_MODEL` | `qwen2.5:7b` | model to use |
| `AGENT_CTX` | `8192` | context size (bigger = more RAM) |
| `JIATRIX_WORK` | current folder | folder mounted at `/work` |

Example: `JIATRIX_MODEL=huihui_ai/qwen3.5-abliterated:9b jiatrix`. Check first that it handles tool calls.

## Safety

- File access is confined to the launch folder (path escapes are rejected).
- Every write and every shell command asks `y/N`.
- Skipped folders: `.git`, `node_modules`, `vendor`, `storage`, `__pycache__`, `.venv`.
- The `run` tool executes inside the container, so there is no `php`, `composer` or `artisan`.
- Jiatrix doesn't start with `docker compose up` (it uses the `agent` profile).

## CPU tips

- Prompt processing runs about 16 tok/s on your hardware. Ask it to search before reading files.
- Use `/new` often; history is resent on every step.
- One model at a time: Ollama keeps models in RAM for the keep-alive period.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ollama error: ... connection refused` | `docker ps`; start it with `docker compose up -d ollama` |
| `model not found` | `docker exec olama ollama pull qwen2.5:7b` |
| Files created as root | the alias passes your UID/GID; if you run `docker compose run` by hand, set `JIATRIX_UID` and `JIATRIX_GID` |
| Hangs with no output | the model is processing; check `docker logs --tail 20 olama` |
| Wrong or no tool calls | use the 7b, or `/new` to drop a confused history |
| Alias not found | `exec zsh`, or `source ~/.zshrc` |

## Security fixes for your compose file

1. The Telegram bot token in the `leadgen` service is in plaintext. Revoke it with `/revoke` in @BotFather, then load the new one from a `.env` file listed in `.gitignore`.
2. Change `"11434:11434"` to `"127.0.0.1:11434:11434"` so Ollama isn't exposed to your network. The Ollama API has no authentication.
