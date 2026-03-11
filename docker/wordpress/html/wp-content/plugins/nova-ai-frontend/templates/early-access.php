<?php
defined('ABSPATH') || exit;
$service = \NovAI\Services\EarlyAccessService::instance();
$stats = $service->get_stats();
?>
<div class="nov-early-access">
    <div class="nov-ea-header">
        <div class="nov-ea-badge">🎉 EARLY ACCESS BETA</div>
        <h2>Get Tier 1 (Pro) Access for FREE</h2>
        <p>Limited to <strong><?php echo $stats['available_slots']; ?></strong> slots remaining!</p>
    </div>

    <?php if ($stats['is_open']): ?>
    <form class="nov-ea-form" id="nov-ea-form">
        <div class="nov-form-group">
            <label for="nov-ea-name">Name (optional)</label>
            <input type="text" id="nov-ea-name" name="name" placeholder="Your name">
        </div>
        <div class="nov-form-group">
            <label for="nov-ea-email">Email *</label>
            <input type="email" id="nov-ea-email" name="email" placeholder="your@email.com" required>
        </div>
        <div class="nov-form-group">
            <label for="nov-ea-password">Password *</label>
            <input type="password" id="nov-ea-password" name="password" placeholder="Min. 6 characters" required minlength="6">
        </div>
        <button type="submit" class="nov-ea-submit">
            <span class="nov-ea-submit-text">🚀 Claim Free Pro Access</span>
            <span class="nov-ea-submit-loading" style="display:none;">Processing...</span>
        </button>
    </form>
    <div class="nov-ea-message" id="nov-ea-message" style="display:none;"></div>
    <?php else: ?>
    <div class="nov-ea-waitlist">
        <p>⏳ All beta slots are currently claimed. Join the waitlist:</p>
        <form class="nov-ea-form" id="nov-ea-waitlist-form">
            <div class="nov-form-group">
                <input type="email" name="email" placeholder="your@email.com" required>
            </div>
            <button type="submit">Join Waitlist</button>
        </form>
    </div>
    <?php endif; ?>

    <div class="nov-ea-features">
        <h3>What you get with Tier 1 (Pro):</h3>
        <ul>
            <li>✅ 250,000 tokens/month</li>
            <li>✅ 600+ AI Models (GPT-4, Claude, Gemini, Llama...)</li>
            <li>✅ Full MCP Tool Access</li>
            <li>✅ CLI Agent Integration</li>
            <li>✅ Email Support</li>
        </ul>
    </div>
</div>

<style>
.nov-early-access {
    max-width: 500px;
    margin: 2rem auto;
    background: var(--nov-bg-secondary, #161b22);
    border: 1px solid var(--nov-border, #30363d);
    border-radius: 12px;
    padding: 2rem;
}
.nov-ea-header {
    text-align: center;
    margin-bottom: 1.5rem;
}
.nov-ea-badge {
    display: inline-block;
    background: linear-gradient(135deg, #238636, #2ea043);
    color: white;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 1rem;
}
.nov-ea-header h2 {
    color: #e6edf3;
    margin: 0 0 0.5rem;
}
.nov-ea-header p {
    color: #8b949e;
    margin: 0;
}
.nov-form-group {
    margin-bottom: 1rem;
}
.nov-form-group label {
    display: block;
    color: #8b949e;
    font-size: 14px;
    margin-bottom: 6px;
}
.nov-form-group input {
    width: 100%;
    background: #0d1117;
    border: 1px solid #30363d;
    color: #e6edf3;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 15px;
    box-sizing: border-box;
}
.nov-form-group input:focus {
    outline: none;
    border-color: #58a6ff;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.15);
}
.nov-ea-submit {
    width: 100%;
    background: linear-gradient(135deg, #58a6ff, #a371f7);
    border: none;
    color: white;
    padding: 14px 24px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}
.nov-ea-submit:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(88,166,255,0.3);
}
.nov-ea-message {
    margin-top: 1rem;
    padding: 1rem;
    border-radius: 8px;
}
.nov-ea-message.success {
    background: rgba(63,185,80,0.1);
    border: 1px solid #3fb950;
    color: #3fb950;
}
.nov-ea-message.error {
    background: rgba(248,81,73,0.1);
    border: 1px solid #f85149;
    color: #f85149;
}
.nov-ea-features {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid #30363d;
}
.nov-ea-features h3 {
    color: #e6edf3;
    font-size: 14px;
    margin: 0 0 1rem;
}
.nov-ea-features ul {
    list-style: none;
    padding: 0;
    margin: 0;
}
.nov-ea-features li {
    color: #8b949e;
    padding: 6px 0;
    font-size: 14px;
}
</style>

<script>
document.getElementById('nov-ea-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('.nov-ea-submit');
    const submitText = form.querySelector('.nov-ea-submit-text');
    const submitLoading = form.querySelector('.nov-ea-submit-loading');
    const messageEl = document.getElementById('nov-ea-message');
    
    submitBtn.disabled = true;
    submitText.style.display = 'none';
    submitLoading.style.display = 'inline';
    
    try {
        const formData = new FormData();
        formData.append('action', 'nov_ai_register');
        formData.append('nonce', novAiConfig.nonce);
        formData.append('name', form.querySelector('[name="name"]').value);
        formData.append('email', form.querySelector('[name="email"]').value);
        formData.append('password', form.querySelector('[name="password"]').value);
        
        const response = await fetch(novAiConfig.ajaxUrl, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        messageEl.style.display = 'block';
        if (data.success) {
            messageEl.className = 'nov-ea-message success';
            messageEl.innerHTML = '✅ ' + data.data.message;
            form.style.display = 'none';
        } else {
            messageEl.className = 'nov-ea-message error';
            messageEl.textContent = '❌ ' + (data.data?.message || 'Registration failed');
        }
    } catch (err) {
        messageEl.style.display = 'block';
        messageEl.className = 'nov-ea-message error';
        messageEl.textContent = '❌ Connection error. Please try again.';
    }
    
    submitBtn.disabled = false;
    submitText.style.display = 'inline';
    submitLoading.style.display = 'none';
});
</script>
