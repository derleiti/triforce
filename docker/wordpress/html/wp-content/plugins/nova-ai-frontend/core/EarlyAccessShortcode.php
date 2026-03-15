<?php
namespace NovAI\Core;

class EarlyAccessShortcode {
    public function render($atts = []) {
        ob_start();
        include NOVA_AI_PLUGIN_DIR . "templates/early-access.php";
        return ob_get_clean();
    }
}
