<?php
/**
 * AI Description Service
 * Generates short descriptions for download files/folders via Haiku
 */
namespace NovAI\Services;

defined('ABSPATH') || exit;

class AiDescriptionService {
    private static $instance = null;

    public static function instance(): self {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {}

    /**
     * Get cached description or generate a new one.
     */
    public function get(string $name, string $type, string $folder = ''): string {
        $cache_key = 'nova_dl_desc_' . md5($type . '|' . $folder . '|' . $name);
        $cached    = get_transient($cache_key);
        if ($cached !== false) {
            return (string) $cached;
        }
        $desc = $this->generate($name, $type, $folder);
        set_transient($cache_key, $desc, 30 * DAY_IN_SECONDS);
        return $desc;
    }

    /**
     * Generate description via Nova backend (Haiku).
     */
    private function generate(string $name, string $type, string $folder): string {
        if ($type === 'folder') {
            $prompt = "Beschreibe kurz (max. 2 Sätze) den Download-Ordner \"{$name}\""
                    . ($folder ? " im Verzeichnis \"{$folder}\"" : "")
                    . ". Was finden Nutzer darin? Antworte direkt ohne Einleitung.";
        } else {
            $ext    = strtolower(pathinfo($name, PATHINFO_EXTENSION));
            $prompt = "Beschreibe kurz (max. 2 Sätze) die Datei \"{$name}\" (.{$ext})"
                    . ($folder ? " aus dem Ordner \"{$folder}\"" : "")
                    . ". Was enthält sie und wozu dient sie? Antworte direkt ohne Einleitung.";
        }

        $backend  = nova_get_backend_base();
        $endpoint = rtrim($backend, '/') . '/v1/chat/completions';

        $response = wp_remote_post($endpoint, [
            'timeout' => 12,
            'headers' => [
                'Content-Type'  => 'application/json',
                'X-Nova-Source' => 'downloads-ai',
            ],
            'body' => wp_json_encode([
                'model'      => 'claude-haiku-4-5',
                'max_tokens' => 100,
                'messages'   => [['role' => 'user', 'content' => $prompt]],
            ]),
        ]);

        if (is_wp_error($response) || wp_remote_retrieve_response_code($response) !== 200) {
            return '';
        }

        $data = json_decode(wp_remote_retrieve_body($response), true);
        return trim($data['choices'][0]['message']['content'] ?? '');
    }

    /**
     * Detect and describe newly discovered files (runs inline, descriptions are cached).
     */
    public function process_new(array $files, string $current_path): void {
        $known   = get_option('nova_dl_known', []);
        $changed = false;

        foreach ($files as $file) {
            $key = ltrim($current_path . '/' . $file['name'], '/');
            if (!isset($known[$key])) {
                $this->get($file['name'], $file['type'], $current_path);
                $known[$key] = time();
                $changed     = true;
            }
        }

        if ($changed) {
            update_option('nova_dl_known', $known, false);
        }
    }
}
