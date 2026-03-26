# Podman Setup & Befehle — Stand 25.03.2026

## Hardware & Windows
- **HP Compaq 8200 Elite** — i7-2600, 8GB RAM, Windows 10 Home
- **VT-x aktiv** via HP BCU — persistent durch Task Scheduler `HP-BCU-VTx-Restore`
- **WSL2** Standardversion 2

---

## WSL2 Config (`C:\Users\dj_fi\.wslconfig`)
```ini
memory=3GB
processors=4
swap=16GB
swapFile=D:\\wsl-swap.vhdx
```

---

## Stack
- **Podman 5.8.1** — `C:\Program Files\RedHat\Podman\`
- **Daten auf D:** via `XDG_DATA_HOME=D:\PodmanData`
- **Docker API** aktiv — `docker`-Befehle funktionieren direkt ohne Alias
- **Podman Machine:** `podman-machine-default` — Fedora 43 Container
- **Paketmanager in Machine:** `dnf` (NICHT rpm-ostree!)
- **OCI-Runtime:** Youki 0.6.0 (Fallback: `--runtime=runc`)
- **podman-compose, Skopeo, Distrobox, Quadlet** installiert

---

## WICHTIG: Wo arbeiten?

> Projekte IMMER in `~/projects/` inside der Machine anlegen.
> Nie auf `/mnt/d/` oder `/mnt/c/` — 10x langsamer, Hot-Reload kaputt.

### RocksDB / Tuwunel Hinweis
Tuwunel nutzt RocksDB als Datenbank. Die Config `rocksdb_direct_io` in `tuwunel.toml` muss zum Filesystem passen:
- **Podman Machine** (`~/projects/` = ext4): `rocksdb_direct_io = true` — schneller, Direct I/O funktioniert
- **Windows WSL2** (`/mnt/d/` = NTFS via 9P): `rocksdb_direct_io = false` — 9P kann Direct I/O nicht korrekt weiterleiten, potentielle DB-Korruption

```
Windows       ->  nur podman machine start/stop
Machine SSH   ->  alle Builds, compose, git clone
```

---

## Entwicklungsworkflow

**podman-compose ist NUR inside der Machine installiert** — nicht auf Windows.
`podman run/build/ps` funktionieren von Windows direkt, `podman-compose` nicht.

```
Windows CMD:    podman run, podman build, podman ps   -> OK
Windows CMD:    podman-compose up                     -> FEHLER
Machine:        podman-compose up                     -> OK
```

**Entwicklungstools (bun, go, uv etc.) in der Machine installieren:**

```bash
# [MACHINE] Direkt in Fedora Machine:
sudo dnf install -y golang git
curl -fsSL https://bun.sh/install | bash
pip install uv

# Dann normal:
cd ~/projects/matrix
bun install && bun dev
go run .
uv sync
```

**Zwei Ansaetze fuer Projekt-Isolation:**

Option A — Alles direkt in Machine (einfacher, ein Environment):
```bash
# [MACHINE] Tools einmalig installieren, alle Projekte teilen sich die Machine
```

Option B — Distrobox pro Projekt (sauberer, keine Konflikte):
```bash
# [MACHINE] Eigener Container pro Tech-Stack:
distrobox create --name matrix-dev --image ubuntu:24.04
distrobox enter matrix-dev
# -> hier bun, go, uv installieren, nur fuer dieses Projekt
```

---

## Machine Befehle (Windows CMD/PowerShell)

```bash
podman machine start                    # Machine starten
podman machine stop                     # Machine stoppen
podman machine ssh                      # In Machine einloggen
podman machine ssh -- <befehl>          # Einzelnen Befehl in Machine ausfuehren
podman machine ls                       # Machines auflisten
podman machine inspect                  # Details anzeigen
```

---

## Container Befehle (Windows oder Machine)

```bash
podman ps                               # Laufende Container
podman ps -a                            # Alle Container inkl. gestoppte
podman images                           # Lokale Images
podman pull nginx                       # Image herunterladen (Docker Hub)
podman run -d -p 8080:80 nginx          # Container starten
podman stop <name>                      # Container stoppen
podman rm <name>                        # Container loeschen
podman rmi <image>                      # Image loeschen
podman logs <name>                      # Logs anzeigen
podman exec -it <name> bash             # In Container einsteigen
podman run --runtime=runc nginx         # Explizit runc als Runtime
```

---

## Build (IN MACHINE AUSFUEHREN — ~/projects/)

```bash
# [MACHINE] In Machine einloggen
podman machine ssh

# [MACHINE] Projekt anlegen/klonen
cd ~/projects
git clone https://github.com/user/projekt
cd projekt

# [MACHINE] Image bauen (Dockerfile oder Containerfile, beide funktionieren)
podman build -t meinimage .
podman build -t meinimage:v1.0 .
podman build -f Dockerfile.prod -t meinimage .

# [MACHINE] Image testen
podman run --rm -p 3000:3000 meinimage
```

---

## Docker Compose / podman-compose (IN MACHINE AUSFUEHREN)

```bash
# [MACHINE] Starten
podman-compose up
podman-compose up -d                    # Im Hintergrund
podman-compose up --build               # Images neu bauen

# [MACHINE] Stoppen
podman-compose down
podman-compose down -v                  # inkl. Volumes loeschen

# [MACHINE] Status & Logs
podman-compose ps
podman-compose logs
podman-compose logs -f <service>        # Live-Logs

# [MACHINE] Einzelner Service
podman-compose up -d db
podman-compose restart web

# [MACHINE] In Service einsteigen
podman-compose exec web bash
```

---

## Volumes & Netzwerk

```bash
podman volume create meinvolume
podman volume ls
podman volume rm meinvolume

podman network ls
podman network create meinnet
podman network inspect meinnet
```

---

## Skopeo (IN MACHINE)

```bash
# [MACHINE] Image inspizieren OHNE herunterzuladen
skopeo inspect docker://nginx:alpine
skopeo inspect docker://ghcr.io/user/image:tag

# [MACHINE] Image zwischen Registries kopieren
skopeo copy docker://nginx docker://myregistry.io/nginx

# [MACHINE] Image als Archiv exportieren
skopeo copy containers-storage:localhost/meinimage oci-archive:/tmp/meinimage.tar

# [MACHINE] Tags einer Registry auflisten
skopeo list-tags docker://quay.io/podman/stable
```

---

## Distrobox (IN MACHINE)

```bash
# [MACHINE] Ubuntu Container erstellen
distrobox create --name ubuntu-dev --image ubuntu:24.04

# [MACHINE] In Container einsteigen
distrobox enter ubuntu-dev

# Darin: normales Ubuntu, apt install etc.
sudo apt install nodejs npm

# [MACHINE] Container auflisten
distrobox list

# [MACHINE] Container loeschen
distrobox rm ubuntu-dev
```

---

## Quadlet — Permanente Services (IN MACHINE)

```bash
# [MACHINE] Datei anlegen
mkdir -p ~/.config/containers/systemd
nano ~/.config/containers/systemd/postgres.container
```

```ini
# Beispiel: Postgres immer laufen lassen
[Container]
Image=docker.io/library/postgres:16
Environment=POSTGRES_PASSWORD=geheim
PublishPort=5432:5432
Volume=pgdata:/var/lib/postgresql/data

[Service]
Restart=always
TimeoutStartSec=300

[Install]
WantedBy=default.target
```

```bash
# [MACHINE] Aktivieren
systemctl --user daemon-reload
systemctl --user start postgres
systemctl --user enable postgres        # beim Machine-Start automatisch
systemctl --user status postgres
```

---

## Neue Machine einrichten

```bash
# [WINDOWS] Machine erstellen
podman machine init --cpus 2 --memory 1536 --disk-size 20

# [WINDOWS] Setup-Script ausfuehren
podman machine ssh -- bash /mnt/d/Tools/setup-machine.sh
```

---

## VT-x wiederherstellen (nach BIOS-Update)

```bash
# [WINDOWS] Als Administrator in CMD:
D:\Tools\HP-BCU\extracted\BiosConfigUtility64.exe /set:"D:\Tools\HP-BCU\step2_enable_vtx.txt"
# Danach Neustart
```

---

## Cursor / VS Code in Machine

Extension installieren: `Remote - WSL` (Microsoft) in Cursor/VS Code.

```bash
# Option A — von innerhalb der Machine:
podman machine ssh
cd ~/projects/meinprojekt
cursor .        # oeffnet Cursor direkt im Linux-Dateisystem

# Option B — von Windows:
# Ctrl+Shift+P -> "WSL: Connect to WSL using Distro"
# -> podman-machine-default auswaehlen
# -> Ordner oeffnen -> /home/user/projects/meinprojekt
```

Terminal in Cursor zeigt dann direkt die Machine-Shell.
Dateien bearbeiten, Terminal, Git — alles nahtlos ohne manuelles SSH.
