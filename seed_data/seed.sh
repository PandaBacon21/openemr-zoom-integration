#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

read_dotenv_value() {
  local key="$1"
  local file="$ROOT_DIR/.env"
  local line
  local value

  [ -f "$file" ] || return 0

  line=$(grep -E "^${key}=" "$file" | tail -n 1 || true)
  [ -n "$line" ] || return 0

  value="${line#*=}"
  value="${value%$'\r'}"

  if [[ "${value:0:1}" == "\"" && "${value: -1}" == "\"" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
    value="${value:1:${#value}-2}"
  fi

  printf '%s' "$value"
}

DOTENV_MYSQL_ROOT_PASSWORD="$(read_dotenv_value MYSQL_ROOT_PASSWORD)"
DOTENV_MARIADB_CONTAINER="$(read_dotenv_value MARIADB_CONTAINER)"
DOTENV_OPENEMR_DB_NAME="$(read_dotenv_value OPENEMR_DB_NAME)"

DB_ROOT_PASS=${MYSQL_ROOT_PASSWORD:-${DOTENV_MYSQL_ROOT_PASSWORD:-change-me-db-root}}
DB_CONTAINER=${MARIADB_CONTAINER:-${DOTENV_MARIADB_CONTAINER:-mariadb-emr}}
DB_NAME=${OPENEMR_DB_NAME:-${DOTENV_OPENEMR_DB_NAME:-openemr}}

echo "Seeding demo data into $DB_CONTAINER..."
docker exec -i "$DB_CONTAINER" mariadb -u root -p"$DB_ROOT_PASS" "$DB_NAME" < "$SCRIPT_DIR/demo_data.sql"

echo "Done."
