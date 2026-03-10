<?php
/**
 * Plugin Name: Nova AI Frontend
 * Description: AILinux AI Playground & Downloads — Chat, Vision, Media Generation
 * Version: 6.2.0
 * Author: zombie@ailinux
 * Text Domain: nova-ai-frontend
 */

defined('ABSPATH') || exit;

define('NOVA_AI_BACKEND', 'http://172.18.0.1:9000');
define('NOVA_AI_VERSION', '6.2.0');
define('NOVA_AI_PLUGIN_URL', plugin_dir_url(__FILE__));

/* ─── REST API Proxy ──────────────────────────────────────────────────────── */

add_action('rest_api_init', function () {
    $ns = 'nova-ai/v1';
    register_rest_route($ns, '/health',  ['methods'=>'GET',  'callback'=>'nova_proxy_health',  'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/models',  ['methods'=>'GET',  'callback'=>'nova_proxy_models',  'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/chat',    ['methods'=>'POST', 'callback'=>'nova_proxy_chat',    'permission_callback'=>'is_user_logged_in']);
    register_rest_route($ns, '/vision',  ['methods'=>'POST', 'callback'=>'nova_proxy_vision',  'permission_callback'=>'is_user_logged_in']);
    register_rest_route($ns, '/media/image', ['methods'=>'POST','callback'=>'nova_proxy_image','permission_callback'=>'is_user_logged_in']);
    register_rest_route($ns, '/media/video', ['methods'=>'POST','callback'=>'nova_proxy_video','permission_callback'=>'is_user_logged_in']);
    register_rest_route($ns, '/media/video/status/(?P<job_id>[a-zA-Z0-9_\-]+)', ['methods'=>'GET','callback'=>'nova_proxy_video_status','permission_callback'=>'is_user_logged_in']);
    register_rest_route($ns, '/nonce', ['methods'=>'GET', 'callback'=>function(){
        if (!is_user_logged_in()) return new WP_REST_Response(['ok'=>false,'error'=>'not_logged_in'],401);
        return new WP_REST_Response(['ok'=>true,'nonce'=>wp_create_nonce('wp_rest')],200,
            ['Cache-Control'=>'no-store,no-cache,max-age=0','Pragma'=>'no-cache']);
    }, 'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/article-chat', ['methods'=>'POST', 'callback'=>'nova_proxy_article_chat',    'permission_callback'=>'__return_true']);
});

function nova_proxy(string $path, string $method='GET', ?array $body=null): WP_REST_Response {
    $args = ['method'=>$method,'timeout'=>90,'headers'=>['Content-Type'=>'application/json']];
    if ($body !== null) $args['body'] = wp_json_encode($body);
    $response = wp_remote_request(NOVA_AI_BACKEND.$path, $args);
    if (is_wp_error($response)) return new WP_REST_Response(['error'=>$response->get_error_message()], 502);
    $code = wp_remote_retrieve_response_code($response);
    $data = json_decode(wp_remote_retrieve_body($response), true) ?? ['raw'=>wp_remote_retrieve_body($response)];
    if ($code >= 400 && !isset($data['message'])) $data['message'] = $data['detail'] ?? $data['error'] ?? "Backend HTTP $code";
    return new WP_REST_Response($data, $code);
}

function nova_proxy_health(WP_REST_Request $r): WP_REST_Response  { return nova_proxy('/v1/frontend/dashboard/health'); }
function nova_proxy_models(WP_REST_Request $r): WP_REST_Response  { return nova_proxy('/v1/frontend/dashboard/models'); }
function nova_proxy_chat(WP_REST_Request $r): WP_REST_Response    { return nova_proxy('/v1/frontend/dashboard/chat',  'POST', $r->get_json_params()); }
function nova_proxy_vision(WP_REST_Request $r): WP_REST_Response  { return nova_proxy('/v1/frontend/dashboard/vision','POST', $r->get_json_params()); }
function nova_proxy_image(WP_REST_Request $r): WP_REST_Response   { return nova_proxy('/v1/frontend/dashboard/media/image','POST',$r->get_json_params()); }
function nova_proxy_video(WP_REST_Request $r): WP_REST_Response   { return nova_proxy('/v1/frontend/dashboard/media/video','POST',$r->get_json_params()); }
function nova_proxy_video_status(WP_REST_Request $r): WP_REST_Response { return nova_proxy('/v1/frontend/dashboard/media/video/status/'.$r['job_id']); }

/* ─── Assets ──────────────────────────────────────────────────────────────── */

add_action('wp_enqueue_scripts', function () {
    $url = NOVA_AI_PLUGIN_URL.'assets/';
    $ver = NOVA_AI_VERSION;
    wp_enqueue_style('nova-ai-frontend', $url.'nova-ai.css', [], $ver);
    wp_enqueue_script('nova-ai-frontend', $url.'nova-ai.js', [], $ver, true);
    wp_localize_script('nova-ai-frontend', 'novaAiConfig', [
        'apiBase'    => rest_url('nova-ai/v1'),
        'nonce'      => wp_create_nonce('wp_rest'),
        'nonceUrl'   => rest_url('nova-ai/v1/nonce'),
        'autoTheme'  => true,
        'version'    => $ver,
        'isLoggedIn' => is_user_logged_in() ? 'true' : 'false',
    ]);
});


/* ─── Article Chat Proxy ──────────────────────────────────── */
function nova_proxy_article_chat(WP_REST_Request $r): WP_REST_Response {
    $params  = $r->get_json_params();
    $context = sanitize_textarea_field($params['context'] ?? '');
    $model   = sanitize_text_field($params['model']   ?? 'groq/meta-llama/llama-4-scout-17b-16e-instruct');
    $message = sanitize_textarea_field($params['message'] ?? '');
    $history = $params['history'] ?? [];

    // Build messages with article context as system prompt
    $messages = [
        ['role'=>'system','content'=>
            "Du bist ein hilfreicher KI-Assistent der die Nutzer beim Verstehen und Diskutieren von Artikeln und Inhalten unterstützt.\n\n" .
            "ARTIKEL-KONTEXT:\n" . $context . "\n\n" .
            "Beantworte Fragen auf Basis dieses Kontexts. Bei Fragen die nicht im Kontext stehen, nutze dein allgemeines Wissen und weise darauf hin."]
    ];
    foreach ((array)$history as $h) {
        if (isset($h['role'],$h['content'])) {
            $messages[] = ['role'=>sanitize_text_field($h['role']),'content'=>sanitize_textarea_field($h['content'])];
        }
    }
    $messages[] = ['role'=>'user','content'=>$message];

    $body = json_encode(['model'=>$model,'messages'=>$messages,'stream'=>false,'max_tokens'=>800]);
    $resp = wp_remote_post(NOVA_AI_BACKEND.'/v1/frontend/dashboard/chat',
        ['body'=>$body,'headers'=>['Content-Type'=>'application/json'],'timeout'=>30]);
    if (is_wp_error($resp)) return new WP_REST_Response(['error'=>$resp->get_error_message()],502);
    $data = json_decode(wp_remote_retrieve_body($resp), true);
    $code = wp_remote_retrieve_response_code($resp);
    return new WP_REST_Response($data, $code);
}

/* ─── Shortcode: AI Playground ────────────────────────────────────────────── */

add_shortcode('ailinux_ai_playground', function ($atts): string {
    $label = esc_attr($atts['label'] ?? 'AILINUX AI PLAYGROUND');
    $title = esc_html($atts['title'] ?? 'Nova Frontend');
    $desc  = esc_html($atts['desc']  ?? 'Chat, Vision Analyse und Media Generation mit backend-seitiger Modellsortierung.');
    ob_start(); ?>
<div class="nova-ai-shell" data-nova-theme="auto">
  <div class="nova-hero">
    <div class="nova-hero-label"><?= $label ?></div>
    <h2 class="nova-hero-title"><?= $title ?></h2>
    <p class="nova-hero-desc"><?= $desc ?></p>
    <div class="nova-hero-badges">
      <span class="nova-badge" data-health-badge>Prüfe Backend…</span>
      <span class="nova-badge" data-model-count>—</span>
    </div>
  </div>
  <div class="nova-toolbar">
    <button class="nova-tab active" data-tab="nova-panel-chat">Chat</button>
    <button class="nova-tab" data-tab="nova-panel-vision">Vision Analyse</button>
    <button class="nova-tab" data-tab="nova-panel-media">Media Generation</button>
    <div class="nova-theme-picker">
      <button class="nova-theme-btn" title="Theme wechseln">🎨 <span class="nova-theme-label" data-nova-theme-label>Theme</span></button>
      <div class="nova-theme-dropdown"></div>
    </div>
  </div>
  <!-- CHAT -->
  <div class="nova-panel active" id="nova-panel-chat">
    <div class="nova-form-row-inline">
      <div class="nova-form-group" style="flex:1">
        <label class="nova-label" for="nova-chat-model">Chat Modell</label>
        <select id="nova-chat-model" name="nova-chat-model" class="nova-select nova-chat-model" data-model="chat"></select>
      </div>
      <button class="nova-chat-clear" title="Chat leeren">🗑</button>
    </div>
    <button class="nova-system-show nova-small-btn">+ System Prompt</button>
    <div class="nova-form-group nova-system-group nova-hidden">
      <label class="nova-label" for="nova-chat-system">System-Prompt <button class="nova-system-toggle">▲</button></label>
      <textarea id="nova-chat-system" name="nova-chat-system" class="nova-textarea nova-chat-system" rows="3" placeholder="Du bist ein hilfreicher Assistent…"></textarea>
    </div>
    <div class="nova-chat-history" role="log" aria-live="polite">
      <div class="nova-chat-welcome">
        <div class="nova-chat-welcome-icon">✦</div>
        <p>Frag mich etwas — <kbd>Enter</kbd> sendet, <kbd>Shift+Enter</kbd> neue Zeile</p>
      </div>
    </div>
    <div class="nova-input-area">
      <div class="nova-input-row">
        <textarea id="nova-chat-prompt" name="nova-chat-prompt" class="nova-prompt nova-chat-prompt" placeholder="Nachricht eingeben…" rows="1" aria-label="Nachricht"></textarea>
        <button class="nova-send-btn nova-chat-send" aria-label="Senden">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M.5 1.163A1 1 0 0 1 1.97.28l12.868 6.837a1 1 0 0 1 0 1.766L1.969 15.72A1 1 0 0 1 .5 14.836V10.33a1 1 0 0 1 .816-.983L8.5 8 1.316 6.653A1 1 0 0 1 .5 5.67V1.163Z"/></svg>
        </button>
      </div>
      <div class="nova-shortcuts-hint">
        <span><kbd class="nova-key">↑</kbd> letzte Eingabe</span>
        <span><kbd class="nova-key">Esc</kbd> löschen</span>
        <span><kbd class="nova-key">Ctrl+K</kbd> neuer Chat</span>
      </div>
    </div>
  </div>
  <!-- VISION -->
  <div class="nova-panel" id="nova-panel-vision">
    <div class="nova-form-group">
      <label class="nova-label" for="nova-vision-model">Vision Modell</label>
      <select id="nova-vision-model" name="nova-vision-model" class="nova-select nova-vision-model" data-model="vision"></select>
    </div>
    <div class="nova-form-group">
      <label class="nova-label" for="nova-vision-url">Bild URL</label>
      <input type="url" id="nova-vision-url" name="nova-vision-url" class="nova-input nova-vision-url" placeholder="https://…">
    </div>
    <div class="nova-form-group">
      <label class="nova-label" for="nova-vision-b64">Oder Base64</label>
      <textarea id="nova-vision-b64" name="nova-vision-b64" class="nova-textarea nova-vision-b64" rows="3" placeholder="data:image/jpeg;base64,…"></textarea>
    </div>
    <div class="nova-form-group">
      <label class="nova-label" for="nova-vision-task">Analyseauftrag</label>
      <input type="text" id="nova-vision-task" name="nova-vision-task" class="nova-input nova-vision-task" value="Beschreibe dieses Bild detailliert.">
    </div>
    <button class="nova-action-btn nova-vision-btn">Bild analysieren</button>
    <div class="nova-output-box">
      <div class="nova-output-label">Ergebnis</div>
      <div class="nova-output-text nova-vision-output"></div>
    </div>
  </div>
  <!-- MEDIA -->
  <div class="nova-panel" id="nova-panel-media">
    <div class="nova-subtabs">
      <button class="nova-subtab active" data-subtab="bild">Bild</button>
      <button class="nova-subtab" data-subtab="video">Video</button>
    </div>
    <div id="nova-media-bild" class="nova-subpanel active">
      <div class="nova-form-group">
        <label class="nova-label" for="nova-img-model">Bildmodell</label>
        <select id="nova-img-model" name="nova-img-model" class="nova-select nova-img-model" data-model="media_image"></select>
      </div>
      <div class="nova-form-group">
        <label class="nova-label">Prompt</label>
        <textarea id="nova-img-prompt" name="nova-img-prompt" class="nova-textarea nova-img-prompt" rows="4" placeholder="Ein brauner Bär…"></textarea>
      </div>
      <div class="nova-form-row-inline">
        <div class="nova-form-group">
          <label class="nova-label" for="nova-img-count">Anzahl</label>
          <input type="number" id="nova-img-count" name="nova-img-count" class="nova-input nova-img-count" value="1" min="1" max="4">
        </div>
        <div class="nova-form-group" style="flex:1">
          <label class="nova-label" for="nova-img-size">Größe</label>
          <select id="nova-img-size" name="nova-img-size" class="nova-select nova-img-size">
            <option value="1024x1024" selected>1024×1024</option>
            <option value="1280x720">1280×720</option>
            <option value="512x512">512×512</option>
            <option value="1792x1024">1792×1024</option>
          </select>
        </div>
      </div>
      <button class="nova-action-btn nova-img-btn">Bild erzeugen</button>
      <div class="nova-progress nova-img-progress"><div class="nova-progress-bar" style="width:0%"></div></div>
      <div class="nova-output-box nova-img-output"><div class="nova-output-text"></div></div>
    </div>
    <div id="nova-media-video" class="nova-subpanel nova-hidden">
      <div class="nova-form-group">
        <label class="nova-label" for="nova-vid-model">Videomodell</label>
        <select id="nova-vid-model" name="nova-vid-model" class="nova-select nova-vid-model" data-model="media_video"></select>
      </div>
      <div class="nova-form-group">
        <label class="nova-label" for="nova-vid-prompt">Prompt</label>
        <textarea id="nova-vid-prompt" name="nova-vid-prompt" class="nova-textarea nova-vid-prompt" rows="4" placeholder="Ein Braunbär kämpft…"></textarea>
      </div>
      <div class="nova-form-row-inline">
        <div class="nova-form-group">
          <label class="nova-label" for="nova-vid-duration">Dauer (s)</label>
          <input type="number" id="nova-vid-duration" name="nova-vid-duration" class="nova-input nova-vid-duration" value="8" min="4" max="30">
        </div>
        <div class="nova-form-group" style="flex:1">
          <label class="nova-label" for="nova-vid-resolution">Auflösung</label>
          <select id="nova-vid-resolution" name="nova-vid-resolution" class="nova-select nova-vid-resolution">
            <option value="1280x720" selected>1280×720</option>
            <option value="1920x1080">1920×1080</option>
            <option value="854x480">854×480</option>
          </select>
        </div>
      </div>
      <button class="nova-action-btn nova-vid-btn">Video starten</button>
      <div class="nova-progress nova-vid-progress"><div class="nova-progress-bar" style="width:0%"></div></div>
      <div class="nova-output-box nova-vid-output"><div class="nova-output-text"></div></div>
    </div>
  </div>
</div>
    <?php return ob_get_clean();
});

/* ─── Shortcode: Downloads ────────────────────────────────────────────────── */

add_shortcode('ailinux_downloads', function ($atts): string {
    $label = esc_attr($atts['label'] ?? 'AILINUX DOWNLOADS');
    $title = esc_html($atts['title'] ?? 'Downloads');
    $desc  = esc_html($atts['desc']  ?? 'Mehr Metadaten, mehr Übersicht, weniger Blindflug.');
    $raw   = wp_remote_get(NOVA_AI_BACKEND.'/v1/frontend/dashboard/downloads', ['timeout'=>10]);
    $files = []; $total = 0;
    if (!is_wp_error($raw)) {
        $body = json_decode(wp_remote_retrieve_body($raw), true);
        if (isset($body['files']) && is_array($body['files'])) { $files = $body['files']; $total = $body['total_bytes'] ?? 0; }
    }
    $fmt = function(int $b): string {
        if ($b >= 1073741824) return round($b/1073741824,1).' GB';
        if ($b >= 1048576)    return round($b/1048576,1).' MB';
        if ($b >= 1024)       return round($b/1024,1).' KB';
        return $b.' B';
    };
    ob_start(); ?>
<div class="nova-downloads-shell" data-nova-theme="auto">
  <div class="nova-hero">
    <div class="nova-hero-label"><?= $label ?></div>
    <h2 class="nova-hero-title"><?= $title ?></h2>
    <p class="nova-hero-desc"><?= $desc ?></p>
    <div class="nova-hero-badges">
      <?php if (!empty($files)): ?>
        <span class="nova-badge">Dateien: <?= count($files) ?></span>
        <?php if ($total > 0): ?><span class="nova-badge">Gesamt: <?= $fmt($total) ?></span><?php endif; ?>
      <?php endif; ?>
    </div>
    <!-- nova-theme-picker hidden: auto-sync with WP theme -->
  </div>
  <?php if (empty($files)): ?>
    <div class="nova-status-bar warn" style="margin:16px"><span class="nova-status-icon">⚠️</span> Backend nicht erreichbar oder keine Dateien.</div>
  <?php else: ?>
  <div class="nova-panel active" style="padding-top:0">
    <div class="nova-table-wrap">
      <table class="nova-table">
        <thead><tr>
          <th data-sort="0">Datei</th><th data-sort="1">Typ</th><th data-sort="2">Größe</th>
          <th data-sort="3">SHA1</th><th data-sort="4">Geändert</th><th data-sort="5">Link</th>
        </tr></thead>
        <tbody>
          <?php foreach ($files as $f): ?>
          <tr>
            <td title="<?= esc_attr($f['name']??'') ?>"><?= esc_html($f['name']??'—') ?></td>
            <td><?= esc_html(strtoupper($f['type']??'—')) ?></td>
            <td><?= esc_html($fmt((int)($f['size']??0))) ?></td>
            <td title="<?= esc_attr($f['sha1']??'') ?>"><?= esc_html(substr($f['sha1']??'—',0,8)) ?>…</td>
            <td><?= esc_html($f['modified']??'—') ?></td>
            <td><?php if (!empty($f['url'])): ?><a class="nova-dl-link" href="<?= esc_url($f['url']) ?>" download>↓ Download</a><?php else: ?>—<?php endif; ?></td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
  </div>
  <?php endif; ?>
</div>
    <?php return ob_get_clean();
});

/* ─── WP Block filter (WP 6.x compat) ─────────────────────────────────────── */
add_filter('render_block_core/shortcode', function ($content) {
    if (has_shortcode($content,'ailinux_ai_playground') || has_shortcode($content,'ailinux_downloads'))
        return do_shortcode($content);
    return $content;
});
