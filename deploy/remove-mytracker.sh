#!/usr/bin/env bash
# One-off, requested by the owner: delete the mytracker Docker stack (containers,
# volumes, images) to free ports 80/443 for blakecards.it. No backup kept.
set -euo pipefail

mapfile -t ids < <(docker ps -aq --filter name=mytracker)
if [[ ${#ids[@]} -eq 0 ]]; then
  echo "==> Nessun container mytracker: niente da togliere"
  exit 0
fi

echo "==> Container mytracker trovati:"
docker ps -a --filter name=mytracker --format '  {{.Names}} | {{.Image}} | {{.Status}}'

DIR=$(docker inspect "${ids[0]}" --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' 2>/dev/null || true)
PROJECT=$(docker inspect "${ids[0]}" --format '{{ index .Config.Labels "com.docker.compose.project" }}' 2>/dev/null || true)
echo "==> Progetto compose: ${PROJECT:-nessuno} in ${DIR:-?}"

if [[ -n $PROJECT ]] && docker compose -p "$PROJECT" ls >/dev/null 2>&1; then
  if [[ -n $DIR && -d $DIR ]]; then
    (cd "$DIR" && docker compose -p "$PROJECT" down --volumes --rmi all --remove-orphans) || true
  else
    docker compose -p "$PROJECT" down --volumes --rmi all --remove-orphans || true
  fi
fi

# Anything compose didn't catch (or no compose at all).
mapfile -t left < <(docker ps -aq --filter name=mytracker)
if [[ ${#left[@]} -gt 0 ]]; then
  mapfile -t vols < <(docker inspect "${left[@]}" --format '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}}{{"\n"}}{{end}}{{end}}' | sort -u | grep . || true)
  docker rm -f "${left[@]}" >/dev/null
  [[ ${#vols[@]} -gt 0 ]] && docker volume rm "${vols[@]}" >/dev/null || true
fi
[[ -n $PROJECT ]] && docker network ls -q --filter "label=com.docker.compose.project=$PROJECT" | xargs -r docker network rm >/dev/null || true

echo "==> Rimasti: $(docker ps -a --filter name=mytracker -q | wc -l) container mytracker"
echo "==> Volumi rimasti: $(docker volume ls -q | grep -c mytracker || true)"
[[ -n $DIR && -d $DIR ]] && echo "==> Il codice resta in $DIR (non cancellato)"
echo "==> Porta 80: $(ss -ltnH '( sport = :80 )' | grep -q . && echo 'ancora occupata' || echo libera)"
