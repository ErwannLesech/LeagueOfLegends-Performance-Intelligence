#!/usr/bin/env bash

set -euo pipefail

DRY_RUN=1
AUTO_YES=0
DO_PUSH=0
REMOTE_NAME="origin"
PUSH_REF=""

usage() {
  cat <<'EOF'
Usage:
  scripts/rebuild_git_history_2026.sh [--execute] [--yes] [--push] [--remote <name>] [--ref <branch>]

Description:
  Crée une série de commits anti-datés (février 2026 → 5 avril 2026)
  sur la branche courante, à partir des fichiers actuels du projet.

  IMPORTANT:
  - Le script NE rebuild PAS l'historique.
  - Le script NE crée PAS de branche orphan.
  - Il ajoute simplement des commits datés sur la branche active.

Modes:
  - Par défaut: dry-run (aucune modification)
  - --execute: applique réellement les commits

Options:
  --execute         Exécute les commits
  --yes             Ignore la confirmation interactive
  --push            Push automatiquement à la fin
  --remote <name>   Remote Git pour le push (défaut: origin)
  --ref <branch>    Branche cible du push (défaut: branche courante)
  -h, --help        Affiche cette aide
EOF
}

log() {
  printf '[antidate] %s\n' "$*"
}

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    eval "$*"
  fi
}

git_at() {
  local at_date="$1"
  shift

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] GIT_AUTHOR_DATE="%s" GIT_COMMITTER_DATE="%s" git %q' "$at_date" "$at_date" "$1"
    shift
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  else
    GIT_AUTHOR_DATE="$at_date" GIT_COMMITTER_DATE="$at_date" git "$@"
  fi
}

confirm_or_exit() {
  if [[ "$AUTO_YES" -eq 1 ]]; then
    return
  fi

  printf "Ce script va créer des commits anti-datés sur la branche courante. Continuer ? [y/N] "
  read -r answer
  if [[ ! "$answer" =~ ^[Yy]$ ]]; then
    log "Opération annulée."
    exit 0
  fi
}

snapshot_worktree() {
  readarray -t ALL_FILES < <(find . -type f ! -path './.git/*' -print | sed 's#^\./##' | sort)

  if [[ "${#ALL_FILES[@]}" -eq 0 ]]; then
    log "Aucun fichier détecté dans le repository."
    exit 1
  fi

  TMP_DIR="$(mktemp -d)"
  SNAPSHOT_DIR="$TMP_DIR/snapshot"
  mkdir -p "$SNAPSHOT_DIR"

  if [[ "$DRY_RUN" -eq 0 ]]; then
    while IFS= read -r file; do
      mkdir -p "$SNAPSHOT_DIR/$(dirname "$file")"
      cp -a "$file" "$SNAPSHOT_DIR/$file"
    done < <(printf '%s\n' "${ALL_FILES[@]}")
  fi
}

cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}

restore_specs() {
  local specs=("$@")

  for spec in "${specs[@]}"; do
    local matched=0
    for file in "${ALL_FILES[@]}"; do
      if [[ "$file" == "$spec" || "$file" == "$spec/"* ]]; then
        matched=1
        if [[ "$DRY_RUN" -eq 1 ]]; then
          printf '[dry-run] stage from snapshot: %s\n' "$file"
        else
          mkdir -p "$(dirname "$file")"
          cp -a "$SNAPSHOT_DIR/$file" "$file"
        fi
      fi
    done

    if [[ "$matched" -eq 0 ]]; then
      printf '[warn] Aucun fichier trouvé pour: %s\n' "$spec"
    fi
  done
}

commit_step() {
  local at_date="$1"
  local message="$2"
  shift 2
  local specs=("$@")

  log "Commit: $message @ $at_date"
  restore_specs "${specs[@]}"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] git add -A --'
    for spec in "${specs[@]}"; do
      printf ' %q' "$spec"
    done
    printf '\n'
    git_at "$at_date" commit -m "$message"
    return
  fi

  git add -A -- "${specs[@]}"
  if git diff --cached --quiet; then
    log "Aucun changement pour ce commit: $message"
    return
  fi

  git_at "$at_date" commit -m "$message"
}

commit_remaining() {
  local at_date="$1"
  local message="$2"

  log "Commit final des fichiers restants @ $at_date"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] git add -A\n'
    git_at "$at_date" commit -m "$message"
    return
  fi

  git add -A
  if git diff --cached --quiet; then
    log "Aucun fichier restant à committer."
    return
  fi

  git_at "$at_date" commit -m "$message"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      DRY_RUN=0
      shift
      ;;
    --yes)
      AUTO_YES=1
      shift
      ;;
    --push)
      DO_PUSH=1
      shift
      ;;
    --remote)
      REMOTE_NAME="$2"
      shift 2
      ;;
    --ref)
      PUSH_REF="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Option inconnue: %s\n\n' "$1"
      usage
      exit 1
      ;;
  esac
done

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  log "Ce dossier n'est pas un repository Git."
  exit 1
fi

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
if [[ -z "$CURRENT_BRANCH" ]]; then
  CURRENT_BRANCH="main"
fi
if [[ "$CURRENT_BRANCH" == "HEAD" ]]; then
  log "Tu es en detached HEAD. Checkout une branche avant d'exécuter ce script."
  exit 1
fi

if [[ -z "$PUSH_REF" ]]; then
  PUSH_REF="$CURRENT_BRANCH"
fi

confirm_or_exit
snapshot_worktree
trap cleanup EXIT

log "Branche courante: $CURRENT_BRANCH"
log "Mode: $([[ "$DRY_RUN" -eq 1 ]] && echo 'dry-run' || echo 'execute')"

if [[ "$DRY_RUN" -eq 0 ]] && git rev-parse --verify HEAD >/dev/null 2>&1; then
  run "git reset --mixed"
fi

commit_step "2026-02-01T09:00:00+01:00" "chore(init): bootstrap project structure" \
  requirements.txt \
  docker-compose.yml \
  README.md

commit_step "2026-02-05T10:20:00+01:00" "feat(config): add settings and schema mapping" \
  config/

commit_step "2026-02-10T14:10:00+01:00" "feat(collector): add riot client and rate limiter" \
  collector/

commit_step "2026-02-17T17:30:00+01:00" "feat(pipeline): implement transform and database loading" \
  pipeline/

commit_step "2026-03-02T11:00:00+01:00" "feat(scripts): add backfill and automation scripts" \
  scripts/

commit_step "2026-03-15T16:45:00+01:00" "feat(analysis): add notebooks and SQL queries" \
  analysis/

commit_step "2026-03-28T12:15:00+01:00" "docs(readme): document setup and usage" \
  README.md

commit_remaining "2026-04-05T18:00:00+02:00" "chore(release): finalize project snapshot"

if [[ "$DO_PUSH" -eq 1 ]]; then
  run "git push -u $REMOTE_NAME $PUSH_REF"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Dry-run terminé. Relance avec --execute pour créer les commits."
else
  log "Terminé. Vérifie avec: git log --oneline --decorate -n 12"
  if [[ "$DO_PUSH" -eq 1 ]]; then
    log "Push demandé: $REMOTE_NAME/$PUSH_REF"
  else
    log "Aucun push automatique (utilise --push si besoin)."
  fi
fi
