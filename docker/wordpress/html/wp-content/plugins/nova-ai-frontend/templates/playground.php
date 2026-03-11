<?php
/**
 * Nova AI Playground v4.0 - Mobile-First Responsive
 * Theme: AILinux Nova Dark Integration
 */
defined("ABSPATH") || exit;
$tab = $atts["default_tab"] ?? "chat";
$height = $atts["height"] ?? "auto";
?>
<div class="nova-ai" data-tab="<?php echo esc_attr($tab); ?>" id="nova-playground">
    <div class="nova-bar">
        <button class="nova-tab <?php echo $tab === 'chat' ? 'on' : ''; ?>" data-t="chat">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>Chat</span>
        </button>
        <button class="nova-tab <?php echo $tab === 'vision' ? 'on' : ''; ?>" data-t="vision">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"></path>
            </svg>
            <span>Vision</span>
        </button>
        <div class="nova-select-wrap">
            <select id="nova-model" aria-label="Model Selection" class="nova-select-scroll">
                <option>Loading...</option>
            </select>
        </div>
        <button id="nova-new" title="New Chat" aria-label="Start new conversation">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
        </button>
        <button id="nova-fullscreen" title="Fullscreen" aria-label="Toggle fullscreen">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="fs-expand">
                <polyline points="15 3 21 3 21 9"></polyline>
                <polyline points="9 21 3 21 3 15"></polyline>
                <line x1="21" y1="3" x2="14" y2="10"></line>
                <line x1="3" y1="21" x2="10" y2="14"></line>
            </svg>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="fs-collapse" style="display:none">
                <polyline points="4 14 10 14 10 20"></polyline>
                <polyline points="20 10 14 10 14 4"></polyline>
                <line x1="14" y1="10" x2="21" y2="3"></line>
                <line x1="3" y1="21" x2="10" y2="14"></line>
            </svg>
        </button>
    </div>

    <!-- CHAT TAB -->
    <div class="nova-box <?php echo $tab === 'chat' ? 'on' : ''; ?>" id="chat-box">
        <div class="nova-chat" id="chat-log" role="log" aria-live="polite">
            <div class="nova-welcome">
                <div class="nova-welcome-icon">✨</div>
                <h3>Nova AI Chat</h3>
                <p>Powered by 115+ AI Models via TriForce Backend</p>
            </div>
        </div>
        <div class="nova-foot">
            <div id="chat-attachment-preview" class="nova-attachment" aria-live="polite"></div>
            <textarea id="chat-in" placeholder="Type your message... (Enter to send, Shift+Enter for newline)" rows="1" aria-label="Chat input"></textarea>
            <button id="chat-send" aria-label="Send message">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
                <span>Send</span>
            </button>
        </div>
    </div>

    <!-- VISION TAB -->
    <div class="nova-box <?php echo $tab === 'vision' ? 'on' : ''; ?>" id="vision-box">
        <div class="nova-chat" id="vision-log" role="log" aria-live="polite">
            <div class="nova-welcome">
                <div class="nova-welcome-icon">👁️</div>
                <h3>Vision Analysis</h3>
                <p>Upload an image or paste a URL for AI analysis</p>
            </div>
        </div>
        <div class="nova-foot">
            <div id="vision-preview"></div>
            <div class="nova-row">
                <label class="nova-btn">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="17 8 12 3 7 8"></polyline>
                        <line x1="12" y1="3" x2="12" y2="15"></line>
                    </svg>
                    <span>Upload</span>
                    <input type="file" id="vision-file" accept="image/*" hidden>
                </label>
                <input type="text" id="vision-url" placeholder="Or paste image URL..." aria-label="Image URL">
                <div class="nova-select-wrap">
                    <select id="vision-model" aria-label="Vision model selection" size="10" class="nova-select-scroll">
                        <option value="gemini/gemini-2.0-flash">Gemini 2.0 Flash</option>
                        <option value="gemini/gemini-1.5-pro">Gemini 1.5 Pro</option>
                        <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                    </select>
                </div>
            </div>
            <div class="nova-row">
                <textarea id="vision-prompt" rows="2" placeholder="What would you like to know about this image?" aria-label="Vision prompt">Describe this image in detail.</textarea>
                <button id="vision-go" aria-label="Analyze image">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <span>Analyze</span>
                </button>
            </div>
        </div>
    </div>
</div>

<style>
/* Welcome Screen */
.nova-welcome {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 200px;
    text-align: center;
    color: var(--nova-text-muted);
    animation: nova-fade-in 0.5s ease;
}
.nova-welcome-icon {
    font-size: 48px;
    margin-bottom: 16px;
    filter: grayscale(0.3);
}
.nova-welcome h3 {
    font-size: 20px;
    font-weight: 600;
    color: var(--nova-text);
    margin-bottom: 8px;
}
.nova-welcome p {
    font-size: 14px;
    opacity: 0.7;
}
.nova-select-wrap {
    width: 100%;
    max-width: 320px;
}
.nova-select-scroll {
    width: 100%;
    box-sizing: border-box;
    height: 44px;
    padding: var(--nova-space-sm) var(--nova-space-md);
    background: var(--nova-bg-1);
    border: 1px solid var(--nova-border, rgba(255,255,255,0.12));
    border-radius: var(--nova-radius-sm);
}
/* Button Icons */
#chat-send, #vision-go, .nova-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
#chat-send svg, #vision-go svg, .nova-btn svg {
    flex-shrink: 0;
}
/* Tab Icons */
.nova-tab svg {
    flex-shrink: 0;
}
@media (max-width: 480px) {
    .nova-tab span,
    #chat-send span,
    #vision-go span {
        display: none;
    }
    .nova-tab, #chat-send, #vision-go {
        justify-content: center;
    }
}
</style>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Fullscreen Toggle
    const fsBtn = document.getElementById('nova-fullscreen');
    const container = document.getElementById('nova-playground');
    if (fsBtn && container) {
        fsBtn.addEventListener('click', function() {
            container.classList.toggle('fullscreen');
            const expand = fsBtn.querySelector('.fs-expand');
            const collapse = fsBtn.querySelector('.fs-collapse');
            if (container.classList.contains('fullscreen')) {
                expand.style.display = 'none';
                collapse.style.display = 'block';
                document.body.style.overflow = 'hidden';
            } else {
                expand.style.display = 'block';
                collapse.style.display = 'none';
                document.body.style.overflow = '';
            }
        });
        // ESC to exit fullscreen
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && container.classList.contains('fullscreen')) {
                fsBtn.click();
            }
        });
    }
    // Remove welcome on first message
    const removeWelcome = (logId) => {
        const log = document.getElementById(logId);
        const welcome = log?.querySelector('.nova-welcome');
        if (welcome) welcome.remove();
    };
    const chatSend = document.getElementById('chat-send');
    if (chatSend) chatSend.addEventListener('click', () => removeWelcome('chat-log'), {once: true});
    const visionGo = document.getElementById('vision-go');
    if (visionGo) visionGo.addEventListener('click', () => removeWelcome('vision-log'), {once: true});
});
</script>
