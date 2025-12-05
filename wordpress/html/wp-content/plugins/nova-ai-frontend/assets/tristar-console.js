/**
 * TriStar Console - WordPress Admin JavaScript
 */
(function($) {
    'use strict';

    const config = window.novaTriStar || {};
    const frame = document.getElementById('nova-tristar-frame');
    const container = frame ? frame.parentElement : null;
    const status = document.getElementById('nova-tristar-status');
    const refreshBtn = document.getElementById('nova-tristar-refresh-frame');

    if (!frame || !container) {
        return;
    }

    // Track loading state
    let isLoaded = false;

    function setStatus(text, type) {
        if (status) {
            status.textContent = text;
            status.className = 'nova-tristar-status ' + (type || '');
        }
    }

    function setLoading(loading) {
        if (loading) {
            container.classList.add('loading');
            setStatus('Loading...', '');
        } else {
            container.classList.remove('loading');
        }
    }

    // Handle iframe load
    frame.addEventListener('load', function() {
        isLoaded = true;
        setLoading(false);
        setStatus('Connected', 'connected');
    });

    // Handle iframe errors
    frame.addEventListener('error', function() {
        setLoading(false);
        setStatus('Connection Error', 'error');
    });

    // Refresh button
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            setLoading(true);
            frame.src = frame.src;
        });
    }

    // Initial loading state
    setLoading(true);

    // Check if iframe loaded after timeout
    setTimeout(function() {
        if (!isLoaded) {
            setStatus('Slow connection...', '');
        }
    }, 5000);

    // Handle postMessage from iframe (for future auth integration)
    window.addEventListener('message', function(event) {
        // Verify origin
        if (!config.apiBase || !event.origin.includes(new URL(config.apiBase).hostname)) {
            return;
        }

        const data = event.data;

        if (data.type === 'tristar-ready') {
            setStatus('Connected', 'connected');
        } else if (data.type === 'tristar-auth-required') {
            setStatus('Login Required', 'error');
            // Could auto-open login in new tab
        } else if (data.type === 'tristar-error') {
            setStatus('Error: ' + (data.message || 'Unknown'), 'error');
        }
    });

    // Optional: Try WordPress-based auto-authentication
    function tryAutoAuth() {
        if (!config.ajaxUrl || !config.nonce) {
            return;
        }

        $.ajax({
            url: config.ajaxUrl,
            type: 'POST',
            data: {
                action: 'nova_tristar_auth',
                nonce: config.nonce
            },
            success: function(response) {
                if (response.success && response.data) {
                    console.log('[TriStar] Auth response:', response.data);
                    // Session obtained - iframe should pick it up on next load
                }
            },
            error: function(xhr, status, error) {
                console.warn('[TriStar] Auto-auth failed:', error);
            }
        });
    }

    // Attempt auto-auth on load
    tryAutoAuth();

})(jQuery);
