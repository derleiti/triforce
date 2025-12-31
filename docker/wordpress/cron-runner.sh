#!/bin/sh
# WordPress Cron Runner
# Runs WP-Cron every minute using WP-CLI

echo "WordPress Cron Runner started"

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running wp-cron..."

    # Run WP-Cron via WP-CLI
    cd /var/www/html && wp cron event run --due-now --allow-root 2>&1 | head -n 10

    # Wait 60 seconds before next run
    sleep 60
done
