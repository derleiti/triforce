<?php
/**
 * Plugin Name: Nova AI Frontend
 * Description: AILinux AI Playground & Downloads — Chat, Vision, Media Generation + Admin Dashboard
 * Version: 6.5.0
 * Author: zombie@ailinux
 * Text Domain: nova-ai-frontend
 */

defined('ABSPATH') || exit;

define('NOVA_AI_BACKEND',     'http://172.18.0.1:9000');
define('NOVA_AI_VERSION',     '6.5.0');
define('NOVA_AI_PLUGIN_URL',  plugin_dir_url(__FILE__));
define('NOVA_AI_PLUGIN_DIR',  plugin_dir_path(__FILE__));

/* ── FIX: Cloudflare Rocket Loader / WP Page Cache – exclude nova-ai.js ──── */
add_filter('script_loader_tag', function (string $tag, string $handle): string {
    if ($handle === 'nova-ai-frontend') {
        // Rocket Loader: data-cfasync=false prevents deferred execution in wrong scope
        $tag = str_replace(' src=', ' data-cfasync="false" src=', $tag);
    }
    return $tag;
}, 10, 2);

/* ── REST API Proxy ─────────────────────────────────────────────────────────── */
add_action('rest_api_init', function () {
    // Bypass WP cookie auth for nova-ai endpoints.
    // rest_cookie_check_errors fires even with permission_callback=__return_true
    // and rejects requests when browser has a WP cookie but no valid nonce.
    // Fix: WP's rest_cookie_check_errors runs at priority 100.
    // It fires after our priority-5 filter and still returns 403 for logged-in
    // users without a valid nonce. We override it AFTER at priority 200.
    add_filter('rest_authentication_errors', function($result) {
        // Multi-source check: original URI, rewritten path, rest_route param
        $uri   = isset($_SERVER['REQUEST_URI'])   ? $_SERVER['REQUEST_URI']   : '';
        $qs    = isset($_SERVER['QUERY_STRING'])  ? $_SERVER['QUERY_STRING']  : '';
        $route = isset($_SERVER['PATH_INFO'])     ? $_SERVER['PATH_INFO']     : '';
        $rr    = isset($_GET['rest_route'])       ? $_GET['rest_route']       : '';
        $is_nova = (
            strpos($uri,   '/nova-ai/') !== false ||
            strpos($qs,    'nova-ai')   !== false ||
            strpos($rr,    '/nova-ai/') !== false ||
            strpos($route, '/nova-ai/') !== false
        );
        if ($is_nova) {
            error_log('[nova-ai] auth bypass fired, uri=' . $uri . ' result_type=' . (is_wp_error($result) ? 'WP_Error:' . $result->get_error_code() : gettype($result)));
            return null;
        }
        return $result;
    }, 200); // priority 200 = AFTER WP's cookie check at priority 100
    $ns = 'nova-ai/v1';
    // Frontend routes
    register_rest_route($ns, '/health',  ['methods'=>'GET',  'callback'=>'nova_proxy_health',  'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/models',  ['methods'=>'GET',  'callback'=>'nova_proxy_models',  'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/chat',    ['methods'=>'POST', 'callback'=>'nova_proxy_chat',    'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/vision',  ['methods'=>'POST', 'callback'=>'nova_proxy_vision',  'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/vision-upload', ['methods'=>'POST', 'callback'=>'nova_proxy_vision_upload', 'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/media/image', ['methods'=>'POST','callback'=>'nova_proxy_image','permission_callback'=>'__return_true']);
    register_rest_route($ns, '/media/video', ['methods'=>'POST','callback'=>'nova_proxy_video','permission_callback'=>'__return_true']);
    register_rest_route($ns, '/media/video/status/(?P<job_id>[a-zA-Z0-9_\-]+)', ['methods'=>'GET','callback'=>'nova_proxy_video_status','permission_callback'=>'__return_true']);
    register_rest_route($ns, '/nonce',   ['methods'=>'GET', 'permission_callback'=>'__return_true', 'callback'=>function(){
        // Always return a nonce - guests get anonymous nonce (user_id=0), logged-in users get personal nonce
        return new WP_REST_Response(['ok'=>true,'nonce'=>wp_create_nonce('wp_rest'),'guest'=>!is_user_logged_in()],200,
            ['Cache-Control'=>'no-store,no-cache,max-age=0','Pragma'=>'no-cache']);
    }]);
    register_rest_route($ns, '/article-chat', ['methods'=>'POST', 'callback'=>'nova_proxy_article_chat', 'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/auth/status', ['methods'=>'GET', 'callback'=>'nova_auth_status', 'permission_callback'=>'__return_true']);
    register_rest_route($ns, '/account', ['methods'=>'GET', 'callback'=>'nova_proxy_account', 'permission_callback'=>'__return_true']);
    // Auth routes delegated to AuthService.php (register_rest_routes)
    // Subscription & Purchase routes (user must be logged in)
    $user_perm = function() { return is_user_logged_in(); };
    register_rest_route($ns, '/subscription',        ['methods'=>'GET',  'callback'=>'nova_proxy_subscription',        'permission_callback'=>$user_perm]);
    register_rest_route($ns, '/subscription/cancel', ['methods'=>'POST', 'callback'=>'nova_proxy_subscription_cancel', 'permission_callback'=>$user_perm]);
    register_rest_route($ns, '/purchases',           ['methods'=>'GET',  'callback'=>'nova_proxy_purchases',           'permission_callback'=>$user_perm]);

    // Admin routes – require manage_options capability
    $admin_perm = function() { return current_user_can('manage_options'); };
    register_rest_route($ns, '/admin/status',       ['methods'=>'GET',  'callback'=>'nova_admin_status',       'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/logs',         ['methods'=>'GET',  'callback'=>'nova_admin_logs',         'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/agents',       ['methods'=>'GET',  'callback'=>'nova_admin_agents',       'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/agents/(?P<agent_id>[a-z0-9_\-]+)/(?P<action>start|stop|restart)', ['methods'=>'POST','callback'=>'nova_admin_agent_action','permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/mcp/tools',    ['methods'=>'GET',  'callback'=>'nova_admin_mcp_tools',    'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/mcp/call',     ['methods'=>'POST', 'callback'=>'nova_admin_mcp_call',     'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/crawler',      ['methods'=>'GET',  'callback'=>'nova_admin_crawler_get',  'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/crawler',      ['methods'=>'POST', 'callback'=>'nova_admin_crawler_set',  'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/vault/keys',   ['methods'=>'GET',  'callback'=>'nova_admin_vault_keys',   'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/vault/set',    ['methods'=>'POST', 'callback'=>'nova_admin_vault_set',    'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/settings',     ['methods'=>'GET',  'callback'=>'nova_admin_settings_get', 'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/settings',     ['methods'=>'POST', 'callback'=>'nova_admin_settings_set', 'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/restart',      ['methods'=>'POST', 'callback'=>'nova_admin_restart',      'permission_callback'=>$admin_perm]);
    register_rest_route($ns, '/admin/bootstrap',    ['methods'=>'POST', 'callback'=>'nova_admin_bootstrap',    'permission_callback'=>$admin_perm]);
});

/* ── Core proxy helper ──────────────────────────────────────────────────────── */
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

/* ── Frontend proxy callbacks ───────────────────────────────────────────────── */
function nova_proxy_auth(string $path, string $method='GET', ?array $body=null): WP_REST_Response {
    $s = get_option('nova_ai_settings', []);
    $base = $s['api_endpoint_internal'] ?? $s['api_endpoint'] ?? 'http://172.18.0.1:9000';
    $url  = rtrim($base, '/') . $path;
    $args = ['method'=>$method, 'timeout'=>15, 'headers'=>[
        'Content-Type'=>'application/json',
        'Authorization'=>'Basic '.base64_encode((getenv('MCP_OAUTH_USER') ?: 'zombie').':'.(getenv('MCP_OAUTH_PASS') ?: 'JxBWta21vGyMEiPc9Trbn1HlN7KV')),
    ]];
    if ($body !== null) $args['body'] = json_encode($body);
    $resp = wp_remote_request($url, $args);
    if (is_wp_error($resp)) return new WP_REST_Response(['error'=>$resp->get_error_message()], 502);
    $code = wp_remote_retrieve_response_code($resp);
    $data = json_decode(wp_remote_retrieve_body($resp), true) ?? [];
    return new WP_REST_Response($data, $code);
}

function nova_proxy_health(WP_REST_Request $r): WP_REST_Response  { return nova_proxy('/v1/frontend/dashboard/health'); }
function nova_proxy_models(WP_REST_Request $r): WP_REST_Response  { return nova_proxy('/v1/frontend/dashboard/models'); }
function nova_proxy_chat(WP_REST_Request $r): WP_REST_Response    { return nova_proxy('/v1/frontend/dashboard/chat',  'POST', $r->get_json_params()); }
function nova_proxy_vision(WP_REST_Request $r): WP_REST_Response  {
    $params = $r->get_json_params();
    // Normalize: JS might send 'query' or 'prompt'
    if (!empty($params['query']) && empty($params['prompt'])) {
        $params['prompt'] = $params['query'];
    }
    return nova_proxy('/v1/frontend/dashboard/vision','POST', $params);
}

function nova_proxy_vision_upload(WP_REST_Request $r): WP_REST_Response {
    // Phase 5 Fix: file → base64 → JSON → nova_frontend vision route (bypasses broken model_registry).
    // Datei wird nur für die Dauer der Anfrage im Speicher gehalten — keine dauerhafte Speicherung.
    $files = $r->get_file_params();
    $body  = $r->get_body_params();
    $model  = sanitize_text_field($body['model']  ?? '');
    $prompt = sanitize_textarea_field($body['prompt'] ?? 'Beschreibe dieses Bild detailliert.');

    if (empty($files['image_file']) || empty($files['image_file']['tmp_name'])) {
        return new WP_REST_Response(['ok'=>false,'error'=>'Keine Datei empfangen'], 400);
    }
    $tmp_path = $files['image_file']['tmp_name'];
    // BUG-FIX: use finfo magic-bytes instead of browser-declared MIME (can be wrong)
    $finfo_obj = finfo_open(FILEINFO_MIME_TYPE);
    $detected_mime = finfo_file($finfo_obj, $tmp_path);
    finfo_close($finfo_obj);
    $mime = ($detected_mime && strpos($detected_mime, 'image/') === 0) ? $detected_mime : ($files['image_file']['type'] ?: 'image/jpeg');

    $raw_bytes = file_get_contents($tmp_path);
    if ($raw_bytes === false) {
        return new WP_REST_Response(['ok'=>false,'error'=>'Datei konnte nicht gelesen werden'], 500);
    }
    $b64 = base64_encode($raw_bytes);

    return nova_proxy('/v1/frontend/dashboard/vision', 'POST', [
        'model'        => $model,
        'prompt'       => $prompt,
        'image_base64' => $b64,
        'mime_type'    => $mime,
    ]);
}
function nova_proxy_account(WP_REST_Request $r): WP_REST_Response {
    // Returns account info: WP login status + tier/subscription from user_meta
    $user = wp_get_current_user();
    if (!$user || !$user->ID) {
        return new WP_REST_Response([
            'ok'         => true,
            'logged_in'  => false,
            'login_url'  => 'https://login.ailinux.me',
            'register_url' => 'https://login.ailinux.me',
        ], 200);
    }
    $raw_tier = get_user_meta($user->ID, 'nova_tier', true) ?: 'free';
    $tier     = nova_normalize_tier($raw_tier);
    $email    = $user->user_email;
    $sub_id   = get_user_meta($user->ID, 'nova_payment_subscription_id', true) ?: '';
    $entitls  = (array)(get_user_meta($user->ID, 'nova_entitlements', true) ?: []);
    $client_id = get_user_meta($user->ID, 'nova_client_id', true) ?: '';

    // Get available downloads from backend
    $downloads = [];
    $dl_resp = nova_proxy('/v1/frontend/dashboard/downloads', 'GET');
    if ($dl_resp instanceof WP_REST_Response) {
        $dl_data = $dl_resp->get_data();
        $downloads = $dl_data['files'] ?? [];
    }

    return new WP_REST_Response([
        'ok'          => true,
        'logged_in'   => true,
        'email'       => $email,
        'display_name'=> $user->display_name,
        'tier'        => $tier,
        'subscription_id' => $sub_id,
        'entitlements'=> $entitls,
        'client_id'   => $client_id,
        'downloads'   => $downloads,
        'account_url' => 'https://login.ailinux.me',
        'shop_url'    => 'https://ailinux.me/shop',
    ], 200);
}

/* ── Auth callbacks (login.ailinux.me sync) ─────────────────────────────────── */
function nova_auth_status(): WP_REST_Response {
    $user = wp_get_current_user();
    if (!$user || !$user->ID) {
        return new WP_REST_Response(['wp_logged_in'=>false,'login_url'=>'https://login.ailinux.me'], 200);
    }
    return new WP_REST_Response([
        'wp_logged_in' => true,
        'user'         => [
            'id'        => $user->ID,
            'email'     => $user->user_email,
            'name'      => $user->display_name,
            'tier'      => get_user_meta($user->ID, 'nova_tier', true) ?: 'free',
            'client_id' => get_user_meta($user->ID, 'nova_client_id', true) ?: '',
        ],
    ], 200);
}

function nova_auth_sync(WP_REST_Request $r): WP_REST_Response {
    $email     = sanitize_email($r->get_param('email'));
    $token     = sanitize_text_field($r->get_param('token'));
    $tier      = sanitize_text_field($r->get_param('tier') ?? 'free');
    $client_id = sanitize_text_field($r->get_param('client_id') ?? '');
    $name      = sanitize_text_field($r->get_param('name') ?? '');

    if (!$email || !$token) {
        return new WP_REST_Response(['success'=>false,'error'=>'email and token required'], 400);
    }

    // Verify token via backend
    $s = get_option('nova_ai_settings', []);
    $base = $s['api_endpoint_internal'] ?? $s['api_endpoint'] ?? 'https://api.ailinux.me';
    $vr = wp_remote_get(rtrim($base, '/') . '/v1/auth/verify', [
        'headers' => ['Authorization' => 'Bearer ' . $token],
        'timeout' => 8,
    ]);
    if (is_wp_error($vr) || wp_remote_retrieve_response_code($vr) < 200 || wp_remote_retrieve_response_code($vr) >= 300) {
        // Soft: allow sync even if verify fails (offline mode)
        error_log('[nova-ai] auth/sync: token verify failed — soft allow');
    } else {
        $vd = json_decode(wp_remote_retrieve_body($vr), true);
        if (!empty($vd['tier']))      $tier      = sanitize_text_field($vd['tier']);
        if (!empty($vd['client_id'])) $client_id = sanitize_text_field($vd['client_id']);
        if (!empty($vd['name']))      $name      = sanitize_text_field($vd['name']);
    }

    // Find or create WP user
    $user_id = email_exists($email);
    if (!$user_id) {
        $base_name = sanitize_user(strstr($email, '@', true)) ?: 'nova';
        $uname = $base_name; $i = 1;
        while (username_exists($uname)) $uname = $base_name . $i++;
        $user_id = wp_create_user($uname, wp_generate_password(), $email);
        if (is_wp_error($user_id)) return new WP_REST_Response(['success'=>false,'error'=>$user_id->get_error_message()], 500);
        if ($name) wp_update_user(['ID'=>$user_id, 'display_name'=>$name]);
    }

    // Normalize tier
    $tier_map = ['pro'=>'paid','unlimited'=>'paid','premium'=>'paid','enterprise'=>'enterprise','admin'=>'enterprise'];
    $tier_n   = $tier_map[strtolower($tier)] ?? ($tier === 'free' ? 'free' : 'paid');

    update_user_meta($user_id, 'nova_tier', $tier_n);
    update_user_meta($user_id, 'nova_session_token', $token);
    if ($client_id) update_user_meta($user_id, 'nova_client_id', $client_id);
    update_user_meta($user_id, 'nova_ailinux_email', $email);

    // Log user in + set auth cookie
    wp_set_current_user($user_id);
    wp_set_auth_cookie($user_id, true);

    $can_admin = current_user_can('manage_options');
    return new WP_REST_Response(['success'=>true,'can_admin'=>$can_admin,'tier'=>$tier_n,'user_id'=>$user_id], 200);
}

function nova_auth_logout(): WP_REST_Response {
    // FIX 2026-03-11 v2: The rest_authentication_errors bypass (priority 200) also skips
    // cookie auth for /auth/logout, so is_user_logged_in() can return false here even when
    // the user has a valid WP auth cookie. We manually parse + set the user from the cookie
    // so wp_logout() properly destroys the session token in the DB.
    if ( ! is_user_logged_in() ) {
        $uid = wp_validate_auth_cookie( '', 'auth' );
        if ( $uid ) {
            wp_set_current_user( $uid );
        }
    }
    if ( is_user_logged_in() ) {
        $uid = get_current_user_id();
        delete_user_meta( $uid, 'nova_session_token' );
        delete_user_meta( $uid, 'nova_wp_last_sync' );
    }
    // Clear nova_session cookie
    if ( isset( $_COOKIE['nova_session'] ) ) {
        setcookie( 'nova_session', '', time() - 3600, '/', '', is_ssl(), true );
    }
    // Destroy WP session + clear auth cookie
    wp_logout();
    return new WP_REST_Response( ['success' => true, 'redirect' => home_url()], 200 );
}

function nova_proxy_image(WP_REST_Request $r): WP_REST_Response   { return nova_proxy('/v1/frontend/dashboard/media/image','POST',$r->get_json_params()); }
function nova_proxy_video(WP_REST_Request $r): WP_REST_Response   { return nova_proxy('/v1/frontend/dashboard/media/video','POST',$r->get_json_params()); }
function nova_proxy_video_status(WP_REST_Request $r): WP_REST_Response { return nova_proxy('/v1/frontend/dashboard/media/video/status/'.$r['job_id']); }

/* ── Article Chat Proxy ─────────────────────────────────────────────────────── */
function nova_proxy_article_chat(WP_REST_Request $r): WP_REST_Response {
    $params  = $r->get_json_params();
    $context = sanitize_textarea_field($params['context'] ?? '');
    $model   = sanitize_text_field($params['model'] ?? 'groq/meta-llama/llama-4-scout-17b-16e-instruct');
    $message = sanitize_textarea_field($params['message'] ?? '');
    $history = $params['history'] ?? [];
    $messages = [['role'=>'system','content'=>
        "Du bist ein hilfreicher KI-Assistent der die Nutzer beim Verstehen und Diskutieren von Artikeln und Inhalten unterstützt.\n\n".
        "ARTIKEL-KONTEXT:\n".$context."\n\n".
        "Beantworte Fragen auf Basis dieses Kontexts."]];
    foreach ((array)$history as $h) {
        if (isset($h['role'],$h['content']))
            $messages[] = ['role'=>sanitize_text_field($h['role']),'content'=>sanitize_textarea_field($h['content'])];
    }
    $messages[] = ['role'=>'user','content'=>$message];
    $body = json_encode(['model'=>$model,'messages'=>$messages,'stream'=>false,'max_tokens'=>800]);
    $resp = wp_remote_post(NOVA_AI_BACKEND.'/v1/frontend/dashboard/chat',
        ['body'=>$body,'headers'=>['Content-Type'=>'application/json'],'timeout'=>30]);
    if (is_wp_error($resp)) return new WP_REST_Response(['error'=>$resp->get_error_message()],502);
    return new WP_REST_Response(json_decode(wp_remote_retrieve_body($resp), true), wp_remote_retrieve_response_code($resp));
}


/* ── Subscription & Purchases callbacks ─────────────────────────────────────── */
function nova_normalize_tier(string $tier): string {
    return ($tier === 'free') ? 'free' : 'paid';
}

function nova_proxy_subscription(WP_REST_Request $r): WP_REST_Response {
    $user = wp_get_current_user();
    if (!$user || !$user->ID) return new WP_REST_Response(['error'=>'not logged in'], 401);
    $client_id = get_user_meta($user->ID, 'nova_client_id', true) ?: '';
    if (!$client_id) return new WP_REST_Response(['ok'=>true,'tier'=>'free','status'=>'none','client_id'=>'']);
    // Proxy to backend
    $resp = nova_proxy('/v1/tiers/subscription/'.$client_id);
    $data = $resp->get_data();
    // Normalize tier in response
    if (!empty($data['tier'])) $data['tier'] = nova_normalize_tier($data['tier']);
    return new WP_REST_Response($data, $resp->get_status());
}

function nova_proxy_subscription_cancel(WP_REST_Request $r): WP_REST_Response {
    $user = wp_get_current_user();
    if (!$user || !$user->ID) return new WP_REST_Response(['error'=>'not logged in'], 401);
    $client_id = get_user_meta($user->ID, 'nova_client_id', true) ?: '';
    if (!$client_id) return new WP_REST_Response(['error'=>'no client_id found'], 400);
    $resp = nova_proxy('/v1/tiers/cancel', 'POST', ['user_id'=>$client_id]);
    // On success: downgrade WP user_meta to free
    if ($resp->get_status() < 300) {
        update_user_meta($user->ID, 'nova_tier', 'free');
    }
    return $resp;
}

function nova_proxy_purchases(WP_REST_Request $r): WP_REST_Response {
    $user = wp_get_current_user();
    if (!$user || !$user->ID) return new WP_REST_Response(['error'=>'not logged in'], 401);
    $client_id = get_user_meta($user->ID, 'nova_client_id', true) ?: '';
    if (!$client_id) return new WP_REST_Response(['ok'=>true,'purchases'=>[],'client_id'=>'']);
    return nova_proxy('/v1/tiers/purchases/'.$client_id);
}

/* ── Admin REST callbacks ───────────────────────────────────────────────────── */
function nova_admin_status(): WP_REST_Response {
    // FIX 2026-03-10: /health hat kein /v1 Prefix
    $r = nova_proxy('/health');
    $data = $r->get_data();
    if (empty($data['model_count'])) {
        $fh = nova_proxy('/v1/frontend/dashboard/health');
        $fhd = $fh->get_data();
        if (!empty($fhd['model_count'])) { $data['model_count'] = $fhd['model_count']; $r->set_data($data); }
    }
    return $r;
}

function nova_admin_logs(WP_REST_Request $r): WP_REST_Response {
    $cat   = sanitize_text_field($r->get_param('category') ?? 'all');
    $limit = intval($r->get_param('limit') ?? 100);
    $valid_cats = ['all','api','llm','mcp','error','agent'];
    if (!in_array($cat, $valid_cats, true)) $cat = 'all';
    // FIX 2026-03-11: pass category filter to backend
    $qs = "limit={$limit}";
    if ($cat !== 'all') $qs .= "&category={$cat}";
    return nova_proxy("/v1/triforce/logs/recent?{$qs}");
}

function nova_admin_agents(): WP_REST_Response {
    return nova_proxy('/v1/tristar/cli-agents');
}

function nova_admin_agent_action(WP_REST_Request $r): WP_REST_Response {
    $agent  = sanitize_text_field($r['agent_id']);
    $action = sanitize_text_field($r['action']);
    $map    = ['start'=>'start','stop'=>'stop','restart'=>'restart'];
    if (!isset($map[$action])) return new WP_REST_Response(['error'=>'invalid action'],400);
    return nova_proxy("/v1/tristar/cli-agents/{$agent}/{$action}", 'POST');
}

function nova_admin_mcp_tools(): WP_REST_Response {
    // FIX 2026-03-11: Use server-side MCP tools (81 tools) instead of client-side node/tools (7 desktop tools)
    // /v1/mcp accepts JSON-RPC without auth and returns all server-side tools
    $args = [
        'method'  => 'POST',
        'timeout' => 15,
        'headers' => ['Content-Type' => 'application/json'],
        'body'    => wp_json_encode(['jsonrpc' => '2.0', 'method' => 'tools/list', 'id' => 1]),
    ];
    $response = wp_remote_request(NOVA_AI_BACKEND . '/v1/mcp', $args);
    if (is_wp_error($response)) return new WP_REST_Response(['error' => $response->get_error_message()], 502);
    $body = json_decode(wp_remote_retrieve_body($response), true) ?? [];
    // Normalize JSON-RPC result → {tools: [...]} format admin.js expects
    $tools = $body['result']['tools'] ?? [];
    // Add inputSchema-based default args hint for admin.js
    foreach ($tools as &$t) {
        $props = $t['inputSchema']['properties'] ?? [];
        $t['args'] = array_fill_keys(array_keys($props), '');
    }
    unset($t);
    return new WP_REST_Response(['tools' => $tools, 'count' => count($tools)], 200);
}

function nova_admin_mcp_call(WP_REST_Request $r): WP_REST_Response {
    // FIX 2026-03-11 v2: Use server-side MCP /v1/mcp tools/call (JSON-RPC, no auth needed)
    // This replaces the broken /v1/mcp/node/call (requires connected desktop client + JWT)
    $params = $r->get_json_params();
    $tool   = sanitize_text_field($params['tool'] ?? '');
    $args   = $params['args'] ?? [];
    if (!$tool) return new WP_REST_Response(['error' => 'tool required'], 400);
    $rpc_body = wp_json_encode([
        'jsonrpc'  => '2.0',
        'method'   => 'tools/call',
        'id'       => 1,
        'params'   => ['name' => $tool, 'arguments' => (object)$args],
    ]);
    $resp = wp_remote_request(NOVA_AI_BACKEND . '/v1/mcp', [
        'method'  => 'POST',
        'timeout' => 60,
        'headers' => ['Content-Type' => 'application/json'],
        'body'    => $rpc_body,
    ]);
    if (is_wp_error($resp)) return new WP_REST_Response(['error' => $resp->get_error_message()], 502);
    $body = json_decode(wp_remote_retrieve_body($resp), true) ?? [];
    // Normalize JSON-RPC result → flat response for admin.js
    if (isset($body['error'])) {
        return new WP_REST_Response(['error' => $body['error']['message'] ?? 'MCP error'], 400);
    }
    $content = $body['result']['content'] ?? [];
    $text = implode("\n", array_map(fn($c) => $c['text'] ?? json_encode($c), $content));
    return new WP_REST_Response(['ok' => true, 'result' => $text, 'raw' => $body['result'] ?? []], 200);
}

function nova_admin_crawler_get(): WP_REST_Response {
    return nova_proxy('/v1/admin/crawler/config');
}

function nova_admin_crawler_set(WP_REST_Request $r): WP_REST_Response {
    return nova_proxy('/v1/admin/crawler/config', 'POST', $r->get_json_params());
}

function nova_admin_vault_keys(): WP_REST_Response {
    return nova_proxy_auth('/v1/tristar/settings/api-keys');
}

function nova_admin_vault_set(WP_REST_Request $r): WP_REST_Response {
    $params = $r->get_json_params();
    $key    = sanitize_text_field($params['key'] ?? '');
    $value  = $params['value'] ?? '';
    if (!$key) return new WP_REST_Response(['error'=>'key required'],400);
    return nova_proxy_auth('/v1/tristar/settings/api-keys', 'PUT', ['keys'=>[$key=>$value]]);
}

function nova_admin_settings_get(): WP_REST_Response {
    $s = get_option('nova_ai_settings', []);
    // Never expose full secret values
    return new WP_REST_Response(['ok'=>true,'settings'=>$s]);
}

function nova_admin_settings_set(WP_REST_Request $r): WP_REST_Response {
    if (!wp_verify_nonce($r->get_header('X-WP-Nonce') ?: $r->get_param('_wpnonce') ?: '', 'wp_rest'))
        return new WP_REST_Response(['error'=>'bad nonce'],403);
    $params = $r->get_json_params();
    $s = get_option('nova_ai_settings', []);
    $allowed = ['api_endpoint','api_endpoint_internal','mcp_endpoint','downloads_path',
                'default_model','discuss_button_enabled','widget_enabled','widget_position',
                'widget_color','widget_title','widget_welcome','widget_icon'];
    foreach ($allowed as $k) {
        if (array_key_exists($k, $params)) $s[$k] = sanitize_text_field((string)($params[$k]));
    }
    update_option('nova_ai_settings', $s);
    return new WP_REST_Response(['ok'=>true]);
}

function nova_admin_restart(WP_REST_Request $r): WP_REST_Response {
    return nova_proxy('/v1/tristar/cli-agents/reload-prompts', 'POST');
}

function nova_admin_bootstrap(WP_REST_Request $r): WP_REST_Response {
    return nova_proxy('/v1/bootstrap', 'POST');
}

/* ── Assets ─────────────────────────────────────────────────────────────────── */
add_action('wp_enqueue_scripts', function () {
    $url = NOVA_AI_PLUGIN_URL.'assets/';
    $ver = NOVA_AI_VERSION;
    // FIX 2026-03-10: filemtime() as version forces Cloudflare/WP cache bust on every JS update
    $js_ver  = @filemtime(NOVA_AI_PLUGIN_DIR.'assets/nova-ai.js')  ?: $ver;
    $css_ver = @filemtime(NOVA_AI_PLUGIN_DIR.'assets/nova-ai.css') ?: $ver;
    wp_enqueue_style('nova-ai-frontend', $url.'nova-ai.css', [], $css_ver);
    wp_enqueue_script('nova-ai-frontend', $url.'nova-ai.js', [], $js_ver, true);
    wp_localize_script('nova-ai-frontend', 'novaAiConfig', [
        'apiBase'    => rest_url('nova-ai/v1'),
        'nonce'      => wp_create_nonce('wp_rest'),
        'nonceUrl'   => rest_url('nova-ai/v1/nonce'),
        'autoTheme'  => true,
        'version'    => $ver,
        'isLoggedIn' => is_user_logged_in() ? 'true' : 'false',
    ]);
});

/* ── Admin Menu ─────────────────────────────────────────────────────────────── */
add_action('admin_menu', function () {
    add_menu_page(
        'Nova AI',
        'Nova AI',
        'manage_options',
        'nova-ai',
        'nova_render_admin_page',
        'dashicons-format-chat',
        30
    );
});

add_action('admin_enqueue_scripts', function ($hook) {
    if (strpos($hook, 'nova-ai') === false) return;
    wp_enqueue_style('nova-ai-admin', NOVA_AI_PLUGIN_URL.'admin/css/admin.css', [], NOVA_AI_VERSION);
    wp_enqueue_script('nova-ai-admin', NOVA_AI_PLUGIN_URL.'admin/js/admin.js', [], NOVA_AI_VERSION, true);
    wp_localize_script('nova-ai-admin', 'novaAdminConfig', [
        'restUrl'     => rest_url('nova-ai/v1'),
        'nonce'       => wp_create_nonce('wp_rest'),
        'apiEndpoint' => NOVA_AI_BACKEND,
        'version'     => NOVA_AI_VERSION,
    ]);
});

function nova_render_admin_page(): void {
    $tab = isset($_GET['tab']) ? sanitize_text_field($_GET['tab']) : 'dashboard';
    $settings = get_option('nova_ai_settings', []);
    // Handle settings save via traditional POST (fallback if JS fails)
    if (isset($_POST['nova_ai_save']) && check_admin_referer('nova_ai_settings')) {
        $allowed = ['api_endpoint','default_model','discuss_button_enabled','widget_enabled',
                    'widget_position','widget_color','widget_title','widget_welcome'];
        foreach ($allowed as $k) {
            if (isset($_POST[$k])) $settings[$k] = sanitize_text_field($_POST[$k]);
        }
        $settings['discuss_button_enabled'] = !empty($_POST['discuss_button_enabled']);
        $settings['widget_enabled']         = !empty($_POST['widget_enabled']);
        update_option('nova_ai_settings', $settings);
        echo '<div class="notice notice-success is-dismissible"><p>✅ Settings gespeichert.</p></div>';
        $settings = get_option('nova_ai_settings', []);
    }
    ?>
<div class="wrap" id="nova-admin-wrap">
<h1>🚀 Nova AI <span style="font-size:13px;opacity:.6;font-weight:400">v<?= esc_html(NOVA_AI_VERSION) ?></span></h1>

<nav class="nav-tab-wrapper">
<?php foreach ([
    'dashboard'=>'📊 Dashboard','settings'=>'⚙️ Settings','system'=>'🖥️ System Status',
    'agents'=>'🤖 Agents','mcp'=>'🌐 MCP Tools','crawler'=>'🕷️ Crawler','vault'=>'🔑 API Vault'
] as $t => $label): ?>
    <a href="?page=nova-ai&tab=<?= $t ?>" class="nav-tab <?= $tab===$t?'nav-tab-active':'' ?>"><?= $label ?></a>
<?php endforeach; ?>
</nav>

<div class="nova-admin-content" style="margin-top:20px">

<?php if ($tab === 'dashboard'): ?>
<div class="nova-stats-row" style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px">
    <div class="nova-stat-card card" style="padding:16px;min-width:180px;text-align:center">
        <div id="stat-status" style="font-size:28px">⏳</div>
        <strong id="stat-status-text">Checking…</strong><br><small>Backend Status</small>
    </div>
    <div class="nova-stat-card card" style="padding:16px;min-width:180px;text-align:center">
        <div style="font-size:28px" id="stat-models">—</div>
        <small>Available Models</small>
    </div>
    <div class="nova-stat-card card" style="padding:16px;min-width:180px;text-align:center">
        <div style="font-size:28px" id="stat-agents">—</div>
        <small>Active Agents</small>
    </div>
    <div class="nova-stat-card card" style="padding:16px;min-width:180px;text-align:center">
        <div style="font-size:28px">🔗</div>
        <small><?= esc_html(NOVA_AI_BACKEND) ?></small>
    </div>
</div>
<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
    <button class="button button-primary" id="btn-refresh-all">🔄 Refresh Status</button>
    <button class="button" id="btn-test-api">🧪 Test API</button>
    <button class="button" id="btn-view-models">📋 Alle Modelle</button>
</div>
<div class="card" style="padding:16px;margin-bottom:16px">
    <h3 style="margin-top:0">📋 Verfügbare Shortcodes</h3>
    <table class="widefat">
    <tr><td><code>[ailinux_ai_playground]</code></td><td>AI Chat + Vision + Media</td><td><button class="button button-small nova-copy" data-copy="[ailinux_ai_playground]">📋</button></td></tr>
    <tr><td><code>[ailinux_downloads]</code></td><td>Download Browser</td><td><button class="button button-small nova-copy" data-copy="[ailinux_downloads]">📋</button></td></tr>
    </table>
</div>
<div class="card" style="padding:16px">
    <h3 style="margin-top:0">📜 Recent Log <button class="button button-small" id="btn-refresh-log">🔄</button></h3>
    <div id="admin-log" style="background:#1a1a1a;color:#ccc;font-family:monospace;font-size:12px;height:220px;overflow-y:auto;padding:10px;border-radius:4px">Lade Logs…</div>
</div>

<?php elseif ($tab === 'settings'): ?>
<div class="card" style="padding:20px;max-width:680px">
<h3 style="margin-top:0">⚙️ Plugin Settings</h3>
<form method="post">
<?php wp_nonce_field('nova_ai_settings'); ?>
<table class="form-table">
<tr><th>Backend API URL</th><td>
    <input type="text" name="api_endpoint" class="regular-text" value="<?= esc_attr($settings['api_endpoint'] ?? NOVA_AI_BACKEND) ?>">
    <p class="description">Intern: <?= esc_html(NOVA_AI_BACKEND) ?></p>
</td></tr>
<tr><th>Standard-Modell</th><td>
    <input type="text" name="default_model" class="regular-text" value="<?= esc_attr($settings['default_model'] ?? '') ?>" placeholder="groq/llama-3.3-70b-versatile">
</td></tr>
<tr><th>Discuss Button</th><td>
    <label><input type="checkbox" name="discuss_button_enabled" <?= !empty($settings['discuss_button_enabled'])?'checked':'' ?>> „Discuss with AI" auf Posts/Pages</label>
</td></tr>
<tr><th>Chat Widget</th><td>
    <label><input type="checkbox" name="widget_enabled" <?= !empty($settings['widget_enabled'])?'checked':'' ?>> Float-Widget aktivieren</label>
</td></tr>
</table>
<input type="submit" name="nova_ai_save" class="button button-primary" value="Speichern">
</form>
</div>

<?php elseif ($tab === 'system'): ?>
<div style="display:flex;gap:12px;margin-bottom:16px">
    <button class="button button-primary" id="btn-system-refresh">🔄 Refresh</button>
</div>
<div id="system-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">
    <div class="card" style="padding:16px"><h4>🔌 Backend API</h4><div id="sys-backend">⏳</div></div>
    <div class="card" style="padding:16px"><h4>🌐 MCP Server</h4><div id="sys-mcp">⏳</div></div>
    <div class="card" style="padding:16px"><h4>🦙 Ollama</h4><div id="sys-ollama">⏳</div></div>
    <div class="card" style="padding:16px"><h4>🔑 Vault</h4><div id="sys-vault">⏳</div></div>
</div>
<div class="card" style="padding:16px;margin-top:16px">
    <h3 style="margin-top:0">📋 Modelle <span style="font-weight:400;font-size:13px">— <span id="model-count">…</span></span></h3>
    <div style="margin-bottom:10px;display:flex;gap:8px">
        <input type="text" id="model-filter" placeholder="🔍 Filter…" style="flex:1">
        <select id="provider-filter"><option value="">Alle Provider</option></select>
    </div>
    <div id="models-table" style="max-height:400px;overflow-y:auto">⏳ Lade Modelle…</div>
</div>

<?php elseif ($tab === 'agents'): ?>
<div style="display:flex;gap:12px;margin-bottom:16px">
    <button class="button button-primary" id="btn-agents-refresh">🔄 Refresh</button>
    <button class="button" id="btn-agents-bootstrap">🚀 Bootstrap All</button>
</div>
<div id="agents-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">
    <div class="card" style="padding:16px">⏳ Lade Agents…</div>
</div>

<?php elseif ($tab === 'mcp'): ?>
<div style="display:flex;gap:12px;margin-bottom:16px">
    <button class="button button-primary" id="btn-mcp-refresh">🔄 Tools laden</button>
</div>
<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px">
    <div class="card" style="padding:16px">
        <h3 style="margin-top:0">🛠️ MCP Tools</h3>
        <input type="text" id="mcp-tool-filter" placeholder="🔍 Tool suchen…" style="width:100%;margin-bottom:10px">
        <div id="mcp-tools-list" style="max-height:500px;overflow-y:auto">⏳</div>
    </div>
    <div class="card" style="padding:16px">
        <h3 style="margin-top:0">▶️ Tool aufrufen</h3>
        <label>Tool:</label><br>
        <input type="text" id="mcp-call-tool" placeholder="tool_name" style="width:100%;margin-bottom:8px"><br>
        <label>Args (JSON):</label><br>
        <textarea id="mcp-call-args" rows="6" style="width:100%;font-family:monospace;font-size:12px">{}</textarea><br>
        <button class="button button-primary" id="btn-mcp-call" style="margin-top:8px">▶️ Ausführen</button>
        <h4>Ergebnis:</h4>
        <pre id="mcp-call-result" style="background:#1a1a1a;color:#ccc;padding:10px;font-size:11px;max-height:300px;overflow-y:auto;white-space:pre-wrap"></pre>
    </div>
</div>

<?php elseif ($tab === 'crawler'): ?>
<div class="card" style="padding:16px;max-width:680px">
    <h3 style="margin-top:0">🕷️ Crawler Konfiguration</h3>
    <div id="crawler-config">⏳ Lade Config…</div>
    <div id="crawler-form" style="display:none">
        <table class="form-table" id="crawler-table"></table>
        <button class="button button-primary" id="btn-crawler-save">💾 Speichern</button>
    </div>
    <h3>📊 Crawler Status</h3>
    <button class="button" id="btn-crawler-refresh">🔄 Refresh</button>
    <div id="crawler-status" style="margin-top:10px">—</div>
</div>

<?php elseif ($tab === 'vault'): ?>
<div class="card" style="padding:16px;max-width:680px">
    <h3 style="margin-top:0">🔑 API Vault Keys</h3>
    <div id="vault-keys">⏳ Lade Keys…</div>
    <h3>🔐 Key setzen / aktualisieren</h3>
    <table class="form-table">
        <tr><th>Key Name</th><td><input type="text" id="vault-key-name" class="regular-text" placeholder="ANTHROPIC_API_KEY"></td></tr>
        <tr><th>Value</th><td><input type="password" id="vault-key-value" class="regular-text" placeholder="sk-…"></td></tr>
    </table>
    <button class="button button-primary" id="btn-vault-set">💾 Key speichern</button>
    <div id="vault-msg" style="margin-top:10px"></div>
</div>

<?php endif; ?>

</div><!-- .nova-admin-content -->
</div><!-- .wrap -->
    <?php
}

/* ── Shortcode: AI Playground ───────────────────────────────────────────────── */
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
    <button class="nova-tab" data-tab="nova-panel-account">&#128100; My Account</button>

  </div>
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
      <label class="nova-label" for="nova-vision-file">Oder Datei hochladen <small style="opacity:.6">(jpg / png / webp / gif — nur für Analyse, keine Speicherung)</small></label>
      <input type="file" id="nova-vision-file" name="nova-vision-file" class="nova-input nova-vision-file"
             accept="image/jpeg,image/png,image/webp,image/gif" style="padding:6px;cursor:pointer;">
      <div class="nova-vision-preview"></div>
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
        <div class="nova-form-group">
          <label class="nova-label" for="nova-img-aspect">Format</label>
          <select id="nova-img-aspect" class="nova-select nova-img-aspect">
            <option value="1:1" selected>1:1 – Quadrat</option>
            <option value="16:9">16:9 – Breitbild</option>
            <option value="4:3">4:3 – Standard</option>
            <option value="3:4">3:4 – Hochformat</option>
            <option value="9:16">9:16 – Smartphone</option>
          </select>
        </div>
        <div class="nova-form-group" style="flex:1">
          <label class="nova-label" for="nova-img-size">Auflösung</label>
          <select id="nova-img-size" class="nova-select nova-img-size"></select>
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
        <div class="nova-form-group">
          <label class="nova-label" for="nova-vid-aspect">Format</label>
          <select id="nova-vid-aspect" class="nova-select nova-vid-aspect">
            <option value="16:9" selected>16:9 – Breitbild</option>
            <option value="9:16">9:16 – Hochformat</option>
          </select>
        </div>
        <div class="nova-form-group" style="flex:1">
          <label class="nova-label" for="nova-vid-resolution">Auflösung</label>
          <select id="nova-vid-resolution" class="nova-select nova-vid-resolution"></select>
        </div>
      </div>
      <button class="nova-action-btn nova-vid-btn">Video starten</button>
      <div class="nova-progress nova-vid-progress"><div class="nova-progress-bar" style="width:0%"></div></div>
      <div class="nova-output-box nova-vid-output"><div class="nova-output-text"></div></div>
    </div>
  </div>
  <div class="nova-panel" id="nova-panel-account">
    <div style="padding:1.5rem 0">
      <div class="nova-account-container" id="nova-account-panel">
        <div style="text-align:center;padding:2rem;color:#94a3b8">
          <div style="font-size:2rem;margin-bottom:.5rem">&#128100;</div>
          <div>Lade Account…</div>
        </div>
      </div>
    </div>
  </div>
</div>
    <?php return ob_get_clean();
});

/* ── Shortcode: Downloads ───────────────────────────────────────────────────── */
add_shortcode('ailinux_downloads', function ($atts): string {
    $label = esc_attr($atts['label'] ?? 'AILINUX DOWNLOADS');
    $title = esc_html($atts['title'] ?? 'Downloads');
    $desc  = esc_html($atts['desc']  ?? 'Mehr Metadaten, mehr Übersicht.');
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
  </div>
  <?php if (empty($files)): ?>
    <div class="nova-status-bar warn" style="margin:16px"><span class="nova-status-icon">⚠️</span> Backend nicht erreichbar.</div>
  <?php else: ?>
  <div class="nova-panel active" style="padding-top:0">
    <div class="nova-table-wrap">
      <table class="nova-table">
        <thead><tr><th data-sort="0">Datei</th><th data-sort="1">Typ</th><th data-sort="2">Größe</th><th data-sort="3">SHA1</th><th data-sort="4">Geändert</th><th data-sort="5">Link</th></tr></thead>
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
  <div class="nova-panel" id="nova-panel-account">
    <div style="padding:1.5rem 0">
      <div class="nova-account-container" id="nova-account-panel">
        <div style="text-align:center;padding:2rem;color:#94a3b8">
          <div style="font-size:2rem;margin-bottom:.5rem">&#128100;</div>
          <div>Lade Account…</div>
        </div>
      </div>
    </div>
  </div>
  <?php endif; ?>
</div>
    <?php return ob_get_clean();
});

/* ── AccountSuiteService ─────────────────────────────────────────────────────── */
require_once NOVA_AI_PLUGIN_DIR . 'services/AccountSuiteService.php';
\NovAI\Services\AccountSuiteService::instance();

/* ── WP Block filter ────────────────────────────────────────────────────────── */
add_filter('render_block_core/shortcode', function ($content) {
    if (has_shortcode($content,'ailinux_ai_playground') || has_shortcode($content,'ailinux_downloads'))
        return do_shortcode($content);
    return $content;
});
