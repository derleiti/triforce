#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIFORCE STACK CONTROL - Start/Stop/Restart Docker Services
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -e
TRIFORCE_DIR="${TRIFORCE_DIR:-$HOME/triforce}"
cd "$TRIFORCE_DIR"

STACKS="wordpress flarum searxng mailserver repository"

usage() {
    echo "Usage: $0 {start|stop|restart|status|logs} [stack]"
    echo "Stacks: $STACKS | all"
    exit 1
}

ACTION=$1
STACK=${2:-all}

do_action() {
    local stack=$1
    local action=$2
    echo "📦 $stack: $action..."
    cd "$TRIFORCE_DIR/docker/$stack"
    case $action in
        start)   docker compose --env-file ../../.env up -d ;;
        stop)    docker compose down ;;
        restart) docker compose down && docker compose --env-file ../../.env up -d ;;
        status)  docker compose ps ;;
        logs)    docker compose logs --tail=50 ;;
    esac
    cd "$TRIFORCE_DIR"
}

case $ACTION in
    start|stop|restart|status|logs)
        if [ "$STACK" = "all" ]; then
            for s in $STACKS; do do_action "$s" "$ACTION"; done
        else
            do_action "$STACK" "$ACTION"
        fi
        ;;
    *) usage ;;
esac

echo "✅ Done!"
