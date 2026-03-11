(function () {
    'use strict';

    const config = window.ailinuxAuth || {};
    const loginForm = document.getElementById('ailinux-login-form');

    function getRedirectUrl() {
        if (loginForm && loginForm.dataset && loginForm.dataset.redirect) {
            return loginForm.dataset.redirect;
        }
        return config.defaultRedirect || '/';
    }

    function normalizeUrl(url) {
        return (url || '').replace(/\/+$/, '');
    }

    function setMessage(message, type) {
        const messageEl = document.getElementById('ailinux-login-message');
        if (!messageEl) {
            return;
        }
        messageEl.textContent = message;
        messageEl.className = type ? ` ${type}`.trim() : '';
        messageEl.style.display = 'block';
    }

    function extractAuthData(payload) {
        const data = payload || {};
        const nested = data.data || data.user || {};
        return {
            token: data.token || data.access_token || data.jwt || nested.token || nested.access_token || '',
            email: data.email || nested.email || '',
            tier: data.tier || nested.tier || nested.plan || '',
            clientId: data.client_id || data.clientId || nested.client_id || nested.clientId || '',
            name: data.name || nested.name || nested.display_name || nested.full_name || ''
        };
    }

    async function postJson(url, body) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        const text = await response.text();
        let data;
        try {
            data = JSON.parse(text);
        } catch (err) {
            data = { raw: text };
        }

        return { ok: response.ok, status: response.status, data };
    }

    async function loginWithApi(email, password) {
        const base = config.apiEndpoint || '';
        const endpoints = [
            `${base}/v1/auth/login`,
            `${base}/v1/client/auth/login`
        ];

        for (const endpoint of endpoints) {
            try {
                const result = await postJson(endpoint, { email, password });
                if (!result.ok) {
                    continue;
                }
                const authData = extractAuthData(result.data);
                if (authData.token && authData.email) {
                    return authData;
                }
            } catch (err) {
                // Try next endpoint
            }
        }

        throw new Error('Login failed');
    }

    function persistAuth(authData) {
        if (authData.token) {
            localStorage.setItem('ailinux_token', authData.token);
        }
        if (authData.email) {
            localStorage.setItem('ailinux_email', authData.email);
        }
        if (authData.tier) {
            localStorage.setItem('ailinux_tier', authData.tier);
        }
        if (authData.clientId) {
            localStorage.setItem('ailinux_client_id', authData.clientId);
        }
    }

    async function syncWordPress(authData) {
        if (!config.syncUrl) {
            return { ok: false };
        }

        const response = await fetch(config.syncUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-WP-Nonce': config.nonce || ''
            },
            body: JSON.stringify({
                email: authData.email,
                token: authData.token,
                tier: authData.tier,
                client_id: authData.clientId,
                name: authData.name
            })
        });

        const payload = await response.json();
        return {
            ok: response.ok && payload && payload.success,
            data: payload
        };
    }

    window.ailinuxLogin = async function () {
        const emailEl = document.getElementById('ailinux-email');
        const passwordEl = document.getElementById('ailinux-password');
        const button = loginForm ? loginForm.querySelector('button') : null;

        if (!emailEl || !passwordEl) {
            return;
        }

        const email = emailEl.value.trim();
        const password = passwordEl.value;

        if (!email || !password) {
            setMessage('Bitte Email und Passwort eingeben.', 'error');
            return;
        }

        if (button) {
            button.disabled = true;
        }
        setMessage('Login laeuft...', 'success');

        try {
            const authData = await loginWithApi(email, password);
            persistAuth(authData);

            const syncResult = await syncWordPress(authData);
            if (!syncResult.ok) {
                setMessage('WordPress Login fehlgeschlagen.', 'error');
                return;
            }

            const redirectUrl = getRedirectUrl();
            const canAdmin = syncResult.data && syncResult.data.can_admin;

            if (normalizeUrl(redirectUrl) === normalizeUrl(config.adminUrl) && !canAdmin) {
                window.location.href = config.defaultRedirect || '/';
                return;
            }

            if (canAdmin && redirectUrl) {
                window.location.href = redirectUrl;
                return;
            }

            window.location.href = redirectUrl || config.defaultRedirect || '/';
        } catch (err) {
            setMessage('Login fehlgeschlagen. Bitte Zugangsdaten pruefen.', 'error');
        } finally {
            if (button) {
                button.disabled = false;
            }
        }
    };
})();
