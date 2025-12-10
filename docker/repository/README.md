# 🗂️ AILinux Repository

**Status: Early Alpha**

Lokales APT Repository für AILinux Pakete.

## Funktionen

- **Custom Packages**: Eigene .deb Pakete (ailinux-project, nova-ai, etc.)
- **APT Mirror** (optional): Ubuntu/Debian Mirror für Offline-Installationen

## Verwendung

```bash
# Repository starten
docker compose up -d

# Mit APT Mirror (braucht ~500GB+ Speicher!)
docker compose --profile mirror up -d
```

## Repository hinzufügen (Client)

```bash
curl -fsSL "https://repo.ailinux.me:8443/mirror/add-ailinux-repo.sh" | sudo bash
```

## Paket erstellen

```bash
cd ~/ailinux-project/packaging
./build-deb.sh
# Dann nach repository/data/pool/ kopieren
reprepro -b ./data includedeb noble ../packaging/*.deb
```
