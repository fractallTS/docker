# Running the Docker Compose stack as a systemd service

This file describes how to run the project as a systemd-managed service on a Linux VM (e.g. your devops-sk-XX VM).

Prerequisites
- Docker and Docker Compose (or Docker Engine that supports `docker compose`) installed on the VM.
- The project cloned to a directory, e.g. `/home/ubuntu/DevOps/docker`.
- A populated `.env` file (see `.env.example`) and the following host folders/files in place (do NOT commit secrets):
  - `./secrets/db_password`, `./secrets/db_user`, `./secrets/db_name`
  - `./secrets/cloudflare.ini` (for certbot DNS plugin)
  - `./certbot/conf` (will be created by certbot when issuing certificates)

Systemd unit template
Create a unit file `/etc/systemd/system/docker-stack.service` with the following contents (update paths as needed):

[Unit]
Description=Docker Compose: E-commerce stack
Requires=docker.service
After=docker.service

[Service]
Type=notify
Restart=always
WorkingDirectory=/home/ubuntu/DevOps/docker
EnvironmentFile=/home/ubuntu/DevOps/docker/.env
ExecStart=/usr/bin/docker compose -f /home/ubuntu/DevOps/docker/compose.yaml up --remove-orphans
ExecStop=/usr/bin/docker compose -f /home/ubuntu/DevOps/docker/compose.yaml down
TimeoutStartSec=0
RemainAfterExit=no

[Install]
WantedBy=multi-user.target

Notes and best-practices
- Use the absolute path to `docker` and `docker compose` binaries on your system (`which docker`).
- The unit uses `WorkingDirectory` so the compose command can access the compose file and `.env`.
- `EnvironmentFile` points to the `.env` file (copy `.env.example` and fill values). Keep this file OUT of version control.
- Ensure the `certbot` and `secrets` directories exist and are correctly mounted before starting the service.
- Firewall: open ports `80` and `443` so Let's Encrypt can validate and users can access the app.
- For improved security, consider running `certbot-renew` with restricted privileges or handle renewals on the host via cron.

Host renewal (recommended)
- Use a systemd timer or cron on the host to run certificate renewal. This avoids mounting the Docker socket inside a container and keeps renewals under host control.

Example systemd timer (create two files under `/etc/systemd/system`):

1) `/etc/systemd/system/certbot-renew.service`

[Unit]
Description=Run certbot renew for Docker Compose stack

[Service]
Type=oneshot
WorkingDirectory=/home/ubuntu/DevOps/docker
ExecStart=/usr/bin/docker run --rm -v /home/ubuntu/DevOps/docker/certbot/conf:/etc/letsencrypt -v /home/ubuntu/DevOps/docker/secrets/cloudflare.ini:/etc/letsencrypt/cloudflare.ini:ro certbot/dns-cloudflare:latest renew --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini --dns-cloudflare-propagation-seconds 30
ExecStartPost=/usr/bin/docker compose -f /home/ubuntu/DevOps/docker/compose.yaml up -d nginx

2) `/etc/systemd/system/certbot-renew.timer`

[Unit]
Description=Run certbot renew twice daily

[Timer]
OnCalendar=*-*-* 03/12:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target

Enable and start the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now certbot-renew.timer
sudo systemctl status certbot-renew.timer
```

Notes:
- Adjust paths in the unit files to match where you cloned the repo.
- The `ExecStartPost` will restart nginx after a successful renewal so changes take effect.
- This approach avoids exposing the Docker socket to an in-container process.

Enable and start the service

```bash
sudo cp /home/ubuntu/DevOps/docker/deploy/docker-stack.service /etc/systemd/system/docker-stack.service
sudo systemctl daemon-reload
sudo systemctl enable docker-stack.service
sudo systemctl start docker-stack.service
sudo systemctl status docker-stack.service
```

Logs

View unit logs with:

```bash
sudo journalctl -u docker-stack.service -f
```

If containers fail to start, inspect Docker Compose logs:

```bash
docker compose -f /home/ubuntu/DevOps/docker/compose.yaml logs --no-color --follow
```
