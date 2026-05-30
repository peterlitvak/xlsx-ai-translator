# Project Docker Containerization Plan

## Goal

Create a Docker deployment path for the Streamlit web UI so the translator can run on a different Docker-capable host and
be reachable from the local in-house network.

The containerized service should:

- Serve the existing Streamlit UI on port `8501`.
- Bind Streamlit inside the container to `0.0.0.0` so Docker port publishing can expose it through the host.
- Allow Streamlit uploads up to 500 MB.
- Use `uv.lock` for reproducible dependency installation.
- Keep `OPENAI_API_KEY` and any other secrets outside the image.
- Store uploaded files, generated outputs, and temporary binaries on a host-mounted work directory instead of the
  container filesystem.
- Clean staged result artifacts after the user requests the download.
- Run the container with at least one vCPU and at least 2 GB of RAM allocated.
- Keep Streamlit entry-point code focused on UI composition; helper logic belongs in service or utility modules.
- Keep project DTO-style objects as Pydantic models under `src/models/`, with one model per file.
- Keep project enums under `src/enums/`.
- Support deployment to the remote LAN Docker host over SSH using connection details from the local `.env` file.
- Optionally install Docker on the remote host when it is missing.
- Avoid changing CLI, UI, translation, workbook, or test behavior.

Official references checked:

- uv Docker integration and locked project sync: https://docs.astral.sh/uv/guides/integration/docker/
- Docker port publishing and LAN exposure behavior: https://docs.docker.com/engine/network/port-publishing/
- Dockerfile healthcheck behavior: https://docs.docker.com/reference/dockerfile/
- Docker Engine installation procedures: https://docs.docker.com/engine/install/

## Decisions

- Do not add `docker-compose.yml` for the initial Docker deployment.
- Use `Dockerfile`, `.dockerignore`, direct `docker run --restart unless-stopped`, and an optional remote SSH deployment
  helper script.
- Add `scripts/deploy_docker_remote.sh` for one-command deployment to the configured remote LAN Docker host.

## Current State

- The project is uv-managed with `pyproject.toml`, `uv.lock`, and `.python-version`.
- The Streamlit app runs locally with:

```bash
uv run streamlit run src/app/streamlit_app.py
```

- The UI depends on `OPENAI_API_KEY` at runtime.
- The local `.env` file contains deployment connection settings for the remote LAN host:
  - `DEPLOY_HOST_IP`
  - `DEPLOY_HOST_USER`
  - `DEPLOY_HOST_PWD`
  - `OPENAI_API_KEY`
- The UI processes uploaded `.xlsx` and `.zip` files and returns downloadable results. It does not currently require
  persistent application storage.
- The app has no built-in authentication or authorization layer.

## Target Docker Files

Add these top-level files:

```text
Dockerfile
.dockerignore
.streamlit/config.toml
src/enums/
src/models/
```

Add this remote deployment helper:

```text
scripts/deploy_docker_remote.sh
```

Update:

```text
README.md
src/app/streamlit_app.py
src/services/download_artifacts.py
src/services/upload_estimator.py
docs/impl/project-docker-containerization-impl.md
```

## Recommended Runtime Model

Build a production-oriented image for the Streamlit UI:

- Base image: Python `3.11` slim image, matching `.python-version`.
- uv installation: copy a pinned uv binary from the official uv image.
- Dependency install: `uv sync --locked --no-dev --no-editable`.
- Runtime command: run Streamlit from the installed virtual environment.
- Port: `8501/tcp`.
- Max upload size: `500` MB.
- Healthcheck: HTTP check against Streamlit's health endpoint on localhost.
- User: non-root application user.
- Secrets: supplied with `--env OPENAI_API_KEY=...` or `--env-file .env`.
- Remote deployment secrets: read from local `.env` and never copied into the Docker image.
- Work storage: mount a host directory at `/work`; set `TRANSLATION_WORK_DIR=/work` and `TMPDIR=/work/tmp`.
- Resource defaults: run with `--cpus 1 --memory 2g`, configurable upward for larger workloads.
- Local artifacts: keep `.local/`, `.venv/`, caches, local env files, and generated test/debug outputs out of the image.

Expected default command:

```bash
streamlit run src/app/streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true \
  --server.maxUploadSize=500 \
  --browser.gatherUsageStats=false
```

## Deployment Commands

Build on the target machine:

```bash
docker build -t xlsx-llm-translator:local .
```

Run in the foreground for local smoke testing:

```bash
mkdir -p .local/docker-work
chmod 1777 .local/docker-work
docker run --rm \
  --name xlsx-llm-translator \
  --cpus 1 \
  --memory 2g \
  --env OPENAI_API_KEY="$OPENAI_API_KEY" \
  --volume "$PWD/.local/docker-work:/work" \
  --publish 8501:8501 \
  xlsx-llm-translator:local
```

Run as a long-lived local-network service:

```bash
mkdir -p .local/docker-work
chmod 1777 .local/docker-work
docker run -d \
  --name xlsx-llm-translator \
  --restart unless-stopped \
  --cpus 1 \
  --memory 2g \
  --env-file .env \
  --volume "$PWD/.local/docker-work:/work" \
  --publish 8501:8501 \
  xlsx-llm-translator:local
```

Run bound to one LAN address when the host has multiple interfaces:

```bash
mkdir -p .local/docker-work
chmod 1777 .local/docker-work
docker run -d \
  --name xlsx-llm-translator \
  --restart unless-stopped \
  --cpus 1 \
  --memory 2g \
  --env-file .env \
  --volume "$PWD/.local/docker-work:/work" \
  --publish 192.168.1.50:8501:8501 \
  xlsx-llm-translator:local
```

Example `.env` file for the Docker host:

```bash
OPENAI_API_KEY=sk-...
```

Package for transfer to another Docker host without a registry:

```bash
docker save xlsx-llm-translator:local -o .local/xlsx-llm-translator.tar
```

Load on the destination host:

```bash
docker load -i xlsx-llm-translator.tar
```

Then run the same `docker run` command on the destination host.

## Remote LAN Host Deployment

Preferred deployment flow for the known remote LAN host:

1. Build the image locally.
2. Save the image tarball under `.local/`.
3. Copy the tarball to the remote host with `scp`.
4. Create a runtime env file on the remote host that contains only container runtime values such as `OPENAI_API_KEY`.
5. SSH to the remote host.
6. Load the image with `docker load`.
7. Stop and replace the existing container.
8. Run the container with `--restart unless-stopped`, `--cpus 1`, `--memory 2g`, and a host work directory mounted to
   `/work`.
9. Verify the service from this machine and from another trusted LAN client.

The local `.env` deployment variables should be used only by local deployment tooling:

| Variable | Purpose | Secret Handling |
| --- | --- | --- |
| `DEPLOY_HOST_IP` | SSH target and LAN URL host | Not a secret, but avoid hardcoding in docs. |
| `DEPLOY_HOST_USER` | SSH username | Treat as deployment configuration. |
| `DEPLOY_HOST_PWD` | SSH password when key-based auth is not available | Secret; do not echo, pass on the command line, commit, or copy into the container. |
| `OPENAI_API_KEY` | Runtime API key for the Streamlit service | Secret; copy only into the remote runtime env file with restricted permissions. |
| `INSTALL_DOCKER_IF_MISSING` | Optional opt-in for remote Docker installation | Defaults to `false`; Linux requires passwordless `sudo`; macOS installs Docker Desktop with the configured admin password flow. |
| `DOCKER_CPUS` | Optional container CPU allocation | Defaults to `1`; increase for larger concurrent workloads. |
| `DOCKER_MEMORY` | Optional container memory allocation | Defaults to `2g`; increase for larger uploads or archives. |
| `REMOTE_WORK_DIR` | Optional host work directory for mounted binaries | Defaults to `/tmp/xlsx-llm-translator/work`. |

Manual command shape:

```bash
docker build -t xlsx-llm-translator:local .
docker save xlsx-llm-translator:local -o .local/xlsx-llm-translator.tar
scp .local/xlsx-llm-translator.tar "$DEPLOY_HOST_USER@$DEPLOY_HOST_IP:/tmp/xlsx-llm-translator.tar"
ssh "$DEPLOY_HOST_USER@$DEPLOY_HOST_IP" "docker load -i /tmp/xlsx-llm-translator.tar"
```

Remote run command shape:

```bash
docker rm -f xlsx-llm-translator || true
docker run -d \
  --name xlsx-llm-translator \
  --restart unless-stopped \
  --cpus 1 \
  --memory 2g \
  --env-file /tmp/xlsx-llm-translator/.env \
  --volume /tmp/xlsx-llm-translator/work:/work \
  --publish 8501:8501 \
  xlsx-llm-translator:local
```

For a deployment helper script, prefer regular `ssh` and `scp` so existing SSH keys or interactive password prompts work.
If the implementation uses `DEPLOY_HOST_PWD` for non-interactive password auth, prefer `SSHPASS="$DEPLOY_HOST_PWD"
sshpass -e ...` or an `expect` environment variable over passing the password as a command-line argument. Do not log
shell commands with expanded secrets. If the deployment helper installs Docker, it should be opt-in. Linux hosts use
Docker's convenience script; macOS hosts require Docker Desktop because Docker Engine does not run natively on macOS.

## Network And Security Notes

- Publishing `8501:8501` exposes the service on all host interfaces by default. This is appropriate only when the Docker
  host is already restricted to the intended local network.
- Prefer binding to a specific private LAN IP when the host also has public, VPN, guest, or untrusted interfaces.
- Do not publish the service directly to the internet without an authentication layer, TLS termination, and rate limiting.
- Do not bake `OPENAI_API_KEY` into the image with `ARG`, `ENV`, or committed files.
- Do not copy `DEPLOY_HOST_PWD` to the remote host or into the container runtime env file.
- Mount `/work` to a host directory so large uploads and generated outputs are not stored in the container filesystem.
- Clean staged translated artifacts after the user requests a download; Streamlit does not expose a lower-level callback
  that proves the browser completed writing the file.
- Use host firewall rules to restrict access to trusted subnets when the network boundary is not already controlled.

## Dockerfile Shape

Recommended high-level Dockerfile flow:

1. Start from a Python 3.11 slim image.
2. Copy pinned `uv` and `uvx` binaries into the image.
3. Set `WORKDIR /app`.
4. Copy `pyproject.toml` and `uv.lock` first for dependency caching.
5. Run `uv sync --locked --no-dev --no-install-project`.
6. Copy source, docs needed at runtime if any, and project metadata.
7. Run `uv sync --locked --no-dev --no-editable`.
8. Create and use a non-root application user.
9. Create `/work/tmp` and expose `/work` as the mounted work directory.
10. Expose `8501`.
11. Add a healthcheck.
12. Start Streamlit with `server.address=0.0.0.0` and `server.maxUploadSize=500`.

## `.dockerignore` Expectations

The Docker build context should exclude:

```text
.git/
.idea/
.local/
.venv/
.env
.env.*
!.env.example
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.mypy_cache/
.pyright/
resources/test_fixtures/*report*.csv
```

Keep committed fixtures available unless the final image size needs to be reduced and tests are not run inside the image.

## README Updates

Add a Docker section that includes:

- Build command.
- Run command for LAN access.
- Long-running service command with `--restart unless-stopped`.
- Resource settings for at least one vCPU and 2 GB RAM.
- Host work directory volume mapping to `/work`.
- Run command with an env file.
- Image save/load workflow.
- Remote LAN deployment workflow using `.env` variable names without exposing values.
- How to reach the service from another machine: `http://<docker-host-lan-ip>:8501`.
- A warning that the service has no built-in auth and should stay on trusted networks.

## Validation Strategy

After Docker files are implemented:

```bash
docker build -t xlsx-llm-translator:local .
mkdir -p .local/docker-work
chmod 1777 .local/docker-work
docker run --rm --name xlsx-llm-translator-smoke --cpus 1 --memory 2g --env OPENAI_API_KEY="$OPENAI_API_KEY" --volume "$PWD/.local/docker-work:/work" --publish 8501:8501 xlsx-llm-translator:local
curl -f http://127.0.0.1:8501/_stcore/health
bash -n scripts/deploy_docker_remote.sh
ssh "$DEPLOY_HOST_USER@$DEPLOY_HOST_IP" "docker --version"
uv run python -m unittest discover -s tests
uv run pyright
uv run black src tests
```

For LAN validation, open this URL from another machine on the same trusted network:

```text
http://<docker-host-lan-ip>:8501
```

## Open Decisions

- Whether the container should include committed test fixtures.

Recommended initial behavior: keep fixtures in the image for simple smoke testing unless image size becomes a concern.

- Whether to add authentication before LAN deployment.

Recommended initial behavior: keep this Docker task scoped to packaging, but do not deploy beyond a trusted in-house
network without adding an auth layer or a trusted reverse proxy.
