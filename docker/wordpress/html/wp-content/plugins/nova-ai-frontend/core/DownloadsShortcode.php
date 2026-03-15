<?php
namespace NovAI\Core;

class DownloadsShortcode {
    public function render($atts = []) {
        $atts = shortcode_atts(["path" => ""], $atts);
        ob_start();
        include NOVA_AI_PLUGIN_DIR . "templates/downloads.php";
        return ob_get_clean();
    }
}
