<?php
/**
 * Discuss Overlay v3.1 - Dynamic Model Loading from API
 */
defined('ABSPATH') || exit;
?>
<div id="nov-discuss-overlay">
    <div class="nov-discuss-modal">
        <div class="nov-discuss-header">
            <h3>Discuss with AI</h3>
            <select id="nov-discuss-model">
                <option value="groq/llama-3.3-70b-versatile">Loading models...</option>
            </select>
            <button id="nov-discuss-close" class="nov-discuss-close" aria-label="Close">&times;</button>
        </div>
        <div id="nov-discuss-chat"></div>
        <div class="nov-discuss-input-area">
            <textarea id="nov-discuss-input" placeholder="Ask about this article..." rows="2"></textarea>
            <button id="nov-discuss-send">Send</button>
        </div>
    </div>
</div>
