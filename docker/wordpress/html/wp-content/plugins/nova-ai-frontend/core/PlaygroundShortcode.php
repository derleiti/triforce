<?php
namespace NovAI\Core;

class PlaygroundShortcode {
    public function render($atts = []) {
        $atts = shortcode_atts(["default_tab" => "chat", "height" => "600px"], $atts);
        ob_start();
        include NOVA_AI_PLUGIN_DIR . "templates/playground.php";
        return ob_get_clean();
    }
}
