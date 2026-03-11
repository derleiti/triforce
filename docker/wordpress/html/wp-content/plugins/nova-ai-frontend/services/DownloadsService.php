<?php
namespace NovAI\Services;

defined('ABSPATH') || exit;

class DownloadsService {
    private static $instance = null;
    private $base_path;
    private $base_url;

    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        $settings = get_option('nova_ai_settings', []);
        $this->base_path = $settings['downloads_path'] ?? ABSPATH . 'downloads';
        $this->base_url = home_url('/downloads');
        
        // Register AJAX handler
        add_action('wp_ajax_nov_ai_browse', [$this, 'ajax_browse']);
        add_action('wp_ajax_nopriv_nov_ai_browse', [$this, 'ajax_browse']);
    }

    /**
     * AJAX handler for folder navigation
     */
    public function ajax_browse() {
        $path = isset($_POST['path']) ? sanitize_text_field($_POST['path']) : '';
        
        $result = $this->get_directory_contents($path);
        wp_send_json_success($result);
    }

    /**
     * Get directory contents with proper folder navigation support
     */
    public function get_directory_contents($relative_path = '') {
        $relative_path = $this->sanitize_path($relative_path);
        $full_path = rtrim($this->base_path, '/') . '/' . ltrim($relative_path, '/');
        $full_path = rtrim($full_path, '/');
        
        if (!is_dir($full_path)) {
            return ['files' => [], 'breadcrumb' => $this->build_breadcrumb('')];
        }

        $files = [];
        $items = @scandir($full_path);
        
        if ($items === false) {
            return ['files' => [], 'breadcrumb' => $this->build_breadcrumb($relative_path)];
        }

        // First pass: folders
        foreach ($items as $item) {
            if ($item === '.' || $item === '..') continue;
            
            $item_path = $full_path . '/' . $item;
            $item_relative = trim($relative_path . '/' . $item, '/');
            
            if (is_dir($item_path)) {
                $file_count = $this->count_files_in_dir($item_path);
                $files[] = [
                    'name' => $item,
                    'type' => 'folder',
                    'path' => $item_relative,
                    'icon' => '📁',
                    'size' => $file_count . ' items',
                    'modified' => date('Y-m-d H:i', filemtime($item_path)),
                    'url' => ''
                ];
            }
        }

        // Second pass: files
        foreach ($items as $item) {
            if ($item === '.' || $item === '..') continue;
            
            $item_path = $full_path . '/' . $item;
            $item_relative = trim($relative_path . '/' . $item, '/');
            
            if (is_file($item_path)) {
                $files[] = [
                    'name' => $item,
                    'type' => 'file',
                    'path' => $item_relative,
                    'icon' => $this->get_file_icon($item),
                    'size' => $this->format_size(filesize($item_path)),
                    'modified' => date('Y-m-d H:i', filemtime($item_path)),
                    'url' => $this->base_url . '/' . $item_relative
                ];
            }
        }

        return [
            'files' => $files,
            'breadcrumb' => $this->build_breadcrumb($relative_path),
            'current_path' => $relative_path
        ];
    }

    /**
     * Build breadcrumb navigation
     */
    private function build_breadcrumb($relative_path) {
        $breadcrumb = [['name' => 'Downloads', 'path' => '']];
        
        if (empty($relative_path)) {
            return $breadcrumb;
        }

        $parts = explode('/', $relative_path);
        $current_path = '';
        
        foreach ($parts as $part) {
            if (empty($part)) continue;
            $current_path .= ($current_path ? '/' : '') . $part;
            $breadcrumb[] = ['name' => $part, 'path' => $current_path];
        }

        return $breadcrumb;
    }

    /**
     * Sanitize path to prevent directory traversal
     */
    private function sanitize_path($path) {
        $path = str_replace(['..', '\\'], '', $path);
        $path = preg_replace('#/+#', '/', $path);
        return trim($path, '/');
    }

    /**
     * Count files in directory
     */
    private function count_files_in_dir($dir) {
        $count = 0;
        $items = @scandir($dir);
        if ($items) {
            foreach ($items as $item) {
                if ($item !== '.' && $item !== '..') {
                    $count++;
                }
            }
        }
        return $count;
    }

    /**
     * Get file icon based on extension
     */
    private function get_file_icon($filename) {
        $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
        $icons = [
            'deb' => '📦',
            'rpm' => '📦',
            'appimage' => '🐧',
            'tar' => '🗜️',
            'gz' => '🗜️',
            'zip' => '🗜️',
            'xz' => '🗜️',
            '7z' => '🗜️',
            'iso' => '💿',
            'img' => '💿',
            'pdf' => '📕',
            'doc' => '📄',
            'docx' => '📄',
            'txt' => '📝',
            'md' => '📝',
            'sh' => '⚙️',
            'py' => '🐍',
            'js' => '📜',
            'json' => '📋',
            'xml' => '📋',
            'yaml' => '📋',
            'yml' => '📋',
            'png' => '🖼️',
            'jpg' => '🖼️',
            'jpeg' => '🖼️',
            'gif' => '🖼️',
            'svg' => '🖼️',
            'mp3' => '🎵',
            'mp4' => '🎬',
            'avi' => '🎬',
            'mkv' => '🎬',
        ];
        return $icons[$ext] ?? '📄';
    }

    /**
     * Format file size
     */
    private function format_size($bytes) {
        if ($bytes >= 1073741824) {
            return number_format($bytes / 1073741824, 2) . ' GB';
        } elseif ($bytes >= 1048576) {
            return number_format($bytes / 1048576, 2) . ' MB';
        } elseif ($bytes >= 1024) {
            return number_format($bytes / 1024, 2) . ' KB';
        }
        return $bytes . ' B';
    }
}
