#!/usr/bin/env bash
# ============================================================================
# AILinux Mirror Index Generator v3.0
# ============================================================================
# Generates a dynamic, searchable index.html for the mirror directory
#
# Environment Variables:
#   HOST_REPO_PATH  - Path to repo directory (default: ./repo)
#   BASE_URL        - Public base URL (default: https://repo.ailinux.me)
#   PUBLIC_PATH     - Public path segment (default: mirror)
# ============================================================================

if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
HOST_REPO_PATH="${HOST_REPO_PATH:-$SCRIPT_DIR/repo}"
HOST_MIRROR_PATH="$HOST_REPO_PATH/mirror"
INDEX_FILE_ON_MIRROR="$HOST_MIRROR_PATH/index.html"

BASE_URL="${BASE_URL:-https://repo.ailinux.me}"
BASE_URL="${BASE_URL%/}"
PUBLIC_PATH="${PUBLIC_PATH:-mirror}"
PUBLIC_PATH="${PUBLIC_PATH#/}"
PUBLIC_PATH="${PUBLIC_PATH%/}"

if [[ -n "$PUBLIC_PATH" ]]; then
  PUBLIC_BASE="$BASE_URL/$PUBLIC_PATH"
else
  PUBLIC_BASE="$BASE_URL"
fi
PUBLIC_BASE="${PUBLIC_BASE%/}"

mkdir -p "$HOST_MIRROR_PATH"

# Gather repository information
declare -A REPO_CATEGORIES
declare -A REPO_DESCRIPTIONS

# Define categories and descriptions
REPO_CATEGORIES=(
  ["archive.ubuntu.com"]="ubuntu"
  ["security.ubuntu.com"]="ubuntu"
  ["archive.neon.kde.org"]="desktop"
  ["ppa.launchpadcontent.net"]="ppa"
  ["dl.google.com"]="gaming"
  ["dl.winehq.org"]="gaming"
  ["repo.steampowered.com"]="gaming"
  ["download.docker.com"]="dev"
  ["deb.nodesource.com"]="dev"
  ["packages.microsoft.com"]="dev"
  ["cli.github.com"]="dev"
  ["download.sublimetext.com"]="dev"
  ["pkgs.k8s.io"]="dev"
  ["apt.releases.hashicorp.com"]="dev"
  ["developer.download.nvidia.com"]="drivers"
  ["nvidia.github.io"]="ai"
  ["apt.repos.intel.com"]="ai"
  ["updates.signal.org"]="desktop"
)

REPO_DESCRIPTIONS=(
  ["archive.ubuntu.com"]="Ubuntu Main Repository"
  ["security.ubuntu.com"]="Ubuntu Security Updates"
  ["archive.neon.kde.org"]="KDE Neon"
  ["dl.google.com"]="Google Chrome"
  ["dl.winehq.org"]="WineHQ"
  ["repo.steampowered.com"]="Steam"
  ["download.docker.com"]="Docker CE"
  ["deb.nodesource.com"]="Node.js"
  ["packages.microsoft.com"]="Microsoft VS Code"
  ["cli.github.com"]="GitHub CLI"
  ["download.sublimetext.com"]="Sublime Text"
  ["pkgs.k8s.io"]="Kubernetes"
  ["apt.releases.hashicorp.com"]="HashiCorp Tools"
  ["developer.download.nvidia.com"]="NVIDIA CUDA"
  ["nvidia.github.io"]="NVIDIA Container Toolkit"
  ["apt.repos.intel.com"]="Intel oneAPI"
  ["updates.signal.org"]="Signal Desktop"
  ["ppa.launchpadcontent.net"]="Ubuntu PPAs"
)

# Count directories and calculate size
REPO_COUNT=0
TOTAL_SIZE="0"
declare -a UBUNTU_REPOS=()
declare -a GAMING_REPOS=()
declare -a DEV_REPOS=()
declare -a DRIVERS_REPOS=()
declare -a AI_REPOS=()
declare -a DESKTOP_REPOS=()
declare -a PPA_REPOS=()
declare -a OTHER_REPOS=()

while IFS= read -r -d '' dir; do
  name=$(basename "$dir")
  [[ "$name" == "index.html" ]] && continue
  [[ -d "$dir" ]] || continue

  ((REPO_COUNT++)) || true

  # Categorize
  category="other"
  for pattern in "${!REPO_CATEGORIES[@]}"; do
    if [[ "$name" == *"$pattern"* ]]; then
      category="${REPO_CATEGORIES[$pattern]}"
      break
    fi
  done

  case "$category" in
    ubuntu)  UBUNTU_REPOS+=("$name") ;;
    gaming)  GAMING_REPOS+=("$name") ;;
    dev)     DEV_REPOS+=("$name") ;;
    drivers) DRIVERS_REPOS+=("$name") ;;
    ai)      AI_REPOS+=("$name") ;;
    desktop) DESKTOP_REPOS+=("$name") ;;
    ppa)     PPA_REPOS+=("$name") ;;
    *)       OTHER_REPOS+=("$name") ;;
  esac
done < <(find "$HOST_MIRROR_PATH" -maxdepth 1 -mindepth 1 -type d -print0 | sort -z)

# Calculate approximate size
if command -v du >/dev/null 2>&1; then
  TOTAL_SIZE=$(du -sh "$HOST_MIRROR_PATH" 2>/dev/null | cut -f1 || echo "N/A")
fi

GENERATED_DATE=$(date '+%Y-%m-%d %H:%M:%S')
GENERATED_YEAR=$(date +%Y)

TMP_INDEX_FILE="$(mktemp)"
trap 'rm -f "$TMP_INDEX_FILE"' EXIT

# Generate HTML
cat > "$TMP_INDEX_FILE" << 'HTMLHEAD'
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>AILinux Mirror - APT Repository</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="AILinux APT Mirror - Ubuntu, Gaming, Development und AI Pakete">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📦</text></svg>">
<style>
:root {
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  --bg-tertiary: #21262d;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --accent-cyan: #58a6ff;
  --accent-green: #3fb950;
  --accent-orange: #d29922;
  --accent-purple: #a371f7;
  --accent-red: #f85149;
  --border-color: #30363d;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  line-height: 1.6;
  min-height: 100vh;
}

.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

header {
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
  border-bottom: 1px solid var(--border-color);
  padding: 30px 20px;
  margin-bottom: 30px;
}

header h1 {
  font-size: 2rem;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}

header p { color: var(--text-secondary); }

.stats-bar {
  display: flex;
  gap: 30px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.stat {
  background: var(--bg-primary);
  padding: 12px 20px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.stat-value { font-size: 1.5rem; font-weight: 600; color: var(--accent-cyan); }
.stat-label { font-size: 0.85rem; color: var(--text-secondary); }

.search-box {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 25px;
}

.search-box input {
  width: 100%;
  padding: 12px 16px;
  font-size: 1rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  outline: none;
}

.search-box input:focus { border-color: var(--accent-cyan); }
.search-box input::placeholder { color: var(--text-secondary); }

.quick-start {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 25px;
}

.quick-start h2 {
  font-size: 1.1rem;
  margin-bottom: 15px;
  color: var(--accent-green);
  display: flex;
  align-items: center;
  gap: 8px;
}

.code-block {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 15px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9rem;
  overflow-x: auto;
  position: relative;
}

.code-block code { color: var(--accent-cyan); }

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
}

.copy-btn:hover { background: var(--border-color); color: var(--text-primary); }

.category {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 15px;
  overflow: hidden;
}

.category-header {
  padding: 15px 20px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  transition: background 0.2s;
}

.category-header:hover { background: var(--bg-tertiary); }

.category-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.category-count {
  background: var(--bg-tertiary);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.category-icon { font-size: 1.3rem; }
.category-arrow { transition: transform 0.2s; color: var(--text-secondary); }
.category.open .category-arrow { transform: rotate(90deg); }

.category-content {
  display: none;
  border-top: 1px solid var(--border-color);
  padding: 15px 20px;
}

.category.open .category-content { display: block; }

.repo-list { list-style: none; }

.repo-item {
  padding: 10px 15px;
  border-radius: 6px;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: background 0.2s;
}

.repo-item:hover { background: var(--bg-tertiary); }

.repo-item a {
  color: var(--accent-cyan);
  text-decoration: none;
  font-family: monospace;
}

.repo-item a:hover { text-decoration: underline; }

.repo-item .icon { font-size: 1.2rem; }

.repo-desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-left: auto;
}

.tools-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 25px;
}

.tool-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 15px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: border-color 0.2s;
}

.tool-card:hover { border-color: var(--accent-cyan); }

.tool-card a {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
}

.tool-card .icon { font-size: 1.5rem; }
.tool-card .desc { font-size: 0.8rem; color: var(--text-secondary); }

footer {
  text-align: center;
  padding: 30px 20px;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-color);
  margin-top: 40px;
}

footer a { color: var(--accent-cyan); text-decoration: none; }
footer a:hover { text-decoration: underline; }

.hidden { display: none !important; }

@media (max-width: 768px) {
  .stats-bar { flex-direction: column; gap: 10px; }
  .stat { text-align: center; }
  header h1 { font-size: 1.5rem; }
}
</style>
</head>
<body>
HTMLHEAD

# Continue with dynamic content
cat >> "$TMP_INDEX_FILE" << HTMLHEADER
<header>
  <div class="container">
    <h1><span>📦</span> AILinux Mirror</h1>
    <p>APT Package Repository - Ubuntu, Gaming, Development &amp; AI</p>
    <div class="stats-bar">
      <div class="stat">
        <div class="stat-value">${REPO_COUNT}</div>
        <div class="stat-label">Repositories</div>
      </div>
      <div class="stat">
        <div class="stat-value">${TOTAL_SIZE}</div>
        <div class="stat-label">Mirror Size</div>
      </div>
      <div class="stat">
        <div class="stat-value">${GENERATED_DATE}</div>
        <div class="stat-label">Last Update</div>
      </div>
    </div>
  </div>
</header>

<main class="container">
  <div class="search-box">
    <input type="text" id="searchInput" placeholder="🔍 Repository suchen... (z.B. ubuntu, docker, wine)" onkeyup="filterRepos()">
  </div>

  <div class="quick-start">
    <h2><span>⚡</span> Quick Install</h2>
    <div class="code-block">
      <button class="copy-btn" onclick="copyCode(this)">Copy</button>
      <code>curl -fsSL "${PUBLIC_BASE}/add-ailinux-repo.sh" | sudo bash</code>
    </div>
  </div>

  <div class="tools-section">
    <div class="tool-card">
      <span class="icon">🔐</span>
      <div>
        <a href="${PUBLIC_BASE}/ailinux-archive-key.gpg">GPG Key</a>
        <div class="desc">Repository Signing Key</div>
      </div>
    </div>
    <div class="tool-card">
      <span class="icon">⚙️</span>
      <div>
        <a href="${PUBLIC_BASE}/add-ailinux-repo.sh">Install Script</a>
        <div class="desc">Automatisches Setup</div>
      </div>
    </div>
    <div class="tool-card">
      <span class="icon">📊</span>
      <div>
        <a href="${PUBLIC_BASE}/mirror-summary.html">Status</a>
        <div class="desc">Mirror Health Report</div>
      </div>
    </div>
    <div class="tool-card">
      <span class="icon">📜</span>
      <div>
        <a href="${PUBLIC_BASE}/live-log.html">Logs</a>
        <div class="desc">Sync Protokoll</div>
      </div>
    </div>
  </div>

  <div id="repoCategories">
HTMLHEADER

# Function to output category
output_category() {
  local cat_id="$1"
  local cat_icon="$2"
  local cat_name="$3"
  local cat_color="$4"
  shift 4
  local repos=("$@")

  [[ ${#repos[@]} -eq 0 ]] && return

  cat >> "$TMP_INDEX_FILE" << CATHEAD
    <div class="category open" data-category="${cat_id}">
      <div class="category-header" onclick="toggleCategory(this)">
        <div class="category-title">
          <span class="category-icon">${cat_icon}</span>
          <span>${cat_name}</span>
          <span class="category-count">${#repos[@]}</span>
        </div>
        <span class="category-arrow">▶</span>
      </div>
      <div class="category-content">
        <ul class="repo-list">
CATHEAD

  for repo in "${repos[@]}"; do
    local desc=""
    for pattern in "${!REPO_DESCRIPTIONS[@]}"; do
      if [[ "$repo" == *"$pattern"* ]]; then
        desc="${REPO_DESCRIPTIONS[$pattern]}"
        break
      fi
    done
    cat >> "$TMP_INDEX_FILE" << REPOITEM
          <li class="repo-item" data-name="${repo}">
            <span class="icon">📁</span>
            <a href="${PUBLIC_BASE}/${repo}/">${repo}/</a>
            <span class="repo-desc">${desc}</span>
          </li>
REPOITEM
  done

  cat >> "$TMP_INDEX_FILE" << CATFOOT
        </ul>
      </div>
    </div>
CATFOOT
}

# Output all categories
output_category "ubuntu" "🐧" "Ubuntu & Security" "orange" "${UBUNTU_REPOS[@]}"
output_category "gaming" "🎮" "Gaming & Multimedia" "purple" "${GAMING_REPOS[@]}"
output_category "dev" "💻" "Development Tools" "cyan" "${DEV_REPOS[@]}"
output_category "drivers" "🔧" "Drivers" "green" "${DRIVERS_REPOS[@]}"
output_category "ai" "🤖" "AI & Machine Learning" "red" "${AI_REPOS[@]}"
output_category "desktop" "🖥️" "Desktop Applications" "blue" "${DESKTOP_REPOS[@]}"
output_category "ppa" "📦" "Ubuntu PPAs" "yellow" "${PPA_REPOS[@]}"
output_category "other" "📂" "Other" "gray" "${OTHER_REPOS[@]}"

# Footer and scripts
cat >> "$TMP_INDEX_FILE" << HTMLFOOTER
  </div>
</main>

<footer>
  <p>AILinux Repository &copy; ${GENERATED_YEAR} - <a href="https://ailinux.me">ailinux.me</a></p>
  <p style="margin-top: 8px; font-size: 0.8rem;">
    Base URL: <code>${PUBLIC_BASE}</code>
  </p>
</footer>

<script>
function toggleCategory(header) {
  header.parentElement.classList.toggle('open');
}

function filterRepos() {
  const query = document.getElementById('searchInput').value.toLowerCase();
  const items = document.querySelectorAll('.repo-item');
  const categories = document.querySelectorAll('.category');

  items.forEach(item => {
    const name = item.dataset.name.toLowerCase();
    const desc = item.querySelector('.repo-desc')?.textContent.toLowerCase() || '';
    const match = name.includes(query) || desc.includes(query);
    item.classList.toggle('hidden', !match && query.length > 0);
  });

  // Hide empty categories
  categories.forEach(cat => {
    const visibleItems = cat.querySelectorAll('.repo-item:not(.hidden)');
    cat.classList.toggle('hidden', visibleItems.length === 0 && query.length > 0);
    if (query.length > 0 && visibleItems.length > 0) {
      cat.classList.add('open');
    }
  });
}

function copyCode(btn) {
  const code = btn.parentElement.querySelector('code').textContent;
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

// Open all categories by default
document.querySelectorAll('.category').forEach(c => c.classList.add('open'));
</script>
</body>
</html>
HTMLFOOTER

# Deploy index files
declare -a INDEX_TARGETS
INDEX_TARGETS+=("$INDEX_FILE_ON_MIRROR")

if [[ "${WRITE_ROOT_INDEX:-1}" == "1" ]]; then
  INDEX_TARGETS+=("$HOST_REPO_PATH/index.html")
fi

if [[ -n "${EXTRA_INDEX_TARGETS:-}" ]]; then
  while IFS= read -r extra_target; do
    [[ -n "$extra_target" ]] || continue
    INDEX_TARGETS+=("$extra_target")
  done <<< "${EXTRA_INDEX_TARGETS}"
fi

declare -A GENERATED
for target in "${INDEX_TARGETS[@]}"; do
  [[ -n "$target" ]] || continue
  if [[ -n "${GENERATED[$target]+x}" ]]; then
    continue
  fi
  GENERATED["$target"]=1
  mkdir -p "$(dirname "$target")"
  cp "$TMP_INDEX_FILE" "$target"
  chmod 644 "$target"
  echo "[generate-index] $target erfolgreich erstellt."
done

echo "[generate-index] ${REPO_COUNT} Repositories katalogisiert, Gesamtgröße: ${TOTAL_SIZE}"
