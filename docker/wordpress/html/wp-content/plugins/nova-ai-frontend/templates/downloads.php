<?php
/**
 * Downloads Template v3.0 – Card UI with AI descriptions
 * Shortcode: [ailinux_downloads]
 */
defined('ABSPATH') || exit;

$service = \NovAI\Services\DownloadsService::instance();
$path    = isset($atts['path']) ? sanitize_text_field($atts['path']) : '';
$data    = $service->get_directory_contents($path);
?>
<div class="nov-dl" data-base-url="<?php echo esc_attr(home_url('/downloads')); ?>">

    <?php /* ── Breadcrumb ─────────────────────────────────────── */ ?>
    <nav class="nov-dl__crumb" aria-label="Pfad-Navigation">
        <?php foreach ($data['breadcrumb'] as $i => $crumb): ?>
            <?php if ($i > 0): ?><span class="nov-dl__crumb-sep">›</span><?php endif; ?>
            <?php if ($i === count($data['breadcrumb']) - 1): ?>
                <span class="nov-dl__crumb-cur"><?php echo esc_html($crumb['name']); ?></span>
            <?php else: ?>
                <a class="nov-dl__crumb-link" href="#"
                   data-path="<?php echo esc_attr($crumb['path']); ?>"><?php echo esc_html($crumb['name']); ?></a>
            <?php endif; ?>
        <?php endforeach; ?>
    </nav>

    <?php /* ── File grid ─────────────────────────────────────── */ ?>
    <?php if (empty($data['files'])): ?>
        <div class="nov-dl__empty">
            <span class="nov-dl__empty-icon">📂</span>
            <p>Dieser Ordner ist leer.</p>
        </div>
    <?php else: ?>
        <div class="nov-dl__grid">
            <?php foreach ($data['files'] as $file): ?>
                <div class="nov-dl__card <?php echo $file['type'] === 'folder' ? 'is-folder' : 'is-file'; ?>"
                     data-path="<?php echo esc_attr($file['path']); ?>">

                    <div class="nov-dl__card-icon"><?php echo $file['icon']; ?></div>

                    <div class="nov-dl__card-body">
                        <div class="nov-dl__card-name">
                            <?php if ($file['type'] === 'folder'): ?>
                                <button class="nov-dl__folder-btn" data-path="<?php echo esc_attr($file['path']); ?>">
                                    <?php echo esc_html($file['name']); ?>
                                </button>
                            <?php else: ?>
                                <span><?php echo esc_html($file['name']); ?></span>
                            <?php endif; ?>
                        </div>

                        <?php if (!empty($file['description'])): ?>
                            <p class="nov-dl__card-desc">
                                <span class="nov-dl__ai-badge" title="KI-Beschreibung">✦ KI</span>
                                <?php echo esc_html($file['description']); ?>
                            </p>
                        <?php endif; ?>

                        <div class="nov-dl__card-meta">
                            <span class="nov-dl__size"><?php echo esc_html($file['size']); ?></span>
                            <span class="nov-dl__date"><?php echo esc_html($file['modified']); ?></span>
                        </div>
                    </div>

                    <div class="nov-dl__card-action">
                        <?php if ($file['type'] === 'folder'): ?>
                            <button class="nov-dl__btn nov-dl__btn--open" data-path="<?php echo esc_attr($file['path']); ?>"
                                    title="Ordner öffnen">›</button>
                        <?php else: ?>
                            <a class="nov-dl__btn nov-dl__btn--dl"
                               href="<?php echo esc_url($file['url']); ?>"
                               download title="Herunterladen">↓</a>
                        <?php endif; ?>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>
    <?php endif; ?>
</div>

<style>
.nov-dl {
    font-family: var(--font-sans, system-ui, sans-serif);
    color: var(--text, #e8edf2);
    width: 100%;
}

/* Breadcrumb */
.nov-dl__crumb {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-bottom: 20px;
    font-size: 0.9rem;
    color: var(--muted, #a9b3c0);
}
.nov-dl__crumb-link {
    color: var(--accent-active, #3aa0ff);
    text-decoration: none;
    transition: opacity 0.15s;
}
.nov-dl__crumb-link:hover { opacity: 0.75; }
.nov-dl__crumb-cur { font-weight: 600; color: var(--text, #e8edf2); }
.nov-dl__crumb-sep { opacity: 0.4; }

/* Empty state */
.nov-dl__empty {
    text-align: center;
    padding: 48px 24px;
    color: var(--muted, #a9b3c0);
}
.nov-dl__empty-icon { font-size: 3rem; display: block; margin-bottom: 12px; }

/* Grid */
.nov-dl__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
}

/* Card */
.nov-dl__card {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    background: var(--bg-1, #131822);
    border: 1px solid var(--line, #263040);
    border-radius: 12px;
    padding: 16px;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
    cursor: default;
}
.nov-dl__card:hover {
    border-color: var(--accent-active, #3aa0ff);
    box-shadow: 0 4px 20px rgba(58, 160, 255, 0.15);
    transform: translateY(-1px);
}
.nov-dl__card.is-folder { cursor: pointer; }

/* Icon */
.nov-dl__card-icon {
    font-size: 2rem;
    line-height: 1;
    flex-shrink: 0;
    margin-top: 2px;
}

/* Body */
.nov-dl__card-body {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.nov-dl__card-name {
    font-weight: 600;
    font-size: 0.95rem;
    word-break: break-word;
}
.nov-dl__folder-btn {
    background: none;
    border: none;
    padding: 0;
    color: var(--text, #e8edf2);
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
}
.nov-dl__folder-btn:hover { color: var(--accent-active, #3aa0ff); }

/* AI description */
.nov-dl__card-desc {
    font-size: 0.82rem;
    color: var(--muted, #a9b3c0);
    margin: 0;
    line-height: 1.45;
    max-width: 100%;
}
.nov-dl__ai-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--accent-active, #3aa0ff);
    border: 1px solid currentColor;
    border-radius: 4px;
    padding: 1px 4px;
    margin-right: 5px;
    vertical-align: middle;
    opacity: 0.8;
    white-space: nowrap;
}

/* Meta */
.nov-dl__card-meta {
    display: flex;
    gap: 10px;
    font-size: 0.78rem;
    color: var(--muted, #a9b3c0);
    opacity: 0.7;
}

/* Action button */
.nov-dl__card-action {
    flex-shrink: 0;
    display: flex;
    align-items: center;
}
.nov-dl__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    font-size: 1.1rem;
    font-weight: 700;
    text-decoration: none;
    transition: background 0.15s, color 0.15s;
    border: 1px solid var(--line, #263040);
    background: var(--bg-2, #1b2330);
    color: var(--text, #e8edf2);
    cursor: pointer;
    font-family: inherit;
}
.nov-dl__btn--dl { color: var(--accent-active, #3aa0ff); }
.nov-dl__btn:hover {
    background: var(--accent-active, #3aa0ff);
    color: #0e1116;
    border-color: var(--accent-active, #3aa0ff);
}

/* Light mode overrides */
html[data-theme='light'] .nov-dl__card {
    background: #fff;
    border-color: #d7dee9;
}
html[data-theme='light'] .nov-dl__btn {
    background: #f0f4ff;
    border-color: #d7dee9;
    color: #0f141b;
}

/* Responsive */
@media (max-width: 600px) {
    .nov-dl__grid {
        grid-template-columns: 1fr;
    }
    .nov-dl__card-icon { font-size: 1.6rem; }
}
</style>

<script>
(function(){
    function novaDlInit(root) {
        var base = root.dataset.baseUrl || '';

        function loadPath(path) {
            root.classList.add('nov-dl--loading');
            var fd = new FormData();
            fd.append('action', 'nov_ai_browse');
            fd.append('path', path);

            fetch('/wp-admin/admin-ajax.php', {method:'POST', body: fd})
                .then(function(r){ return r.json(); })
                .then(function(r){
                    if (!r.success) return;
                    renderFiles(r.data);
                })
                .finally(function(){ root.classList.remove('nov-dl--loading'); });
        }

        function renderFiles(data) {
            // Re-render breadcrumb
            var crumb = root.querySelector('.nov-dl__crumb');
            if (crumb) {
                crumb.innerHTML = data.breadcrumb.map(function(c, i){
                    var sep = i > 0 ? '<span class="nov-dl__crumb-sep">›</span>' : '';
                    if (i === data.breadcrumb.length - 1) {
                        return sep + '<span class="nov-dl__crumb-cur">' + escHtml(c.name) + '</span>';
                    }
                    return sep + '<a class="nov-dl__crumb-link" href="#" data-path="' + escHtml(c.path) + '">' + escHtml(c.name) + '</a>';
                }).join('');
                bindCrumb(crumb);
            }

            // Re-render grid
            var container = root.querySelector('.nov-dl__grid, .nov-dl__empty');
            if (!container) return;
            var parent = container.parentNode;

            if (!data.files || data.files.length === 0) {
                parent.innerHTML += '<div class="nov-dl__empty"><span class="nov-dl__empty-icon">📂</span><p>Dieser Ordner ist leer.</p></div>';
                if (container.classList) container.remove();
                return;
            }

            var html = '<div class="nov-dl__grid">';
            data.files.forEach(function(f){
                var isFolder = f.type === 'folder';
                var desc = f.description
                    ? '<p class="nov-dl__card-desc"><span class="nov-dl__ai-badge" title="KI-Beschreibung">✦ KI</span>' + escHtml(f.description) + '</p>'
                    : '';
                var nameHtml = isFolder
                    ? '<button class="nov-dl__folder-btn" data-path="' + escHtml(f.path) + '">' + escHtml(f.name) + '</button>'
                    : '<span>' + escHtml(f.name) + '</span>';
                var action = isFolder
                    ? '<button class="nov-dl__btn nov-dl__btn--open" data-path="' + escHtml(f.path) + '" title="Öffnen">›</button>'
                    : '<a class="nov-dl__btn nov-dl__btn--dl" href="' + escHtml(f.url) + '" download title="Herunterladen">↓</a>';

                html += '<div class="nov-dl__card ' + (isFolder ? 'is-folder' : 'is-file') + '" data-path="' + escHtml(f.path) + '">'
                    + '<div class="nov-dl__card-icon">' + f.icon + '</div>'
                    + '<div class="nov-dl__card-body">'
                    + '<div class="nov-dl__card-name">' + nameHtml + '</div>'
                    + desc
                    + '<div class="nov-dl__card-meta"><span class="nov-dl__size">' + escHtml(f.size) + '</span><span class="nov-dl__date">' + escHtml(f.modified) + '</span></div>'
                    + '</div>'
                    + '<div class="nov-dl__card-action">' + action + '</div>'
                    + '</div>';
            });
            html += '</div>';

            container.outerHTML = html;
            bindGrid(root);
        }

        function bindCrumb(crumb) {
            crumb.querySelectorAll('.nov-dl__crumb-link').forEach(function(a){
                a.addEventListener('click', function(e){
                    e.preventDefault();
                    loadPath(a.dataset.path || '');
                });
            });
        }

        function bindGrid(root) {
            root.querySelectorAll('.nov-dl__folder-btn, .nov-dl__btn--open').forEach(function(btn){
                btn.addEventListener('click', function(e){
                    e.stopPropagation();
                    loadPath(btn.dataset.path || '');
                });
            });
            root.querySelectorAll('.nov-dl__card.is-folder').forEach(function(card){
                card.addEventListener('click', function(){
                    loadPath(card.dataset.path || '');
                });
            });
        }

        function escHtml(s) {
            return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        bindCrumb(root);
        bindGrid(root);
    }

    document.querySelectorAll('.nov-dl').forEach(novaDlInit);
})();
</script>
