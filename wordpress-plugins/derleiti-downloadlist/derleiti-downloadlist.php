<?php
/**
 * Plugin Name: Derleiti Download List
 * Plugin URI: https://derleiti.de
 * Description: Listet Dateien/Ordner aus dem Download-Verzeichnis auf, macht sie per gesichertem AJAX-Endpoint herunterladbar und erlaubt Admin-Notizen, die im Frontend angezeigt werden.
 * Version: 1.5.0
 * Author: Derleiti
 * Author URI: https://derleiti.de
 * License: GPL2
 */

if (!defined('ABSPATH')) exit;

class Derleiti_Download_List {
    const NONCE_ACTION       = 'derleiti_download_file';
    const NOTES_NONCE_ACTION = 'derleiti_notes_nonce';
    const NOTE_KEY_PREFIX    = 'derleiti_note_';
    const OPTION_DIR         = 'derleiti_download_directory';

    /** @var string Absoluter Pfad (normalisiert, ohne Slash am Ende) */
    private $download_directory = '';
    /** @var string realpath des Download-Ordners (oder leer) */
    private $download_directory_real = '';

    public function __construct() {
        // 1) Pfad bestimmen (Option > Filter > Default)
        $opt = get_option(self::OPTION_DIR, '');
        if (is_string($opt) && $opt !== '') {
            $base = $opt;
        } else {
            $base = trailingslashit(ABSPATH) . 'downloads'; // Standard: /var/www/html/downloads
        }
        $base = apply_filters('derleiti_download_directory', $base);
        if (function_exists('wp_normalize_path')) $base = wp_normalize_path($base);
        $base = rtrim($base, '/');

        // 2) Sicherstellen, dass Ordner existiert/lesbar ist — sonst Fallback in Uploads
        if (!$this->ensure_directory_exists($base)) {
            $uploads = wp_upload_dir();
            $fallback = trailingslashit($uploads['basedir']) . 'ailinux-downloads';
            if (function_exists('wp_normalize_path')) $fallback = wp_normalize_path($fallback);
            $fallback = rtrim($fallback, '/');
            $this->ensure_directory_exists($fallback); // Best effort
            $base = $fallback;
            update_option(self::OPTION_DIR, $base, false);
        }

        $this->download_directory = $base;
        $this->download_directory_real = realpath($this->download_directory) ?: '';

        // Shortcode
        add_shortcode('derleiti_downloads', array($this, 'shortcode_handler'));

        // AJAX Download
        add_action('wp_ajax_derleiti_download_file', array($this, 'handle_download'));
        add_action('wp_ajax_nopriv_derleiti_download_file', array($this, 'handle_download'));

        // Query Vars
        add_filter('query_vars', array($this, 'add_query_vars'));

        // Styles
        add_action('wp_head', array($this, 'add_header_styles'));

        // Admin
        add_action('admin_menu', array($this, 'register_admin_menu'));
        add_action('wp_ajax_derleiti_save_note', array($this, 'ajax_save_note'));

        // Aktivierung: Ordner anlegen
        register_activation_hook(__FILE__, array(__CLASS__, 'on_activate'));
    }

    /** Aktivierung: Ordner anlegen falls fehlt */
    public static function on_activate() {
        $opt = get_option(self::OPTION_DIR, '');
        $base = $opt !== '' ? $opt : trailingslashit(ABSPATH) . 'downloads';
        if (function_exists('wp_normalize_path')) $base = wp_normalize_path($base);
        $base = rtrim($base, '/');
        if (!is_dir($base)) {
            if (!wp_mkdir_p($base)) {
                $uploads = wp_upload_dir();
                $fallback = trailingslashit($uploads['basedir']) . 'ailinux-downloads';
                if (function_exists('wp_normalize_path')) $fallback = wp_normalize_path($fallback);
                $fallback = rtrim($fallback, '/');
                wp_mkdir_p($fallback);
                update_option(self::OPTION_DIR, $fallback, false);
            } else {
                update_option(self::OPTION_DIR, $base, false);
            }
        }
    }

    /** Ordner anlegen & Rechte grob prüfen */
    private function ensure_directory_exists($path) {
        if (!is_dir($path)) {
            if (!wp_mkdir_p($path)) return false;
        }
        if (!is_readable($path)) {
            @chmod($path, 0755);
        }
        return is_dir($path) && is_readable($path);
    }

    public function add_header_styles() {
        echo '<style>
        .derleiti-downloads-container { margin:20px 0; font-family: system-ui, Arial, sans-serif; color:#e9eef3; }
        .derleiti-downloads-breadcrumb { margin-bottom:15px; padding:12px; background:#1e2124; border-radius:6px; border-left:4px solid #0073aa; color:#fff; }
        .derleiti-downloads-breadcrumb a { color:#66c0ff; }
        .derleiti-downloads-table { width:100%; border-collapse:collapse; margin-bottom:20px; border-radius:8px; overflow:hidden; }
        .derleiti-downloads-table th, .derleiti-downloads-table td { padding:12px; text-align:left; border-bottom:1px solid #2b2f33; }
        .derleiti-downloads-table th { background:#0f1317; color:#c6d4df; font-weight:600; }
        .derleiti-downloads-table tr:hover { background:#1b2024; }
        .derleiti-downloads-table a { color:#66c0ff; text-decoration:none; }
        .derleiti-downloads-table a:hover { text-decoration:underline; }
        .derleiti-downloads-error { color:#ff8585; padding:14px; border:1px solid #5a2a2a; background:#2a1515; border-radius:6px; margin:10px 0 20px; }
        .file-icon { display:inline-block; width:20px; height:20px; margin-right:8px; vertical-align:middle; }
        .folder-icon { color:#FFA000; }
        .file-size,.file-perms { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; white-space:nowrap; }
        .file-date { white-space:nowrap; }
        .derleiti-note-row td { background:#0f1113; border-top:0; }
        .derleiti-note { margin:8px 0 4px; padding:8px 10px; border-left:3px solid #3b82f6; background:#12161a; color:#cfe0ff; white-space:pre-wrap; }
        </style>';
    }

    public function add_query_vars($vars) {
        $vars[] = 'dl_path';
        return $vars;
    }

    public function handle_download() {
        check_ajax_referer(self::NONCE_ACTION);

        $file_rel_in = isset($_GET['file']) ? wp_unslash($_GET['file']) : '';
        if ($file_rel_in === '') wp_die('Keine Datei angegeben.');

        $file_rel = $this->sanitize_relative_path($file_rel_in);
        if ($file_rel === '') wp_die('Ungültiger Dateipfad.');

        $full_path = $this->download_directory . '/' . $file_rel;
        $real_path = realpath($full_path);
        $base_real = $this->download_directory_real ?: realpath($this->download_directory);

        if ($real_path === false || !$base_real || strpos($real_path, $base_real) !== 0) {
            wp_die('Ungültiger Dateipfad.');
        }
        if (!file_exists($full_path) || is_dir($full_path) || !is_readable($full_path)) {
            wp_die('Datei nicht gefunden.');
        }

        $mime_type = function_exists('mime_content_type') ? mime_content_type($full_path) : '';
        if (!$mime_type) $mime_type = 'application/octet-stream';

        $filename = basename($full_path);
        $filesize = @filesize($full_path);

        nocache_headers();
        status_header(200);
        while (ob_get_level() > 0) {
            ob_end_clean();
        }
        header('Content-Type: ' . $mime_type);
        header('Content-Disposition: attachment; filename="' . $filename . '"; filename*=UTF-8\'\'' . rawurlencode($filename));
        if ($filesize !== false) {
            header('Content-Length: ' . sprintf('%.0f', $filesize));
        }
        header('Content-Transfer-Encoding: binary');
        header('Cache-Control: private');
        header('X-Accel-Buffering: no');

        if (function_exists('ignore_user_abort')) {
            ignore_user_abort(true);
        }
        if (function_exists('set_time_limit')) {
            @set_time_limit(0);
        }

        $handle = fopen($full_path, 'rb');
        if ($handle === false) {
            wp_die('Datei konnte nicht gelesen werden.');
        }

        $chunk_size = 1024 * 1024; // 1 MB stream chunks for large files
        while (!feof($handle)) {
            $chunk = fread($handle, $chunk_size);
            if ($chunk === false) {
                break;
            }
            echo $chunk;
            flush();
        }
        fclose($handle);
        exit;
    }

    private function get_file_icon($ext) {
        $ext = strtolower((string)$ext);
        $map = [
            'img' => ['jpg','jpeg','png','gif','bmp','svg','webp'],
            'doc' => ['doc','docx','odt','rtf','txt','md'],
            'pdf' => ['pdf'],
            'zip' => ['zip','rar','7z','tar','gz','bz2'],
            'vid' => ['mp4','avi','mov','wmv','mkv','webm'],
            'aud' => ['mp3','wav','ogg','flac','aac'],
            'cod' => ['html','css','js','php','py','java','c','cpp','h','json','xml'],
        ];
        $icon = '📄'; $cls = 'file-icon-default';
        foreach ($map as $key => $arr) {
            if (in_array($ext, $arr, true)) {
                $icon = ['img'=>'📷','doc'=>'📄','pdf'=>'📑','zip'=>'🗜','vid'=>'🎬','aud'=>'🎵','cod'=>'📝'][$key];
                $cls  = [
                    'img'=>'file-icon-img','doc'=>'file-icon-doc','pdf'=>'file-icon-pdf',
                    'zip'=>'file-icon-zip','vid'=>'file-icon-video','aud'=>'file-icon-audio','cod'=>'file-icon-code'
                ][$key];
                break;
            }
        }
        return '<span class="file-icon '.$cls.'">'.$icon.'</span>';
    }

    private function format_permissions($file_path) {
        $perms = @fileperms($file_path);
        if ($perms === false) return '?????????';
        $info = (($perms & 0x4000) == 0x4000) ? 'd' : '-';
        $info .= (($perms & 0x0100) ? 'r' : '-');
        $info .= (($perms & 0x0080) ? 'w' : '-');
        $info .= (($perms & 0x0040) ? (($perms & 0x0800) ? 's' : 'x') : (($perms & 0x0800) ? 'S' : '-'));
        $info .= (($perms & 0x0020) ? 'r' : '-');
        $info .= (($perms & 0x0010) ? 'w' : '-');
        $info .= (($perms & 0x0008) ? (($perms & 0x0400) ? 's' : 'x') : (($perms & 0x0400) ? 'S' : '-'));
        $info .= (($perms & 0x0004) ? 'r' : '-');
        $info .= (($perms & 0x0002) ? 'w' : '-');
        $info .= (($perms & 0x0001) ? (($perms & 0x0200) ? 't' : 'x') : (($perms & 0x0200) ? 'T' : '-'));
        return $info;
    }

    /* ===================== Notizen (relativer Pfad als Schlüssel) ===================== */

    private function note_key_for($relative_path) {
        $p = str_replace('\\', '/', (string)$relative_path);
        $p = ltrim($p, '/');
        return self::NOTE_KEY_PREFIX . md5($p);
    }
    private function get_note($relative_path) {
        return (string) get_option($this->note_key_for($relative_path), '');
    }
    private function set_note($relative_path, $content) {
        return update_option($this->note_key_for($relative_path), wp_kses_post($content), false);
    }

    /* ===================== Admin-Menü & Seiten ===================== */

    public function register_admin_menu() {
        add_menu_page(
            'Download Notes', 'Download Notes', 'manage_options',
            'derleiti-download-notes', array($this, 'render_admin_notes_page'),
            'dashicons-edit', 58
        );
        add_submenu_page(
            'derleiti-download-notes', 'Download Ordner', 'Ordner & Pfad', 'manage_options',
            'derleiti-download-settings', array($this,'render_admin_settings')
        );
    }

    public function render_admin_settings() {
        if (!current_user_can('manage_options')) return;
        if (isset($_POST['_wpnonce']) && wp_verify_nonce($_POST['_wpnonce'], 'derleiti_dir_save')) {
            $dir = isset($_POST['derleiti_dir']) ? wp_unslash($_POST['derleiti_dir']) : '';
            $dir = trim($dir);
            if ($dir !== '') {
                if (function_exists('wp_normalize_path')) $dir = wp_normalize_path($dir);
                $dir = rtrim($dir, '/');
                if ($this->ensure_directory_exists($dir)) {
                    update_option(self::OPTION_DIR, $dir, false);
                    $this->download_directory = $dir;
                    $this->download_directory_real = realpath($dir) ?: '';
                    echo '<div class="updated"><p>Download-Ordner aktualisiert: <code>'.esc_html($dir).'</code></p></div>';
                } else {
                    echo '<div class="error"><p>Konnte Ordner nicht erstellen/lesen: <code>'.esc_html($dir).'</code></p></div>';
                }
            }
        }
        $cur = esc_attr(get_option(self::OPTION_DIR, $this->download_directory));
        echo '<div class="wrap"><h1>Download Ordner</h1>
        <form method="post">'.wp_nonce_field('derleiti_dir_save', '_wpnonce', true, false).'
        <p><label>Pfad zum Download-Verzeichnis:<br>
        <input type="text" name="derleiti_dir" value="'.$cur.'" class="regular-text" style="width:480px"></label></p>
        <p class="description">Standard ist <code>'.esc_html(trailingslashit(ABSPATH).'downloads').'</code>. Alternativ wird <code>wp-content/uploads/ailinux-downloads</code> verwendet.</p>
        <p><button class="button button-primary">Speichern</button></p>
        </form></div>';
    }

    /** Rekursiver Dateiscan inkl. Unterordner (für Admin) */
    private function scan_files_recursive($baseDir = null, $maxDepth = 3) {
        $out = [];
        $root = $baseDir ?: $this->download_directory;
        if (!is_dir($root) || !is_readable($root)) return $out;

        $rootReal = realpath($root);
        if ($rootReal === false) return $out;

        $iter = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::SELF_FIRST
        );
        foreach ($iter as $path => $info) {
            /** @var SplFileInfo $info */
            if ($info->isDir()) continue;
            if ($maxDepth >= 0 && $iter->getDepth() > $maxDepth) continue;

            $real = realpath($path);
            if ($real === false) continue;

            // Relativer Pfad
            $rel = trim(str_replace($rootReal, '', $real), DIRECTORY_SEPARATOR);
            if ($rel === '' || $rel === $real) {
                $rel = ltrim(str_replace($root . DIRECTORY_SEPARATOR, '', $path), DIRECTORY_SEPARATOR);
            }
            $rel = str_replace('\\', '/', $rel);

            $out[] = [
                'name'  => basename($path),
                'rel'   => $rel,
                'path'  => $path,
                'size'  => @filesize($path) ?: 0,
                'mtime' => @filemtime($path) ?: 0,
                'url'   => home_url('/downloads/' . implode('/', array_map('rawurlencode', explode('/', $rel)))),
                'note'  => $this->get_note($rel),
            ];
        }

        usort($out, fn($a,$b)=> ($b['mtime'] <=> $a['mtime']));
        return $out;
    }

    public function render_admin_notes_page() {
        if (!current_user_can('manage_options')) return;
        $nonce = wp_create_nonce(self::NOTES_NONCE_ACTION);

        $files = $this->scan_files_recursive(); // ← jetzt rekursiv!
        echo '<div class="wrap"><h1>Download Notes</h1>';
        echo '<p>Admin-Kommentare pro Datei (inkl. Unterordner) pflegen. Die Notizen erscheinen im Frontend unter der jeweiligen Datei.</p>';
        echo '<p><strong>Ordner:</strong> <code>'.esc_html($this->download_directory).'</code></p>';
        echo '<table class="widefat striped"><thead><tr><th>Datei (relativer Pfad)</th><th>Größe</th><th>Geändert</th><th>Kommentar</th><th>Aktion</th></tr></thead><tbody>';

        if (!$files) {
            echo '<tr><td colspan="5">Keine Dateien gefunden oder Ordner nicht lesbar.</td></tr>';
        } else {
            foreach ($files as $f) {
                echo '<tr>';
                echo '<td><strong><a href="'.esc_url($f['url']).'" target="_blank" rel="noopener">'.esc_html($f['rel']).'</a></strong></td>';
                echo '<td>'.esc_html($this->format_file_size($f['size'])).'</td>';
                echo '<td>'.esc_html(date('Y-m-d H:i', $f['mtime'])).'</td>';
                echo '<td style="min-width:320px;"><textarea class="derleiti-note-ta" data-file="'.esc_attr($f['rel']).'" rows="3" style="width:100%;">'.esc_textarea($f['note']).'</textarea></td>';
                echo '<td><button class="button button-primary derleiti-save-note" data-file="'.esc_attr($f['rel']).'">Speichern</button></td>';
                echo '</tr>';
            }
        }
        echo '</tbody></table></div>';
        ?>
        <script>
        (function(){
          const nonce = <?php echo json_encode($nonce); ?>;
          document.querySelectorAll('.derleiti-save-note').forEach(btn=>{
            btn.addEventListener('click', async ()=>{
              const file = btn.getAttribute('data-file'); // relativer Pfad!
              const ta = document.querySelector('.derleiti-note-ta[data-file="'+file+'"]');
              const note = ta ? ta.value : '';
              const old = btn.textContent; btn.disabled = true; btn.textContent='Speichern...';
              try {
                const res = await fetch(ajaxurl, {
                  method: 'POST',
                  headers: {'Content-Type':'application/x-www-form-urlencoded'},
                  body: new URLSearchParams({ action:'derleiti_save_note', _ajax_nonce: nonce, file, note })
                });
                const data = await res.json();
                btn.textContent = data.success ? 'Gespeichert' : 'Fehler';
              } catch(e){ btn.textContent='Fehler'; }
              setTimeout(()=>{ btn.textContent=old; btn.disabled=false; }, 1200);
            });
          });
        })();
        </script>
        <?php
    }

    public function ajax_save_note() {
        if (!current_user_can('manage_options')) wp_send_json_error(['message'=>'No permission'], 403);
        check_ajax_referer(self::NOTES_NONCE_ACTION);

        $rel_in = isset($_POST['file']) ? wp_unslash($_POST['file']) : '';
        $rel = $this->sanitize_relative_path($rel_in);
        if ($rel === '') wp_send_json_error(['message'=>'Missing file']);

        $full = $this->download_directory . '/' . $rel;
        $real = realpath($full);
        $base = $this->download_directory_real ?: realpath($this->download_directory);
        if (!$real || !$base || strpos($real, $base)!==0 || !is_file($real)) {
            wp_send_json_error(['message'=>'Invalid file']);
        }

        $note = isset($_POST['note']) ? wp_kses_post(wp_unslash($_POST['note'])) : '';
        $this->set_note($rel, $note); // relativer Pfad als Schlüssel!
        wp_send_json_success();
    }

    /* ===================== Shortcode / Frontend ===================== */

    public function shortcode_handler($atts) {
        $atts = shortcode_atts(['path' => ''], $atts, 'derleiti_downloads');
        if (isset($_GET['dl_path'])) $atts['path'] = wp_unslash($_GET['dl_path']);

        $relative_path = $this->sanitize_relative_path($atts['path']);
        $current_path  = $this->download_directory . ($relative_path !== '' ? '/' . $relative_path : '');

        $output = '<div class="derleiti-downloads-container">';

        if (!is_dir($this->download_directory)) {
            return $output . '<div class="derleiti-downloads-error">Download-Ordner existiert nicht: <code>' . esc_html($this->download_directory) . '</code></div></div>';
        }
        if (!is_readable($this->download_directory)) {
            return $output . '<div class="derleiti-downloads-error">Download-Ordner ist nicht lesbar: <code>' . esc_html($this->download_directory) . '</code> (Berechtigungen prüfen)</div></div>';
        }
        if (!is_dir($current_path)) {
            return $output . '<div class="derleiti-downloads-error">Verzeichnis nicht gefunden: <code>' . esc_html($current_path) . '</code></div></div>';
        }
        if (!is_readable($current_path)) {
            return $output . '<div class="derleiti-downloads-error">Verzeichnis kann nicht gelesen werden: <code>' . esc_html($current_path) . '</code></div></div>';
        }

        $output .= $this->generate_breadcrumb($relative_path);
        $output .= '<table class="derleiti-downloads-table">';
        $output .= '<thead><tr><th>Name</th><th>Typ</th><th>Größe</th><th>Geändert am</th><th>Zugriff</th></tr></thead><tbody>';

        $files = @scandir($current_path) ?: [];

        if ($relative_path !== '') {
            $parent_path = dirname($relative_path); if ($parent_path === '.' ) $parent_path = '';
            $page_url = get_permalink();
            $parent_url = add_query_arg('dl_path', $parent_path, $page_url);
            $output .= '<tr><td colspan="5"><a href="'.esc_url($parent_url).'"><span class="file-icon folder-icon">📁</span> <strong>..</strong> (Zurück)</a></td></tr>';
        }

        $directories = []; $file_list = [];
        foreach ($files as $file) {
            if ($file === '.' || $file === '..') continue;
            $fp = $current_path . '/' . $file;
            if (is_dir($fp)) $directories[] = $file; else $file_list[] = $file;
        }

        sort($directories, SORT_NATURAL|SORT_FLAG_CASE);
        foreach ($directories as $directory) {
            $dir_path = ($relative_path !== '') ? ($relative_path . '/' . $directory) : $directory;
            $full_dir_path = $current_path . '/' . $directory;
            $page_url = get_permalink();
            $dir_url = add_query_arg('dl_path', $dir_path, $page_url);
            $output .= '<tr>';
            $output .= '<td><a href="'.esc_url($dir_url).'"><span class="file-icon folder-icon">📁</span> <strong>'.esc_html($directory).'</strong></a></td>';
            $output .= '<td>Ordner</td>';
            $output .= '<td class="file-size">-</td>';
            $output .= '<td class="file-date">'.esc_html(date('d.m.Y H:i', @filemtime($full_dir_path) ?: time())).'</td>';
            $output .= '<td class="file-perms">'.esc_html($this->format_permissions($full_dir_path)).'</td>';
            $output .= '</tr>';
        }

        sort($file_list, SORT_NATURAL|SORT_FLAG_CASE);
        foreach ($file_list as $file) {
            $file_rel = ($relative_path !== '') ? ($relative_path . '/' . $file) : $file;
            $full_file_path = $current_path . '/' . $file;
            $file_size = @filesize($full_file_path) ?: 0;
            $file_ext  = pathinfo($file, PATHINFO_EXTENSION);

            $download_url = wp_nonce_url(
                add_query_arg(['action'=>'derleiti_download_file','file'=>$file_rel], admin_url('admin-ajax.php')),
                self::NONCE_ACTION
            );

            $output .= '<tr>';
            $output .= '<td><a href="'.esc_url($download_url).'">'.$this->get_file_icon($file_ext).' '.esc_html($file).'</a></td>';
            $output .= '<td>'.esc_html(strtoupper($file_ext)).'</td>';
            $output .= '<td class="file-size">'.$this->format_file_size($file_size).'</td>';
            $output .= '<td class="file-date">'.esc_html(date('d.m.Y H:i', @filemtime($full_file_path) ?: time())).'</td>';
            $output .= '<td class="file-perms">'.esc_html($this->format_permissions($full_file_path)).'</td>';
            $output .= '</tr>';

            // WICHTIG: Notiz jetzt über RELATIVEN PFAD holen
            $note = $this->get_note($file_rel);
            if ($note !== '') {
                $output .= '<tr class="derleiti-note-row"><td colspan="5"><div class="derleiti-note">'.wp_kses_post($note).'</div></td></tr>';
            }
        }

        if (empty($directories) && empty($file_list)) {
            $output .= '<tr><td colspan="5">Keine Dateien gefunden.</td></tr>';
        }

        $output .= '</tbody></table></div>';
        return $output;
    }

    private function generate_breadcrumb($path) {
        $page_url = get_permalink();
        $out = '<div class="derleiti-downloads-breadcrumb"><strong>Pfad:</strong> <a href="'.esc_url($page_url).'">Downloads</a>';
        if ($path !== '') {
            $parts = explode('/', trim($path, '/'));
            $cur = '';
            foreach ($parts as $part) {
                $cur .= '/' . $part; $cur = ltrim($cur, '/');
                $part_url = add_query_arg('dl_path', $cur, $page_url);
                $out .= ' / <a href="'.esc_url($part_url).'">'.esc_html($part).'</a>';
            }
        }
        return $out . '</div>';
    }

    private function format_file_size($bytes) {
        $units = ['B','KB','MB','GB','TB'];
        $bytes = max(0, (int)$bytes);
        $pow = $bytes > 0 ? floor(log($bytes, 1024)) : 0;
        $pow = min($pow, count($units) - 1);
        $val = ($pow > 0) ? $bytes / (1024 ** $pow) : $bytes;
        return number_format_i18n($val, 2) . ' ' . $units[$pow];
    }

    private function sanitize_relative_path($path) {
        $path = (string)$path;
        $path = str_replace("\0", '', $path);
        $path = str_replace('\\', '/', $path);
        $path = trim($path);
        if ($path === '') return '';
        $path = preg_replace('#/+#', '/', $path);
        $segments = explode('/', trim($path, '/'));
        $clean = [];
        foreach ($segments as $seg) {
            if ($seg === '' || $seg === '.' || $seg === '..') continue;
            $clean[] = $seg;
        }
        return implode('/', $clean);
    }
}

new Derleiti_Download_List();
