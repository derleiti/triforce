<?php
/**
 * Asset Loader with Manifest Support
 *
 * Handles cache-busted asset loading using Vite-generated manifest
 *
 * @package Ailinux_Nova_Dark
 * @since 1.1.0
 */

if (!defined('ABSPATH')) {
    exit;
}

class Ailinux_Nova_Dark_Asset_Loader
{
    /**
     * Cached manifest data
     *
     * @var array|null
     */
    private static $manifest = null;

    /**
     * Theme directory path
     *
     * @var string
     */
    private static $theme_dir;

    /**
     * Theme directory URL
     *
     * @var string
     */
    private static $theme_uri;

    /**
     * Initialize asset loader
     *
     * @return void
     */
    public static function init()
    {
        self::$theme_dir = get_template_directory();
        self::$theme_uri = get_template_directory_uri();
    }

    /**
     * Load manifest file
     *
     * @return array Manifest data or empty array on failure
     */
    private static function load_manifest()
    {
        if (self::$manifest !== null) {
            return self::$manifest;
        }

        $manifest_path = self::$theme_dir . '/dist/manifest.php';

        if (!file_exists($manifest_path)) {
            // Fallback to non-hashed assets if manifest doesn't exist
            error_log('Ailinux Nova Dark: manifest.php not found. Run `npm run build` to generate it.');
            self::$manifest = [];
            return self::$manifest;
        }

        self::$manifest = include $manifest_path;

        if (!is_array(self::$manifest)) {
            error_log('Ailinux Nova Dark: Invalid manifest.php format');
            self::$manifest = [];
        }

        return self::$manifest;
    }

    /**
     * Get asset URL from manifest
     *
     * @param string $asset_name Asset name without extension (e.g., 'app', 'style')
     * @param string $fallback_file Fallback file name if manifest doesn't exist
     * @return string Asset URL
     */
    public static function get_asset_url($asset_name, $fallback_file = '')
    {
        $manifest = self::load_manifest();

        if (isset($manifest[$asset_name]) && isset($manifest[$asset_name]['file'])) {
            return self::$theme_uri . '/dist/' . $manifest[$asset_name]['file'];
        }

        // Fallback to non-hashed file
        if (!empty($fallback_file)) {
            return self::$theme_uri . '/dist/' . $fallback_file;
        }

        return '';
    }

    /**
     * Get asset version from manifest
     *
     * @param string $asset_name Asset name without extension
     * @return string Version string (file hash or modification time)
     */
    public static function get_asset_version($asset_name)
    {
        $manifest = self::load_manifest();

        if (isset($manifest[$asset_name]) && isset($manifest[$asset_name]['file'])) {
            // Extract hash from filename (e.g., app.abc123.js -> abc123)
            $file = $manifest[$asset_name]['file'];
            if (preg_match('/\.([a-f0-9]+)\.(js|css)$/', $file, $matches)) {
                return $matches[1];
            }
        }

        // Fallback to file modification time
        $asset_path = self::$theme_dir . '/dist/' . $asset_name;
        if (file_exists($asset_path)) {
            return (string) filemtime($asset_path);
        }

        return AILINUX_NOVA_DARK_VERSION;
    }

    /**
     * Enqueue script with manifest support
     *
     * @param string $handle Script handle
     * @param string $asset_name Asset name in manifest (e.g., 'app')
     * @param string $fallback_file Fallback filename
     * @param array $deps Dependencies
     * @param bool $in_footer Load in footer
     * @return void
     */
    public static function enqueue_script($handle, $asset_name, $fallback_file = '', $deps = [], $in_footer = true)
    {
        $url = self::get_asset_url($asset_name, $fallback_file);

        if (empty($url)) {
            error_log("Ailinux Nova Dark: Cannot load script '{$handle}' - asset '{$asset_name}' not found");
            return;
        }

        $version = self::get_asset_version($asset_name);
        wp_enqueue_script($handle, $url, $deps, $version, $in_footer);
    }

    /**
     * Enqueue style with manifest support
     *
     * @param string $handle Style handle
     * @param string $asset_name Asset name in manifest (e.g., 'style')
     * @param string $fallback_file Fallback filename
     * @param array $deps Dependencies
     * @param string $media Media type
     * @return void
     */
    public static function enqueue_style($handle, $asset_name, $fallback_file = '', $deps = [], $media = 'all')
    {
        $url = self::get_asset_url($asset_name, $fallback_file);

        if (empty($url)) {
            error_log("Ailinux Nova Dark: Cannot load style '{$handle}' - asset '{$asset_name}' not found");
            return;
        }

        $version = self::get_asset_version($asset_name);
        wp_enqueue_style($handle, $url, $deps, $version, $media);
    }

    /**
     * Check if asset exists in manifest
     *
     * @param string $asset_name Asset name
     * @return bool True if asset exists
     */
    public static function asset_exists($asset_name)
    {
        $manifest = self::load_manifest();
        return isset($manifest[$asset_name]);
    }

    /**
     * Get all assets from manifest
     *
     * @return array All assets
     */
    public static function get_all_assets()
    {
        return self::load_manifest();
    }

    /**
     * Clear manifest cache (useful for development)
     *
     * @return void
     */
    public static function clear_cache()
    {
        self::$manifest = null;
    }
}

// Initialize on theme setup
add_action('after_setup_theme', ['Ailinux_Nova_Dark_Asset_Loader', 'init']);
