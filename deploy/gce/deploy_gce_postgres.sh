#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright 2026 BellaKeri@github.com & balparda@github.com
# SPDX-License-Identifier: Apache-2.0
#
# deploy_gce_postgres.sh – provision a Compute Engine e2-micro VM running
# PostgreSQL 17, tuned for the FREE-tier (1 GB RAM).
#
# Prerequisites:
#   brew install --cask gcloud-cli   # macOS
#   gcloud auth login
#   gcloud config set project tfinta-prod
#
# Usage:
#   ./deploy/gce/deploy_gce_postgres.sh          # create VM + firewall
#   ./deploy/gce/deploy_gce_postgres.sh teardown  # delete VM + disk
#
# After the VM is running, SSH in and run the migration:
#   gcloud compute ssh tfinta-pg -- 'sudo -u postgres psql -f /opt/tfinta/db/migrations/000_create_database.sql'
#   gcloud compute ssh tfinta-pg -- 'PGPASSWORD=<pw> psql -U tfinta -d tfinta -f /opt/tfinta/db/migrations/001_initial_schema.sql'
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration (override with env vars)
# ---------------------------------------------------------------------------
PROJECT="${GCE_PROJECT:-tfinta-prod}"
ZONE="${GCE_ZONE:-europe-west1-b}"
MACHINE="${GCE_MACHINE:-e2-micro}"
DISK_SIZE="${GCE_DISK_SIZE:-30}"           # GB (free tier = 30 GB standard PD)
IMAGE_FAMILY="${GCE_IMAGE_FAMILY:-debian-12}"
IMAGE_PROJECT="${GCE_IMAGE_PROJECT:-debian-cloud}"
VM_NAME="${GCE_VM_NAME:-tfinta-pg}"
NETWORK_TAG="tfinta-pg"

# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "teardown" ]]; then
  echo "==> Deleting VM ${VM_NAME} ..."
  gcloud compute instances delete "${VM_NAME}" \
    --project="${PROJECT}" --zone="${ZONE}" --quiet || true
  echo "==> Deleting firewall rule allow-postgres ..."
  gcloud compute firewall-rules delete allow-postgres \
    --project="${PROJECT}" --quiet || true
  echo "==> Teardown complete."
  exit 0
fi

# ---------------------------------------------------------------------------
# Create VM
# ---------------------------------------------------------------------------
echo "==> Creating ${MACHINE} VM '${VM_NAME}' in ${ZONE} ..."

gcloud compute instances create "${VM_NAME}" \
  --project="${PROJECT}" \
  --zone="${ZONE}" \
  --machine-type="${MACHINE}" \
  --image-family="${IMAGE_FAMILY}" \
  --image-project="${IMAGE_PROJECT}" \
  --boot-disk-size="${DISK_SIZE}GB" \
  --boot-disk-type=pd-standard \
  --tags="${NETWORK_TAG}" \
  --metadata=startup-script='#!/bin/bash
set -ex

# Install PostgreSQL 17
apt-get update -qq
apt-get install -y -qq postgresql-common
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
apt-get install -y -qq postgresql-17

# Enable & start
systemctl enable postgresql
systemctl start postgresql

# Create TFINTA user & DB (idempotent)
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='"'"'tfinta'"'"'" \
  | grep -q 1 || sudo -u postgres psql -c "CREATE ROLE tfinta WITH LOGIN PASSWORD '"'"'changeme'"'"';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='"'"'tfinta'"'"'" \
  | grep -q 1 || sudo -u postgres createdb -O tfinta tfinta

# Allow password auth from all VPC IPs (10.x.x.x)
PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)
grep -q "host.*tfinta.*10\." "$PG_HBA" || \
  echo "host  tfinta  tfinta  10.0.0.0/8  scram-sha-256" >> "$PG_HBA"
# Also allow from Cloud Run connector / external (restrict in production!)
grep -q "host.*tfinta.*0\.0\.0\.0" "$PG_HBA" || \
  echo "host  tfinta  tfinta  0.0.0.0/0   scram-sha-256" >> "$PG_HBA"

# Apply TFINTA tuning
PG_CONF=$(find /etc/postgresql -name postgresql.conf | head -1)
cat >> "$PG_CONF" << TUNECFG

# --- TFINTA e2-micro tuning ---
max_connections = 30
shared_buffers = 128MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 512MB
wal_buffers = 4MB
checkpoint_completion_target = 0.9
min_wal_size = 80MB
max_wal_size = 256MB
autovacuum = on
autovacuum_max_workers = 2
autovacuum_naptime = 60s
log_min_duration_statement = 500
timezone = '"'"'UTC'"'"'
TUNECFG

# Listen on all interfaces
sed -i "s/#listen_addresses = .*/listen_addresses = '"'"'*'"'"'/" "$PG_CONF"

systemctl restart postgresql
echo "TFINTA PostgreSQL ready."
'

echo "==> VM created."

# ---------------------------------------------------------------------------
# Firewall: allow Postgres from Cloud Run / your IP (restrict in prod)
# ---------------------------------------------------------------------------
echo "==> Creating firewall rule (tcp:5432) for tag '${NETWORK_TAG}' ..."

gcloud compute firewall-rules create allow-postgres \
  --project="${PROJECT}" \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:5432 \
  --source-ranges=0.0.0.0/0 \
  --target-tags="${NETWORK_TAG}" \
  --description="Allow PostgreSQL traffic to TFINTA DB VM" \
  2>/dev/null || echo "    (firewall rule already exists)"

echo ""
echo "==> Done.  SSH into the VM:"
echo "    gcloud compute ssh ${VM_NAME} --zone=${ZONE}"
echo ""
echo "==> Get the external IP:"
echo "    gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"
echo ""
echo "==> Then run migrations (from your local machine):"
echo "    PGHOST=<VM_IP> PGPASSWORD=changeme ./db/migrate.sh"
