<?php
namespace NovAI\Core;

class DiscussButton {
    public function render_top() {
        return $this->get_button("top") . $this->get_overlay();
    }
    
    public function render_bottom() {
        return $this->get_button("bottom");
    }
    
    private function get_button($position) {
        $class = $position === "top" ? "nov-discuss-btn-top" : "nov-discuss-btn-bottom";
        return "<div class=\"nov-discuss-wrapper {$class}\">
            <button class=\"nova-discuss-button\">
                <span class=\"nov-discuss-icon\">💬</span>
                <span class=\"nov-discuss-text\">Discuss with AI</span>
            </button>
        </div>";
    }
    
    private function get_overlay() {
        ob_start();
        include NOV_AI_PLUGIN_DIR . "templates/discuss-overlay.php";
        return ob_get_clean();
    }
}
