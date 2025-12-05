FROM debian:stable-slim

# Enable i386 architecture
RUN dpkg --add-architecture i386 && \
    apt-get update && apt-get install -y \
        apt-mirror \
        cron \
        wget \
        curl \
        gnupg \
        apt-utils \
        dpkg-dev \
        ca-certificates \
        pv \
        progress \
        procps && \
    rm -rf /var/lib/apt/lists/*

# Mirror directories
RUN mkdir -p /var/spool/apt-mirror /repo /usr/share/keyrings

# Mirror config + scripts
COPY mirror.list /etc/apt/mirror.list
COPY update-mirror.sh /usr/local/bin/update-mirror.sh
COPY generate-index.sh /repo/generate-index.sh

RUN chmod +x /usr/local/bin/update-mirror.sh /repo/generate-index.sh

# Google Chrome key
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor > /usr/share/keyrings/google-linux-keyring.gpg

# WineHQ key
RUN curl -fsSL https://dl.winehq.org/wine-builds/winehq.key \
    | gpg --dearmor > /usr/share/keyrings/winehq-archive-keyring.gpg

# Cappelikan PPA Key — sauber importieren
# RICHTIGER COPY-PFAD ohne Slash!
COPY cappelikan-ppa.asc /tmp/cappelikan-ppa.asc

RUN gpg --import /tmp/cappelikan-ppa.asc && \
    gpg --export --output /usr/share/keyrings/launchpad-cappelikan.gpg && \
    rm /tmp/cappelikan-ppa.asc

# Cronjob
RUN echo "0 3 * * * /usr/local/bin/update-mirror.sh" > /etc/cron.d/aptmirror && \
    chmod 0644 /etc/cron.d/aptmirror && \
    crontab /etc/cron.d/aptmirror

EXPOSE 80

CMD ["cron", "-f"]
