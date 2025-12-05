
# Gemini Workspace Analysis

This document provides a comprehensive overview of the projects and development conventions within this workspace. It is intended to be used as a guide for developers and AI agents to understand the codebase and contribute effectively.

## Project Overview

This workspace contains a project for managing a local Debian/Ubuntu package mirror. It uses `apt-mirror` to mirror remote repositories and `nginx` to serve the packages over HTTP. The entire setup is containerized using Docker and managed with Docker Compose.

The `mirror.list` file defines the repositories to be mirrored, which include:

*   Ubuntu (Noble Numbat)
*   KDE Neon
*   LibreOffice Fresh PPA
*   XFCE Desktop PPA

The project includes a set of shell scripts for automating the mirroring process, including updating the mirror, signing the repository, and generating an index page.

## Building and Running

The following commands are used to build, run, and test the project. These commands are based on the `AGENTS.md` file and the project-specific configurations.

*   **Build the Docker image:**
    ```bash
    docker compose build apt-mirror
    ```
*   **Start the services:**
    ```bash
    docker compose up -d
    ```
*   **Validate the NGINX configuration:**
    ```bash
    docker compose exec nginx nginx -t
    ```
*   **Run the mirror update process:**
    ```bash
    ./update-mirror.sh
    ```
*   **View the logs:**
    ```bash
    docker compose logs --tail=200 nginx
    ```

## Development Conventions

The following development conventions are used in this project:

*   **Shell Scripting:** Scripts are written in Bash and use `set -euo pipefail` for robustness. Functions are named in `snake_case` and scripts are named in `kebab-case.sh`.
*   **Configuration:** NGINX configuration is kept minimal and environment-agnostic, with one concern per file under the `conf.d/` directory.
*   **Commits:** Commits should follow the Conventional Commits specification (e.g., `feat:`, `fix:`, `chore:`).
*   **Pull Requests:** Pull requests should have a concise description, be linked to an issue, and include before/after notes for configuration changes.
*   **Security:** Private keys should not be committed to the repository. TLS certificates and GPG keyrings should be mounted as volumes.
*   **Mirroring Schedule:** The `apt-mirror` service is configured to update the mirror daily at 3 AM via a cron job.
*   **Ports:** The NGINX service exposes ports `8080`, `8443`, and `9000`.
*   **CORS:** NGINX is configured to handle CORS for `ailinux.me` and its subdomains, including the `/health` endpoint.

