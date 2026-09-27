#!/usr/bin/env sh
# itsmlab.sh - run the course checker (itsmlab) as a container against the current directory.
#
#   ./itsmlab.sh doctor
#   ./itsmlab.sh verify 1 --json report.json
#   ./itsmlab.sh submit 1 --kind submission --tag lab1/v1
#
# Every argument is passed through to itsmlab. The image comes from, in order of precedence:
#   1. the environment variable ITSMLAB_IMAGE,
#   2. "checker_image:" in ./itsmlab.yaml,
#   3. ghcr.io/swasik/itsmlab:2026.
# The current directory is mounted at the same absolute path inside the container, and the
# Docker socket is mounted so that the checker can run "docker compose" for your service.
set -eu

default_image="ghcr.io/swasik/itsmlab:2026"

yaml_image=""
if [ -f itsmlab.yaml ]; then
  yaml_image="$(sed -n 's/^checker_image:[[:space:]]*"\{0,1\}\([^"#[:space:]]*\)"\{0,1\}.*/\1/p' itsmlab.yaml | head -n 1)"
fi
image="${ITSMLAB_IMAGE:-${yaml_image:-$default_image}}"

# Docker socket: /var/run/docker.sock, unless DOCKER_HOST points at another unix socket
# (rootless Docker, Colima, OrbStack). On Docker Desktop for macOS that path does not exist on the Mac
# itself (the CLI reaches the daemon through ~/.docker/run/docker.sock), but the bind mount resolves
# inside Docker Desktop's VM, where it does exist, so the default is correct there too.
sock="/var/run/docker.sock"
extra=""
case "${DOCKER_HOST:-}" in
  unix://*) sock="${DOCKER_HOST#unix://}" ;;
  "") ;;
  *) extra="-e DOCKER_HOST=$DOCKER_HOST" ;;   # tcp://, ssh://: the CLI in the container needs it
esac

# shellcheck disable=SC2086
exec docker run --rm \
  -v "$PWD:$PWD" -w "$PWD" \
  -v "$sock:/var/run/docker.sock" \
  $extra \
  "$image" "$@"
