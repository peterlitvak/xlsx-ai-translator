#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"

IMAGE_NAME="${IMAGE_NAME:-xlsx-llm-translator}"
IMAGE_TAG="${IMAGE_TAG:-local}"
IMAGE_REF="$IMAGE_NAME:$IMAGE_TAG"
CONTAINER_NAME="${CONTAINER_NAME:-xlsx-llm-translator}"

HOST_PORT="${HOST_PORT:-8501}"
CONTAINER_PORT="${CONTAINER_PORT:-8501}"
HOST_BIND_IP="${HOST_BIND_IP:-}"
HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_DELAY_SECONDS="${HEALTH_DELAY_SECONDS:-2}"
DOCKER_CPUS="${DOCKER_CPUS:-1}"
DOCKER_MEMORY="${DOCKER_MEMORY:-2g}"
INSTALL_DOCKER_IF_MISSING="${INSTALL_DOCKER_IF_MISSING:-false}"
REMOTE_COMMAND_PATH="${REMOTE_COMMAND_PATH:-\$HOME/.local/bin:\$HOME/.docker/bin:/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:\$PATH}"

LOCAL_IMAGE_ARCHIVE="${LOCAL_IMAGE_ARCHIVE:-$PROJECT_ROOT/.local/xlsx-llm-translator.tar}"
REMOTE_IMAGE_ARCHIVE="${REMOTE_IMAGE_ARCHIVE:-/tmp/xlsx-llm-translator.tar}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/tmp/xlsx-llm-translator}"
REMOTE_ENV_FILE="$REMOTE_APP_DIR/.env"
REMOTE_WORK_DIR="${REMOTE_WORK_DIR:-/tmp/xlsx-llm-translator/work}"
CONTAINER_WORK_DIR="${CONTAINER_WORK_DIR:-/work}"
DEPLOY_HOST_TARGET=""

SSH_OPTIONS=(-o StrictHostKeyChecking=accept-new)

log() {
    printf '[deploy] %s\n' "$1"
}

fail() {
    printf '[deploy] ERROR: %s\n' "$1" >&2
    exit 1
}

trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

strip_matching_quotes() {
    local value="$1"
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
        value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
        value="${value:1:${#value}-2}"
    fi
    printf '%s' "$value"
}

load_dotenv() {
    [[ -f "$ENV_FILE" ]] || fail "Missing env file: $ENV_FILE"

    local line key value
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="$(trim "$line")"
        [[ -z "$line" || "$line" == \#* ]] && continue
        [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue

        key="${BASH_REMATCH[1]}"
        value="$(trim "${BASH_REMATCH[2]}")"
        value="$(strip_matching_quotes "$value")"
        export "$key=$value"
    done < "$ENV_FILE"
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Required command is not available: $1"
}

require_env() {
    local name="$1"
    [[ -n "${!name:-}" ]] || fail "Missing required environment variable: $name"
}

resolve_deploy_host_target() {
    if [[ -n "${DEPLOY_HOST_NAME:-}" ]]; then
        DEPLOY_HOST_TARGET="$DEPLOY_HOST_NAME"
    elif [[ -n "${DEPLOY_HOST_IP:-}" ]]; then
        DEPLOY_HOST_TARGET="$DEPLOY_HOST_IP"
    else
        fail "Missing required environment variable: DEPLOY_HOST_NAME or DEPLOY_HOST_IP"
    fi
}

shell_quote() {
    printf "'%s'" "${1//\'/\'\\\'\'}"
}

use_sshpass() {
    [[ -n "${DEPLOY_HOST_PWD:-}" && -x "$(command -v sshpass 2>/dev/null || true)" ]]
}

use_expect() {
    [[ -n "${DEPLOY_HOST_PWD:-}" && -x "$(command -v expect 2>/dev/null || true)" ]]
}

remote_target() {
    printf '%s@%s' "$DEPLOY_HOST_USER" "$DEPLOY_HOST_TARGET"
}

run_expect_password_command() {
    local password="$1"
    shift

    DEPLOY_EXPECT_PASSWORD="$password" expect -f - -- "$@" <<'EXPECT_SCRIPT'
set timeout -1
set password $env(DEPLOY_EXPECT_PASSWORD)
set command_args {}
for {set index 0} {$index < $argc} {incr index} {
    lappend command_args [lindex $argv $index]
}
spawn {*}$command_args
expect {
    -re "continue connecting" {
        send "yes\r"
        exp_continue
    }
    -re "assword:" {
        send -- "$password\r"
        exp_continue
    }
    eof {
        catch wait result
        exit [lindex $result 3]
    }
}
EXPECT_SCRIPT
}

run_expect_password_stdin_command() {
    local password="$1"
    local stdin_payload="$2"
    shift 2

DEPLOY_EXPECT_PASSWORD="$password" DEPLOY_EXPECT_STDIN="$stdin_payload" expect -f - -- "$@" <<'EXPECT_SCRIPT'
log_user 0
set timeout 30
set password $env(DEPLOY_EXPECT_PASSWORD)
set stdin_payload $env(DEPLOY_EXPECT_STDIN)
set sent_stdin 0
set command_args {}
for {set index 0} {$index < $argc} {incr index} {
    lappend command_args [lindex $argv $index]
}
spawn {*}$command_args
expect {
    -re "continue connecting" {
        send "yes\r"
        exp_continue
    }
    -re "assword:" {
        send -- "$password\r"
        set timeout 1
        exp_continue
    }
    timeout {
        if {$sent_stdin == 0} {
            send -- "$stdin_payload"
            send "\004"
            set sent_stdin 1
            set timeout -1
            exp_continue
        }
        exit 124
    }
    eof {
        catch wait result
        exit [lindex $result 3]
    }
}
EXPECT_SCRIPT
}

run_ssh() {
    local target remote_command
    target="$(remote_target)"
    remote_command="PATH=$REMOTE_COMMAND_PATH; export PATH; $*"

    if use_sshpass; then
        SSHPASS="$DEPLOY_HOST_PWD" sshpass -e ssh "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    elif use_expect; then
        run_expect_password_command "$DEPLOY_HOST_PWD" ssh "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    else
        ssh "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    fi
}

run_ssh_tty() {
    local target remote_command
    target="$(remote_target)"
    remote_command="PATH=$REMOTE_COMMAND_PATH; export PATH; $*"

    if use_sshpass; then
        SSHPASS="$DEPLOY_HOST_PWD" sshpass -e ssh -tt "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    elif use_expect; then
        run_expect_password_command "$DEPLOY_HOST_PWD" ssh -tt "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    else
        ssh -tt "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    fi
}

run_ssh_with_stdin() {
    local stdin_payload="$1"
    local target remote_command
    shift
    target="$(remote_target)"
    remote_command="PATH=$REMOTE_COMMAND_PATH; export PATH; $*"

    if use_sshpass; then
        printf '%s' "$stdin_payload" | SSHPASS="$DEPLOY_HOST_PWD" sshpass -e ssh "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    elif use_expect; then
        run_expect_password_stdin_command "$DEPLOY_HOST_PWD" "$stdin_payload" ssh "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    else
        printf '%s' "$stdin_payload" | ssh "${SSH_OPTIONS[@]}" "$target" "$remote_command"
    fi
}

run_scp() {
    if use_sshpass; then
        SSHPASS="$DEPLOY_HOST_PWD" sshpass -e scp "${SSH_OPTIONS[@]}" "$@"
    elif use_expect; then
        run_expect_password_command "$DEPLOY_HOST_PWD" scp "${SSH_OPTIONS[@]}" "$@"
    else
        scp "${SSH_OPTIONS[@]}" "$@"
    fi
}

write_remote_runtime_env() {
    local quoted_app_dir quoted_env_file quoted_work_dir
    quoted_app_dir="$(shell_quote "$REMOTE_APP_DIR")"
    quoted_env_file="$(shell_quote "$REMOTE_ENV_FILE")"
    quoted_work_dir="$(shell_quote "$REMOTE_WORK_DIR")"

    run_ssh "mkdir -p $quoted_app_dir $quoted_work_dir && chmod 700 $quoted_app_dir && chmod 1777 $quoted_work_dir"
    run_ssh_with_stdin "OPENAI_API_KEY=$OPENAI_API_KEY"$'\n' "umask 077 && cat > $quoted_env_file"
}

publish_arg() {
    if [[ -n "$HOST_BIND_IP" ]]; then
        printf '%s:%s:%s' "$HOST_BIND_IP" "$HOST_PORT" "$CONTAINER_PORT"
    else
        printf '%s:%s' "$HOST_PORT" "$CONTAINER_PORT"
    fi
}

probe_remote_health() {
    local health_url="http://$DEPLOY_HOST_TARGET:$HOST_PORT/_stcore/health"

    if command -v curl >/dev/null 2>&1; then
        curl -fsS "$health_url" >/dev/null
    else
        python3 - "$health_url" <<'PY'
import sys
from urllib.request import urlopen

urlopen(sys.argv[1], timeout=10).read()
PY
    fi
}

check_remote_health() {
    local health_url="http://$DEPLOY_HOST_TARGET:$HOST_PORT/_stcore/health"
    local attempt=1

    log "Checking remote health endpoint: $health_url"
    while ((attempt <= HEALTH_RETRIES)); do
        if probe_remote_health; then
            return
        fi

        sleep "$HEALTH_DELAY_SECONDS"
        attempt=$((attempt + 1))
    done

    fail "Remote health endpoint did not become healthy after $HEALTH_RETRIES attempts"
}

ensure_remote_docker() {
    if run_ssh "docker --version >/dev/null 2>&1"; then
        return
    fi

    if [[ "$INSTALL_DOCKER_IF_MISSING" != "true" ]]; then
        fail "Docker is not available on the remote host. Install Docker or rerun with INSTALL_DOCKER_IF_MISSING=true."
    fi

    if run_ssh "[ \"\$(uname -s)\" = \"Darwin\" ]"; then
        install_remote_docker_desktop_mac
    else
        install_remote_docker_engine_linux
    fi

    run_ssh "docker --version >/dev/null 2>&1"
}

install_remote_docker_engine_linux() {
    log "Docker is missing on the remote Linux host; attempting installation with Docker's convenience script"
    run_ssh "command -v curl >/dev/null 2>&1 || (sudo -n apt-get update && sudo -n apt-get install -y ca-certificates curl)"
    run_ssh "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sudo -n sh /tmp/get-docker.sh && rm -f /tmp/get-docker.sh"
}

install_remote_docker_desktop_mac() {
    local quoted_user
    quoted_user="$(shell_quote "$DEPLOY_HOST_USER")"

    log "Docker is missing on the remote macOS host; attempting Docker Desktop installation"
    run_ssh_tty "set -e; \
        arch=\"\$(uname -m)\"; \
        if [ \"\$arch\" = \"arm64\" ]; then docker_dmg_url='https://desktop.docker.com/mac/main/arm64/Docker.dmg'; else docker_dmg_url='https://desktop.docker.com/mac/main/amd64/Docker.dmg'; fi; \
        hdiutil detach /Volumes/Docker -quiet >/dev/null 2>&1 || true; \
        rm -f /tmp/Docker.dmg; \
        curl -fL \"\$docker_dmg_url\" -o /tmp/Docker.dmg; \
        hdiutil attach /tmp/Docker.dmg -nobrowse -quiet; \
        sudo /Volumes/Docker/Docker.app/Contents/MacOS/install --accept-license --user $quoted_user; \
        hdiutil detach /Volumes/Docker -quiet >/dev/null 2>&1 || true; \
        rm -f /tmp/Docker.dmg; \
        mkdir -p \"\$HOME/.local/bin\"; \
        ln -sfn /Applications/Docker.app/Contents/Resources/bin/docker \"\$HOME/.local/bin/docker\"; \
        ln -sfn /Applications/Docker.app/Contents/Resources/bin/docker-credential-desktop \"\$HOME/.local/bin/docker-credential-desktop\"; \
        ln -sfn /Applications/Docker.app/Contents/Resources/bin/docker-credential-osxkeychain \"\$HOME/.local/bin/docker-credential-osxkeychain\"; \
        open -a Docker || true; \
        for attempt in \$(seq 1 90); do \
            if docker info >/dev/null 2>&1; then exit 0; fi; \
            sleep 2; \
        done; \
        exit 1"
}

main() {
    load_dotenv

    resolve_deploy_host_target
    require_env "DEPLOY_HOST_USER"
    require_env "OPENAI_API_KEY"
    require_command "docker"
    require_command "ssh"
    require_command "scp"

    if [[ -n "${DEPLOY_HOST_PWD:-}" ]] && ! use_sshpass && ! use_expect; then
        log "DEPLOY_HOST_PWD is set, but neither sshpass nor expect is installed. Falling back to SSH key or interactive auth."
    fi

    mkdir -p "$(dirname "$LOCAL_IMAGE_ARCHIVE")"

    log "Building image $IMAGE_REF"
    docker build -t "$IMAGE_REF" "$PROJECT_ROOT"

    log "Saving image archive to $LOCAL_IMAGE_ARCHIVE"
    docker save "$IMAGE_REF" -o "$LOCAL_IMAGE_ARCHIVE"

    log "Verifying remote Docker access"
    ensure_remote_docker

    log "Copying image archive to remote host"
    run_scp "$LOCAL_IMAGE_ARCHIVE" "$(remote_target):$REMOTE_IMAGE_ARCHIVE"

    log "Writing remote runtime env file"
    write_remote_runtime_env

    local quoted_archive quoted_env_file quoted_volume publish
    quoted_archive="$(shell_quote "$REMOTE_IMAGE_ARCHIVE")"
    quoted_env_file="$(shell_quote "$REMOTE_ENV_FILE")"
    quoted_volume="$(shell_quote "$REMOTE_WORK_DIR:$CONTAINER_WORK_DIR")"
    publish="$(publish_arg)"

    log "Loading image and replacing remote container"
    run_ssh "docker load -i $quoted_archive && (docker rm -f $(shell_quote "$CONTAINER_NAME") >/dev/null 2>&1 || true) && docker run -d --name $(shell_quote "$CONTAINER_NAME") --restart unless-stopped --cpus $(shell_quote "$DOCKER_CPUS") --memory $(shell_quote "$DOCKER_MEMORY") --env-file $quoted_env_file --volume $quoted_volume --publish $(shell_quote "$publish") $(shell_quote "$IMAGE_REF") && rm -f $quoted_archive"

    check_remote_health
    log "Deployment complete: http://$DEPLOY_HOST_TARGET:$HOST_PORT"
}

main "$@"
