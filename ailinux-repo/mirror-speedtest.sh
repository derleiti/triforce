#!/usr/bin/env bash
set -uo pipefail

# --- KONFIGURATION ---
MIRROR_LIST="${1:-mirror.list}"
# Wir suchen Dateien zwischen 40MB und 250MB (deckt Kernel, Chrome, etc. ab)
MIN_SIZE=$((40 * 1024 * 1024))
MAX_SIZE=$((250 * 1024 * 1024))

# Prüfen ob Datei existiert
if [[ ! -f "$MIRROR_LIST" ]]; then
    echo "❌ Datei '$MIRROR_LIST' nicht gefunden."
    exit 1
fi

# --- HILFSFUNKTIONEN ---
calc_mb() { awk "BEGIN {printf \"%.2f\", $1/1024/1024}"; }
calc_mbit() { awk "BEGIN {printf \"%.2f\", ($1*8)/1000/1000}"; }

# Sucht in der Packages.gz nach einer Datei passender Größe
discover_big_file() {
    local base_url="$1"
    local dist="$2"
    local comp="$3"
    
    # Pfad zur Index-Datei bauen
    local index_url="${base_url}/dists/${dist}/${comp}/binary-amd64/Packages.gz"
    # Doppelte Slashes bereinigen
    index_url=$(echo "$index_url" | sed 's#//#/#g' | sed 's#http:/#http://#g' | sed 's#https:/#https://#g')

    local found_file
    # Lädt den Index (max 4 Sek), entpackt live und sucht Größe
    found_file=$(curl -sL -f --max-time 4 "$index_url" | zcat 2>/dev/null | awk -v min="$MIN_SIZE" -v max="$MAX_SIZE" '
        /^Filename:/ { current_file = $2 }
        /^Size:/ { 
            if ($2 >= min && $2 <= max) {
                print current_file
                exit
            }
        }
    ')

    if [[ -n "$found_file" ]]; then
        echo "$found_file"
    else
        echo "FALLBACK"
    fi
}

perform_test() {
    local url="$1"
    # Max 12 Sekunden Download-Zeit
    curl -L -s -o /dev/null --max-time 12 -w "%{speed_download}" "$url" || echo "ERROR"
}

# --- HAUPTPROGRAMM ---

# Assoziatives Array zum Merken bereits getesteter Hosts
declare -A CHECKED_HOSTS

echo "🔎 Analysiere Mirror-Liste (Universal Discovery + Deduplizierung)..."
echo "================================================================================="
printf "%-40s | %-12s | %-12s | %s\n" "Mirror" "MB/s" "Mbit/s" "Datei-Info"
echo "---------------------------------------------------------------------------------"

TMP_RESULT=$(mktemp)

# Liste lesen, Kommentare ignorieren, Loop starten
grep -E "^\s*deb" "$MIRROR_LIST" | while read -r type url dist comp rest; do
    
    # URL bereinigen (Trailing Slash entfernen)
    url="${url%/}"
    
    # -- DEDUPLIZIERUNG --
    # Wenn URL schon im Array ist -> Überspringen
    if [[ -n "${CHECKED_HOSTS[$url]:-}" ]]; then
        continue
    fi
    # URL als "getestet" markieren
    CHECKED_HOSTS[$url]=1
    # --------------------

    # 1. Datei suchen
    file_path=$(discover_big_file "$url" "$dist" "$comp")
    
    test_url=""
    info_txt=""

    if [[ "$file_path" == "FALLBACK" ]]; then
        # Nichts Großes gefunden, wir testen den Index selbst
        test_url="${url}/dists/${dist}/${comp}/binary-amd64/Packages.gz"
        info_txt="⚠️ Index (klein)"
    else
        test_url="${url}/${file_path}"
        info_txt="✅ File gefunden"
    fi

    # URL sauber zusammensetzen
    test_url=$(echo "$test_url" | sed 's#//#/#g' | sed 's#http:/#http://#g' | sed 's#https:/#https://#g')

    # 2. Speedtest ausführen
    speed_bps=$(perform_test "$test_url")

    # 3. Ergebnis ausgeben
    if [[ "$speed_bps" == "ERROR" || "$speed_bps" == "0" ]]; then
        printf "%-40s | %-12s | %-12s | %s\n" "${url:0:40}" "0" "0" "❌ Fehler"
    else
        mbs=$(calc_mb "$speed_bps")
        mbits=$(calc_mbit "$speed_bps")
        
        printf "%-40s | %-12s | %-12s | %s\n" "${url:0:40}" "$mbs" "$mbits" "$info_txt"
        
        # In Temp-Datei schreiben für Ranking
        echo "$mbs $mbits $url" >> "$TMP_RESULT"
    fi
done

echo "---------------------------------------------------------------------------------"
echo
echo "🏆 Ranking (nach Geschwindigkeit sortiert):"
echo "-------------------------------------------"

if [[ -s "$TMP_RESULT" ]]; then
    sort -nr "$TMP_RESULT" | while read -r mbs mbits h; do
        printf "🚀 %-10s MB/s (%-8s Mbit/s) -> %s\n" "$mbs" "$mbits" "$h"
    done
else
    echo "Keine erfolgreichen Messungen."
fi

rm "$TMP_RESULT" 2>/dev/null
echo
