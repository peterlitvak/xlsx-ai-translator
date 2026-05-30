# Project Docker Containerization Implementation Notes

## Scope

Add Docker packaging for the Streamlit UI so the service can run on another Docker-capable host and be available on the
local in-house network.

This work should not change translation logic, CLI behavior, workbook handling, Streamlit UI workflow, model selection,
or test fixture contents.

## Proposed File Changes

| Current File | Target Change | Notes |
| --- | --- | --- |
| `Dockerfile` | Add | Build a Python 3.11 slim runtime image with locked uv dependencies and the Streamlit UI as the default command. |
| `.dockerignore` | Add | Keep local virtualenvs, git metadata, debug artifacts, caches, and generated reports out of image builds. |
| `.streamlit/config.toml` | Add | Configure Streamlit to accept uploads up to 500 MB for local and Docker runs. |
| `src/enums/` | Add | Keep project enums for supported languages, model options, and upload types outside app code. |
| `src/models/` | Add | Keep Pydantic DTO-style models outside app and service implementation modules, with one model per file. |
| `src/app/streamlit_app.py` | Update | Stage translated download artifacts under `TRANSLATION_WORK_DIR` and clean them up when the download button is clicked. |
| `src/services/download_artifacts.py` | Add | Own staged download artifact creation and cleanup. |
| `src/services/upload_estimator.py` | Add | Own uploaded XLSX/ZIP estimation helper behavior. |
| `scripts/deploy_docker_remote.sh` | Add | Automate build, image transfer, remote load, container replacement, and health validation over SSH. |
| `README.md` | Update | Add Docker build, run, LAN access, env var, save/load, and security notes. |
| `docs/plan/project-docker-containerization-plan.md` | Add | Captures target behavior, deployment commands, and decisions. |
| `docs/impl/project-docker-containerization-impl.md` | Add | Tracks implementation sequence and validation status. |

## Proposed Dockerfile Behavior

- Use Python `3.11` to match `.python-version`.
- Install uv from a pinned official uv container image tag.
- Install runtime dependencies with `uv sync --locked --no-dev`.
- Prefer non-editable project installation in the image.
- Run as a non-root application user.
- Expose port `8501`.
- Configure Streamlit upload size to 500 MB.
- Use `/work` as the mounted work directory for uploads, generated outputs, and temporary binaries.
- Use `TMPDIR=/work/tmp` so Python temporary files are created on the mounted host volume.
- Start Streamlit with:

```bash
streamlit run src/app/streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true \
  --server.maxUploadSize=500 \
  --browser.gatherUsageStats=false
```

## Runtime Configuration

Required environment variables:

| Variable | Required | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Must be supplied at `docker run` runtime. Do not bake into the image. |
| `DEPLOY_HOST_IP` | For remote deployment | SSH target and LAN URL host. Do not hardcode the value in docs. |
| `DEPLOY_HOST_USER` | For remote deployment | SSH username for the Docker host. |
| `DEPLOY_HOST_PWD` | For remote deployment when key auth is unavailable | Secret. Use only locally, never in the container env file. |
| `INSTALL_DOCKER_IF_MISSING` | Optional | Defaults to `false`; when `true`, attempts remote Docker installation and requires passwordless `sudo`. |
| `DOCKER_CPUS` | Optional | Defaults to `1`; pass a larger value for heavier workloads. |
| `DOCKER_MEMORY` | Optional | Defaults to `2g`; pass a larger value for larger upload/archive workloads. |
| `REMOTE_WORK_DIR` | Optional | Host directory mounted to `/work`; defaults to `/tmp/xlsx-llm-translator/work`. |
| `TRANSLATION_WORK_DIR` | Container runtime | Set to `/work` in the image. |

Expected published port:

| Host Port | Container Port | Notes |
| --- | --- | --- |
| `8501` | `8501` | Publish to all interfaces only on trusted LAN hosts. Prefer a specific LAN IP when needed. |

Expected resource and volume configuration:

| Setting | Default | Notes |
| --- | --- | --- |
| CPU | `--cpus 1` | Minimum requested deployment setting; can be increased with `DOCKER_CPUS`. |
| Memory | `--memory 2g` | Minimum requested deployment setting; can be increased with `DOCKER_MEMORY`. |
| Work volume | `<host-work-dir>:/work` | Required so large uploads and generated binaries are not kept in the container filesystem. |

## Implementation Steps

1. Add `.dockerignore`.
   - Exclude `.venv/`, `.local/`, `.git/`, IDE files, Python caches, egg-info, and generated reports.
   - Keep committed source, docs, `resources/test_fixtures/`, `pyproject.toml`, and `uv.lock` available to the build.

2. Add `Dockerfile`.
   - Use a Python 3.11 slim base.
   - Copy pinned uv binaries from the official uv image.
   - Install dependencies from `uv.lock` before copying the full source when possible.
   - Sync without dev dependencies for runtime image size and attack surface.
   - Add a non-root app user.
   - Configure `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=500`.
   - Configure `TRANSLATION_WORK_DIR=/work` and `TMPDIR=/work/tmp`.
   - Declare `/work` as the mounted work volume.
   - Add a healthcheck for Streamlit.
   - Set the default command to run the Streamlit app on `0.0.0.0:8501`.

3. Update Streamlit runtime storage.
   - Add `.streamlit/config.toml` with `server.maxUploadSize = 500`.
   - Stage translated result downloads under `TRANSLATION_WORK_DIR`.
   - Remove the previous staged artifact before a new translation starts.
   - Remove the staged artifact when the download button is clicked.
   - Move upload-estimation and download-artifact helpers out of `src/app/streamlit_app.py`.
   - Move DTO-style objects into Pydantic models under `src/models/`, with one model per file.
   - Move constrained UI option sets into enums under `src/enums/`.

4. Do not add `docker-compose.yml`.
   - The service is a single container with one published port and no database, sidecar, or persistent volume.
   - Use direct `docker run --restart unless-stopped` commands for the initial remote LAN deployment.

5. Add `scripts/deploy_docker_remote.sh`.
   - Source local `.env` for `DEPLOY_HOST_IP`, `DEPLOY_HOST_USER`, `DEPLOY_HOST_PWD`, and `OPENAI_API_KEY`.
   - Build and save the Docker image under `.local/`.
   - Copy the image tarball to the remote host with `scp`.
   - Create a remote runtime env file containing only `OPENAI_API_KEY`.
   - Set remote env file permissions to `600`.
   - Load the image on the remote host.
   - Stop and replace the existing container.
   - Run the container with `--restart unless-stopped`, `--cpus`, `--memory`, and the host work directory mounted to
     `/work`.
   - Optionally install Docker when `INSTALL_DOCKER_IF_MISSING=true`.
   - Use `sshpass` when available, or `expect` when `sshpass` is not installed, for non-interactive password-based SSH.
   - Support macOS remote hosts by installing Docker Desktop from Docker's official DMG when Docker is missing.
   - Validate the remote health endpoint.
   - Mask secrets in logs and never pass passwords as visible command-line arguments.

6. Update `README.md`.
   - Add build and run commands.
   - Add `.env` example.
   - Add long-running `docker run -d --restart unless-stopped` service command.
   - Add 500 MB upload limit, resource settings, and external work volume mapping.
   - Add image save/load handoff commands.
   - Add remote LAN deployment instructions using `.env` variable names without values.
   - Add LAN URL format.
   - Add security note about trusted-network-only exposure.

7. Validate locally.
   - Build the image.
   - Run the container with `OPENAI_API_KEY`.
   - Check the health endpoint.
   - Open the UI from the Docker host.
   - Confirm uploads and translated result staging use the mounted work directory.
   - Run existing uv tests outside the container to ensure source behavior stayed unchanged.

8. Validate remote SSH deployment.
   - Confirm SSH connectivity to `DEPLOY_HOST_USER@DEPLOY_HOST_IP`.
   - Confirm Docker is installed and available to that remote user.
   - If Docker is missing, rerun with `INSTALL_DOCKER_IF_MISSING=true` only when passwordless `sudo` is acceptable.
   - Transfer and load the image on the remote host.
   - Start the service with the remote runtime env file.
   - Check `http://DEPLOY_HOST_IP:8501/_stcore/health` from this machine.

9. Validate LAN access.
   - Publish the port on the intended host interface.
   - Access `http://<docker-host-lan-ip>:8501` from another trusted network machine.
   - Confirm host firewall rules allow only intended clients or subnets.

## Validation Commands

Use these commands after implementation:

```bash
docker build -t xlsx-llm-translator:local .
mkdir -p .local/docker-work
chmod 1777 .local/docker-work
docker run --rm --name xlsx-llm-translator-smoke --cpus 1 --memory 2g --env OPENAI_API_KEY="$OPENAI_API_KEY" --volume "$PWD/.local/docker-work:/work" --publish 8501:8501 xlsx-llm-translator:local
curl -f http://127.0.0.1:8501/_stcore/health
bash -n scripts/deploy_docker_remote.sh
ssh "$DEPLOY_HOST_USER@$DEPLOY_HOST_IP" "docker --version"
uv run black src tests
uv run pyright
uv run python -m unittest discover -s tests
```

Run this packaging check before handing the image to another host:

```bash
docker save xlsx-llm-translator:local -o .local/xlsx-llm-translator.tar
docker load -i .local/xlsx-llm-translator.tar
```

## Validation Results

M7 local Docker validation completed:

- Exposed Docker Desktop CLI to the terminal by linking Docker Desktop binaries into `~/.local/bin`, which is already on
  the shell `PATH`.
- Confirmed Docker Desktop CLI and daemon availability with Docker `29.5.2` on the `desktop-linux` context.
- Built `xlsx-llm-translator:local` successfully.
- Created `.local/docker-work` and mounted it to `/work` for the smoke container.
- Ran the smoke container with `--cpus 1`, `--memory 2g`, `OPENAI_API_KEY`, `--volume "$PWD/.local/docker-work:/work"`,
  and `--publish 8501:8501`.
- Confirmed `http://127.0.0.1:8501/_stcore/health` returns `ok`.
- Confirmed the Docker-served Streamlit page renders in browser automation with the `XLSX LLM Translator` title, upload
  control, `500MB per file` upload hint, and default Japanese-to-English GPT-4o selections.

Local Docker Desktop note: `docker ps` and `docker stop` can see the smoke container, but `docker inspect`, `docker exec`,
and `docker logs` currently fail to resolve the same container on this machine. M7 validation therefore used the build
output, `docker image ls`, `docker ps`, HTTP health check, and browser-rendered UI verification as the authoritative
local smoke evidence.

Dockerized E2E translation validation completed:

- Started `xlsx-llm-translator:local` as `xlsx-llm-translator-e2e` with `--cpus 1`, `--memory 2g`, `OPENAI_API_KEY`,
  `--volume "$PWD/.local/docker-work:/work"`, and `--publish 8501:8501`.
- Confirmed `http://127.0.0.1:8501/_stcore/health` returns `ok`.
- Used browser automation against the Docker-served Streamlit UI to upload `resources/test_fixtures/sample.xlsx`, execute
  translation, click the download button, and save `.local/docker-e2e-downloads/single_sample_en.xlsx`.
- Used browser automation against the Docker-served Streamlit UI to upload `resources/test_fixtures/sample.zip`, execute
  translation, click the download button, and save `.local/docker-e2e-downloads/archive_sample_en.zip`.
- Verified the single-workbook download opens with `openpyxl` and contains translated visible-sheet values `Hello` and
  `World`.
- Verified the zip download is valid, contains `nested/sample_en.xlsx`, and the nested workbook opens with `openpyxl`
  with translated visible-sheet values `Hello` and `World`.
- Confirmed `.local/docker-work` was empty after the successful download clicks, which validates staged result cleanup
  through the mounted work volume for these E2E paths.

M8 remote SSH deployment validation completed:

- Confirmed password-based SSH access to the configured remote host from the local `.env` values.
- Confirmed key-based SSH was not available, `sshpass` was not installed locally, and `expect` was available.
- Updated `scripts/deploy_docker_remote.sh` so password-based SSH and SCP can use `expect` without passing passwords as
  command-line arguments.
- Updated the remote env-file write path so runtime env payloads are sent over the authenticated SSH session without
  logging stdin contents.
- Updated the deploy helper so remote SSH commands include common Docker Desktop CLI locations in `PATH`.
- Confirmed the configured remote host is macOS on Apple silicon with enough memory for the requested `--memory 2g`
  container setting.
- Confirmed Docker was initially missing on the remote host.
- Ran the deploy helper with `INSTALL_DOCKER_IF_MISSING=true`.
- Installed Docker Desktop on the remote macOS host from Docker's official Apple silicon DMG using the command-line
  installer.
- Built and saved `xlsx-llm-translator:local` locally, copied the image archive to the remote host, loaded it remotely,
  and replaced the remote `xlsx-llm-translator` container.
- Wrote the remote runtime env file at `/tmp/xlsx-llm-translator/.env` with mode `600`.
- Created the remote host work directory at `/tmp/xlsx-llm-translator/work` with mode `777`.
- Confirmed the remote container is healthy, publishes `8501:8501`, uses restart policy `unless-stopped`, applies
  `--cpus 1`, applies `--memory 2g`, and bind-mounts `/tmp/xlsx-llm-translator/work:/work`.
- Confirmed `http://<configured DEPLOY_HOST_IP>:8501/_stcore/health` returns `ok` from this machine.

M9 LAN deployment validation completed:

- Confirmed TCP connectivity from this workstation to the configured remote host on port `8501`.
- Confirmed `http://<configured DEPLOY_HOST_IP>:8501/_stcore/health` returns `ok` from this workstation.
- Used browser automation from this workstation to load `http://<configured DEPLOY_HOST_IP>:8501/` and confirmed the
  Docker-served Streamlit UI renders the `XLSX LLM Translator` title, upload control, `500MB per file` upload hint, and
  default Japanese-to-English GPT-4o selections.
- Confirmed the remote container is still healthy and publishes `0.0.0.0:8501->8501/tcp` and `[::]:8501->8501/tcp`.
- Confirmed the remote container keeps restart policy `unless-stopped`, `--cpus 1`, `--memory 2g`, and
  `/tmp/xlsx-llm-translator/work:/work`.
- Confirmed the remote macOS application firewall is disabled and block-all mode is disabled; access is therefore
  controlled by the trusted LAN boundary and any upstream network controls, not by a host application firewall rule.

## Rollback Plan

If Docker build or runtime validation fails:

- Remove or revert `Dockerfile`.
- Remove or revert `.dockerignore`.
- Remove or revert `scripts/deploy_docker_remote.sh` if it was added.
- Revert README Docker instructions.
- Keep the failure details in this implementation doc before reverting so the next attempt has concrete diagnostics.

## Implementation Milestones

Status key: ✅ done, 🟡 in progress, ⚪ not started, 🛑 blocked.

| Milestone | Status | Work Item | Notes |
| --- | --- | --- | --- |
| M1 | ✅ | Document Docker containerization plan and implementation notes | Captured in `docs/plan/project-docker-containerization-plan.md` and this file. |
| M2 | ✅ | Add `.dockerignore` | Excludes local env files, virtualenvs, git metadata, caches, egg-info, `.local/`, and generated reports from the Docker build context. |
| M3 | ✅ | Add Dockerfile and app architecture cleanup | Builds a Python 3.11 locked uv runtime image with a non-root app user, healthcheck, 500 MB upload limit, and `/work` volume; moved helpers, one-model-per-file Pydantic models, and enums to their proper packages. |
| M4 | ✅ | Decide on compose support | Do not add Compose initially; direct `docker run --restart unless-stopped` is enough for the single-container service. |
| M5 | ✅ | Add remote deployment helper | Added `scripts/deploy_docker_remote.sh` for one-command SSH deployment from local `.env`, optional remote Docker install, resource limits, and host work-volume mapping. |
| M6 | ✅ | Update README Docker instructions | Documented build, smoke run, long-running service run, remote SSH deploy, 500 MB uploads, resource settings, work volume, env, LAN access, save/load, and security notes. |
| M7 | ✅ | Validate Docker build and local smoke test | Built `xlsx-llm-translator:local`, ran the smoke container with `/work` mounted from `.local/docker-work`, checked Streamlit health, and verified the UI rendered from `http://127.0.0.1:8501`. |
| M8 | ✅ | Validate remote SSH deployment workflow | Installed Docker Desktop on the remote macOS host when Docker was missing, transferred and loaded the image, replaced the remote container, confirmed resource limits and `/work` bind mount, and verified the health endpoint. |
| M9 | ✅ | Validate LAN deployment workflow | Confirmed health and browser UI access from this workstation over the remote host LAN IP, verified port publishing and container settings, and checked remote macOS firewall state. |
