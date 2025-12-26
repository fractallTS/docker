# E-commerce Docker Compose stack

This repository contains a Docker Compose application stack for a small e-commerce API used in a DevOps assignment. It provides a multi-service stack with Postgres, Redis, a Flask app, nginx (with TLS), and Certbot automation. CI builds images with BuildX and publishes to GHCR.

Quick links
- Compose file: `compose.yaml`
- App: `app/app.py`
- DB init: `database/init.sql`
- CI workflow: `.github/workflows/build-and-push.yml`

Architecture / Services
- `db` — PostgreSQL with initialization script and persistent volume.
- `redis` — Redis cache (persistent volume `redis_data`).
- `app` — Flask API served by Gunicorn (multi-stage Dockerfile, venv-based).
- `nginx` / `html` — Nginx front-end and reverse-proxy; TLS termination.
- `certbot` — Certificate issuance (DNS Cloudflare plugin).
- `certbot-renew` — Renewal loop that reloads nginx after renewals.

Prerequisites
- Docker (and `docker compose`) installed on host.
- On production VM: open ports `80` and `443`.
- Create a `.env` from `.env.example` and set `GITHUB_OWNER`/`GITHUB_REPO` if you want images tagged for GHCR.
- Place secrets on the host (do NOT commit):
	- `secrets/db_password`, `secrets/db_user`, `secrets/db_name`
	- `secrets/cloudflare.ini` — Cloudflare API token for DNS challenge (format shown below).

Cloudflare credentials file (`secrets/cloudflare.ini`) example
```
[dns_cloudflare]
dns_cloudflare_api_token = 0123456789abcdef0123456789abcdef
```

Local development (quick start)
1. Copy example env and edit:
```bash
cp .env.example .env
# edit .env as needed
```
2. Ensure `secrets/` and `certbot/conf` exist on host and contain proper files (see above).
3. Start the stack (builds locally unless images are pulled):
```bash
docker compose up --build -d
```
4. Check services:
```bash
docker compose ps
docker compose logs -f
curl http://localhost:5000/health
curl -k https://localhost/  # if testing TLS locally with certs
```

CI / GitHub Actions
- Workflow: `.github/workflows/build-and-push.yml`. It uses `docker/setup-buildx-action` and `docker/build-push-action` to build multi-platform images and push to GHCR.
- Default registry in workflow: `ghcr.io`. It tags images as `ghcr.io/<owner>/<repo>-app:latest` and `ghcr.io/<owner>/<repo>-app:<short-sha>` (same pattern for `html` and `database`).
- Required repo configuration: GitHub Actions uses `GITHUB_TOKEN` for GHCR push; ensure `Allow GitHub Actions to create and publish packages` is enabled in repo settings if needed.
- To use Docker Hub instead, modify the login and tags in the workflow and add `DOCKERHUB_USER`/`DOCKERHUB_TOKEN` secrets.

TLS / Certificates
- The Compose stack uses nginx with certificate files mounted from `./certbot/conf`.
- The `certbot` service runs a one-shot issuance command using the Cloudflare DNS plugin. Provide `secrets/cloudflare.ini` with your API token.
- To obtain initial certificates run (once) while DNS credentials are present:
```bash
docker compose run --rm certbot
```
- The repository includes `certbot/renew-loop.sh` and a `certbot-renew` service in `compose.yaml` which periodically runs `certbot renew` and reloads `nginx`.

Notes about security and best-practices
- Do NOT commit secrets to git. Use GitHub Secrets for CI and host files for Compose secrets.
- The `certbot-renew` service mounts the Docker socket to run `docker exec` to reload nginx. This is convenient but exposes the Docker API — consider running renewals on the host instead for higher security.
- Pin image versions for reproducibility (e.g., `postgres:15`, `nginx:1.25`, `redis:7`) if deploying to production.
- Postgres data path set to `/var/lib/postgresql/data` and Redis persists to `redis_data` volume.
  
Postgres pinning and recovery (current state)
- The project is pinned to PostgreSQL 17 for stability. See `database/Dockerfile` which uses `FROM postgres:17`.
- During a test/upgrade run a legacy on-volume Postgres layout was encountered. To preserve data we:
	1. Created a tarball backup of the old volume mountpoint (saved under `/tmp/docker_db_data_backup_<timestamp>.tgz` on the host).
	2. Launched a temporary `postgres:17` container mounting the existing `docker_db_data` volume and ran `pg_dumpall` to produce `/tmp/all_databases.sql` on the host.
	3. Created a fresh volume `docker_db_data_fresh`, started a clean `postgres:17` cluster on it, and restored `/tmp/all_databases.sql` into the fresh cluster.

- Current runtime configuration uses the fresh volume name `docker_db_data_fresh` (see `compose.yaml`). The original volume `docker_db_data` was intentionally left in place (not removed) to preserve the raw on-disk data for future inspection or a `pg_upgrade` attempt.

- Files created during recovery (on the host):
	- Backup tarball: `/tmp/docker_db_data_backup_<timestamp>.tgz`
	- SQL dump: `/tmp/all_databases.sql`

- Recommendation: keep the DB pinned to Postgres 17 (`postgres:17`) in production until you schedule a controlled upgrade. For future major upgrades you can either:
	- Perform a dump/restore (what we did) — easiest and safest for most workloads.
	- Use `pg_upgrade` with both old and new server binaries and a single mount at `/var/lib/postgresql` (advanced; preserves physical layout and can be faster for very large DBs).

- We did NOT remove the original `docker_db_data` volume. If you later decide to reclaim space, remove it only after you are certain the fresh cluster is correct and you have additional backups.

Deployment to a VM (systemd)
- Unit template: `deploy/docker-stack.service` — copy to `/etc/systemd/system/docker-stack.service` and edit `WorkingDirectory`/`EnvironmentFile` paths.
- Helper installer: `deploy/systemd-install.sh` (run with `sudo`) will copy and start the unit.

Testing and healthchecks
- Containers include healthchecks defined in `compose.yaml` for `db`, `redis`, `app`, and `nginx`.
- Use `docker compose ps` and `docker compose logs` to diagnose issues.

Grading checklist (how this repo meets the assignment)
- Minimum 4 services: `db`, `redis`, `app`, `nginx` (+ certbot) — satisfied.
- Docker Compose used: `compose.yaml` — satisfied.
- Volumes used for persistence: `db_data`, `redis_data` — satisfied.
- Multi-stage custom build: `app/Dockerfile` multi-stage with venv — satisfied.
- BuildX + CI: `.github/workflows/build-and-push.yml` builds with BuildX and pushes to GHCR — satisfied.
- TLS: nginx + certbot using DNS Cloudflare plugin and renewal loop — implemented.

Next steps / suggestions
- If you want automatic deployment on image push, add a separate GitHub Actions deploy job (not implemented by default).
- Consider switching `certbot-renew` to a host cron job or a container with fewer privileges.

If you want, I can now:
- run a local `docker compose up` to smoke-test the stack, or
- prepare a short checklist of repo secrets and GHCR settings to finalize CI.

