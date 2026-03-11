<?php
/**
 * Nova AI Floating Chat Widget Template
 *
 * @package NovAI
 * @version 4.5.1
 */

defined('ABSPATH') || exit;

$settings = get_option('nova_ai_settings', []);
$position = $atts['position'] ?? $settings['widget_position'] ?? 'bottom-right';
$color = $settings['widget_color'] ?? '#6366f1';
$title = $settings['widget_title'] ?? 'BRUMO AI Chat';
$icon = $settings['widget_icon'] ?? '🐻';
$welcome = $settings['widget_welcome'] ?? 'Hallo! Wie kann ich dir helfen?';
?>

<div id="nova-chat-widget" class="nova-chat-widget nova-chat-closed position-<?php echo esc_attr($position); ?>" style="--nova-accent: <?php echo esc_attr($color); ?>">

    <!-- Toggle Button -->
    <button class="nova-chat-toggle" id="nova-chat-toggle" aria-label="<?php esc_attr_e('Chat öffnen', 'nov-ai-frontend'); ?>">
        <span class="nova-chat-icon"><?php echo esc_html($icon); ?></span>
        <span class="nova-chat-close">×</span>
    </button>

    <!-- Chat Container -->
    <div class="nova-chat-container" id="nova-chat-container">
        <div class="nova-chat-header">
            <span class="nova-chat-title"><?php echo esc_html($title); ?></span>
            <button class="nova-chat-minimize" aria-label="<?php esc_attr_e('Minimieren', 'nov-ai-frontend'); ?>">−</button>
        </div>

        <div class="nova-chat-messages" id="nova-chat-messages">
            <div class="nova-chat-msg nova-chat-ai">
                <span class="nova-chat-msg-content"><?php echo esc_html($welcome); ?></span>
            </div>
        </div>

        <div class="nova-chat-footer">
            <form id="nova-chat-form" class="nova-chat-form">
                <input type="text"
                       id="nova-chat-input"
                       class="nova-chat-input"
                       placeholder="<?php esc_attr_e('Nachricht eingeben...', 'nov-ai-frontend'); ?>"
                       autocomplete="off">
                <button type="submit" class="nova-chat-send" aria-label="<?php esc_attr_e('Senden', 'nov-ai-frontend'); ?>">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                    </svg>
                </button>
            </form>
        </div>
    </div>

</div>

<style>
/* Nova Chat Widget Styles */
.nova-chat-widget {
    --nova-accent: #6366f1;
    --nova-bg: #1d2125;
    --nova-bg-dark: #0d1117;
    --nova-border: #30363d;
    --nova-text: #e6edf3;
    --nova-text-muted: #8b949e;

    position: fixed;
    z-index: 99999;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Positions */
.nova-chat-widget.position-bottom-right {
    bottom: 20px;
    right: 20px;
}

.nova-chat-widget.position-bottom-left {
    bottom: 20px;
    left: 20px;
}

.nova-chat-widget.position-top-right {
    top: 20px;
    right: 20px;
}

.nova-chat-widget.position-top-left {
    top: 20px;
    left: 20px;
}

/* Toggle Button */
.nova-chat-toggle {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: var(--nova-accent);
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    transition: transform 0.2s, box-shadow 0.2s;
    font-size: 28px;
}

.nova-chat-toggle:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 16px rgba(0,0,0,0.4);
}

.nova-chat-icon,
.nova-chat-close {
    position: absolute;
    transition: opacity 0.2s, transform 0.2s;
}

.nova-chat-close {
    color: white;
    font-size: 28px;
    font-weight: 300;
    opacity: 0;
    transform: rotate(-90deg);
}

.nova-chat-widget.nova-chat-closed .nova-chat-close {
    opacity: 0;
    transform: rotate(-90deg);
}

.nova-chat-widget:not(.nova-chat-closed) .nova-chat-icon {
    opacity: 0;
    transform: rotate(90deg);
}

.nova-chat-widget:not(.nova-chat-closed) .nova-chat-close {
    opacity: 1;
    transform: rotate(0);
}

/* Chat Container */
.nova-chat-container {
    position: absolute;
    bottom: 70px;
    width: 360px;
    max-height: 500px;
    background: var(--nova-bg);
    border: 1px solid var(--nova-border);
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: opacity 0.2s, transform 0.2s;
}

.nova-chat-widget.position-bottom-right .nova-chat-container,
.nova-chat-widget.position-top-right .nova-chat-container {
    right: 0;
}

.nova-chat-widget.position-bottom-left .nova-chat-container,
.nova-chat-widget.position-top-left .nova-chat-container {
    left: 0;
}

.nova-chat-widget.position-top-right .nova-chat-container,
.nova-chat-widget.position-top-left .nova-chat-container {
    bottom: auto;
    top: 70px;
}

.nova-chat-widget.nova-chat-closed .nova-chat-container {
    opacity: 0;
    pointer-events: none;
    transform: translateY(10px) scale(0.95);
}

/* Header */
.nova-chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    background: var(--nova-accent);
    color: white;
}

.nova-chat-title {
    font-weight: 600;
    font-size: 15px;
}

.nova-chat-minimize {
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
}

.nova-chat-minimize:hover {
    background: rgba(255,255,255,0.3);
}

/* Messages */
.nova-chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    background: var(--nova-bg-dark);
    min-height: 300px;
    max-height: 350px;
}

.nova-chat-msg {
    margin-bottom: 12px;
    display: flex;
}

.nova-chat-msg-content {
    padding: 10px 14px;
    border-radius: 12px;
    max-width: 85%;
    font-size: 14px;
    line-height: 1.5;
    word-wrap: break-word;
}

.nova-chat-ai .nova-chat-msg-content {
    background: var(--nova-bg);
    color: var(--nova-text);
    border-bottom-left-radius: 4px;
}

.nova-chat-user {
    justify-content: flex-end;
}

.nova-chat-user .nova-chat-msg-content {
    background: var(--nova-accent);
    color: white;
    border-bottom-right-radius: 4px;
}

.nova-chat-loading .nova-chat-msg-content {
    color: var(--nova-text-muted);
    font-style: italic;
}

/* Typing indicator */
.nova-chat-typing {
    display: flex;
    gap: 4px;
    padding: 10px 14px;
}

.nova-chat-typing span {
    width: 8px;
    height: 8px;
    background: var(--nova-text-muted);
    border-radius: 50%;
    animation: novaChatPulse 1.4s infinite;
}

.nova-chat-typing span:nth-child(2) { animation-delay: 0.2s; }
.nova-chat-typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes novaChatPulse {
    0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
    30% { opacity: 1; transform: scale(1); }
}

/* Footer */
.nova-chat-footer {
    padding: 12px;
    border-top: 1px solid var(--nova-border);
    background: var(--nova-bg);
}

.nova-chat-form {
    display: flex;
    gap: 8px;
}

.nova-chat-input {
    flex: 1;
    padding: 10px 14px;
    background: var(--nova-bg-dark);
    border: 1px solid var(--nova-border);
    border-radius: 8px;
    color: var(--nova-text);
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
}

.nova-chat-input:focus {
    border-color: var(--nova-accent);
}

.nova-chat-input::placeholder {
    color: var(--nova-text-muted);
}

.nova-chat-send {
    width: 42px;
    height: 42px;
    background: var(--nova-accent);
    border: none;
    border-radius: 8px;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
}

.nova-chat-send:hover {
    background: #5558e3;
}

.nova-chat-send:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Scrollbar */
.nova-chat-messages::-webkit-scrollbar {
    width: 6px;
}

.nova-chat-messages::-webkit-scrollbar-track {
    background: transparent;
}

.nova-chat-messages::-webkit-scrollbar-thumb {
    background: var(--nova-border);
    border-radius: 3px;
}

/* Responsive */
@media (max-width: 480px) {
    .nova-chat-container {
        width: calc(100vw - 40px);
        max-width: 360px;
    }

    .nova-chat-widget.position-bottom-right,
    .nova-chat-widget.position-bottom-left {
        bottom: 10px;
        right: 10px;
        left: auto;
    }
}
</style>

<script>
(function() {
    'use strict';

    const widget = document.getElementById('nova-chat-widget');
    const toggle = document.getElementById('nova-chat-toggle');
    const minimize = widget.querySelector('.nova-chat-minimize');
    const form = document.getElementById('nova-chat-form');
    const input = document.getElementById('nova-chat-input');
    const messages = document.getElementById('nova-chat-messages');

    // Chat history for context
    let chatHistory = [];
    const ajaxUrl = window.novAiConfig?.ajaxUrl || '/wp-admin/admin-ajax.php';

    // Toggle widget
    toggle.addEventListener('click', function() {
        widget.classList.toggle('nova-chat-closed');
        if (!widget.classList.contains('nova-chat-closed')) {
            input.focus();
        }
    });

    // Minimize button
    minimize.addEventListener('click', function() {
        widget.classList.add('nova-chat-closed');
    });

    // Handle form submit
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const message = input.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, 'user');
        chatHistory.push({ role: 'user', content: message });
        input.value = '';

        // Show typing indicator
        const typingId = showTyping();

        try {
            // Send as JSON with messages array (correct format for ChatProxy)
            const response = await fetch(ajaxUrl + '?action=nov_ai_chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: 'groq/llama-3.3-70b-versatile',
                    messages: chatHistory,
                    temperature: 0.7,
                    max_tokens: 4096
                })
            });

            const data = await response.json();
            removeTyping(typingId);

            // Extract content from various response formats
            let reply = null;

            if (data.content && typeof data.content === 'string') {
                reply = data.content;
            } else if (data.response && typeof data.response === 'string') {
                reply = data.response;
            } else if (data.data?.content) {
                reply = data.data.content;
            } else if (data.choices?.[0]?.message?.content) {
                reply = data.choices[0].message.content;
            } else if (data.success === false) {
                // WordPress error format
                reply = 'Fehler: ' + (typeof data.data === 'string' ? data.data : (data.data?.error || 'Unbekannter Fehler'));
            } else if (data.error) {
                reply = 'Fehler: ' + (typeof data.error === 'string' ? data.error : data.error.message || JSON.stringify(data.error));
            }

            if (!reply) {
                console.error('[Widget] Could not parse response:', data);
                reply = 'Fehler: Unbekanntes Antwortformat';
            }

            chatHistory.push({ role: 'assistant', content: reply });
            addMessage(reply, 'ai');

        } catch (error) {
            removeTyping(typingId);
            console.error('[Widget] Request failed:', error);
            addMessage('Verbindungsfehler: ' + error.message, 'ai');
        }
    });

    function addMessage(text, type) {
        const msg = document.createElement('div');
        msg.className = 'nova-chat-msg nova-chat-' + type;
        msg.innerHTML = '<span class="nova-chat-msg-content">' + formatMessage(text) + '</span>';
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
    }

    function formatMessage(text) {
        // Basic markdown: bold, italic, code, links
        let html = escapeHtml(text);
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        html = html.replace(/`([^`]+)`/g, '<code style="background:#2d333b;padding:2px 4px;border-radius:3px">$1</code>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function showTyping() {
        const id = 'typing-' + Date.now();
        const msg = document.createElement('div');
        msg.id = id;
        msg.className = 'nova-chat-msg nova-chat-ai nova-chat-loading';
        msg.innerHTML = '<div class="nova-chat-typing"><span></span><span></span><span></span></div>';
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
        return id;
    }

    function removeTyping(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Close on ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !widget.classList.contains('nova-chat-closed')) {
            widget.classList.add('nova-chat-closed');
        }
    });

    console.log('[BRUMO Widget] v4.5.1 initialized');

})();
</script>
