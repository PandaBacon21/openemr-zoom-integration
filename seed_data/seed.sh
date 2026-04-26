#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env for DB credentials and seed config
if [ -f "$ROOT_DIR/.env" ]; then
  MYSQL_ROOT_PASSWORD=$(grep '^MYSQL_ROOT_PASSWORD=' "$ROOT_DIR/.env" | cut -d '=' -f2)
  MARIADB_CONTAINER=$(grep '^MARIADB_CONTAINER=' "$ROOT_DIR/.env" | cut -d '=' -f2)
  OPENEMR_DB_NAME=$(grep '^OPENEMR_DB_NAME=' "$ROOT_DIR/.env" | cut -d '=' -f2)
fi

DB_ROOT_PASS=${MYSQL_ROOT_PASSWORD:-change-me-db-root}
DB_CONTAINER=${MARIADB_CONTAINER:-mariadb-emr}
DB_NAME=${OPENEMR_DB_NAME:-openemr}

# Email used for all seeded providers and patients - for testing purposes
# Will update to their Demo Portal emails in the future
# SEED_EMAIL in .env file or override inline:
# SEED_EMAIL=you@example.com ./seed_data/seed.sh
SEED_EMAIL=${SEED_EMAIL:-seed@example.com}

echo "Seeding demo data into $DB_CONTAINER..."
echo "Using seed email: $SEED_EMAIL"

# Replace placeholder in SQL and pipe to container
sed "s/SEED_EMAIL_PLACEHOLDER/$SEED_EMAIL/g" "$SCRIPT_DIR/demo_data.sql" | \
  docker exec -i "$DB_CONTAINER" mariadb -u root -p"$DB_ROOT_PASS" "$DB_NAME"

echo "Done."