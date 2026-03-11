<?php
/**
 * LemonSqueezy Konfiguration
 *
 * ANLEITUNG:
 * 1. LemonSqueezy Account erstellen: https://app.lemonsqueezy.com
 * 2. API Key erstellen: Settings → API → New API Key
 * 3. Store ID finden: Settings → Stores → deine Store ID
 * 4. Webhook Secret: Settings → Webhooks → Add Webhook → Secret kopieren
 *
 * Werte ENTWEDER hier eintragen (nur für lokale Entwicklung)
 * ODER in wp-config.php als Konstanten definieren (empfohlen für Produktion).
 *
 * SICHERHEIT: Diese Datei niemals committen! Steht in .gitignore.
 */

// ─── API Key ──────────────────────────────────────────────────────────────────
// Aus LemonSqueezy: Settings → API → New API Key
// Format: lsv2_live_xxxx... (Live) oder lsv2_test_xxxx... (Test)
if (!defined('NOVA_LS_API_KEY')) {
    define('NOVA_LS_API_KEY', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5NGQ1OWNlZi1kYmI4LTRlYTUtYjE3OC1kMjU0MGZjZDY5MTkiLCJqdGkiOiJlNTkxMTY4MjhkNmY3MzVhNDlhOTg0YTgxYzFmYmZmODdiNzUxMjFlOWRlYjJmODY4NzAwYThjMWU4YTZhZDZhZjBhY2QxMTQ1YzY2NjdjZiIsImlhdCI6MTc3MjI4OTQxNC43MDk1MjMsIm5iZiI6MTc3MjI4OTQxNC43MDk1MjYsImV4cCI6MjQwMDk2OTYwMC4wMjg2NzcsInN1YiI6IjI1NzYxMTUiLCJzY29wZXMiOltdfQ.J_z12dqvaP26JcjfLTshGgRfSxMTx6d6U1miif1DseXmMVBGg9twm4RamZZoWhpx3VTS_C0vYsyhhWfs6fLxoALhw_-uUjtyUXj9yKJ4WAj7f6dQfgP1jG08smhqjKhz0ow79tKWP0aSP9zMO_X6djeFaHMc9mvg8_6z543cIuiw3NLO2s8aSnXBauGTqzmri_P9-KBtMsr9mRJH19_2fggU8iyKkCqFEVdCACXWFqGuaTEEiPau6-BfAqFnXialPAdDqSGHSLk4wodfj2E3oGy9n4qKdbHman8j-P6_0dtyX9UDhhgIcv347t_Q0emUK8fJFbtWMUcKRmP0gLKKd6kt1PRGG4Zkk0lmIO_iAoXy9FDBbrJZIo_bGRX9aNzGZMYf_ZIp40F4pcmdl-FAl_IS4d3V-f4CkC6-LAP26nAXYAG1ZFO6XxUGVBSIM7Ea4mPvia_KZ8fT7QZdK_qlANW_Z_DiB2ENNhjFhIPt5H7WRWvAaTEjcX1qNJJfIT8cr6ImO--Se1jiVcMeV5zefdMu_vgFtPCvWRdU6RG4K9qbYUONYf5MMkSIOX-vDyqaYXrhg78-eaPfYNGZJG94ewrjxgKx_rIlJqqowPi7IxL2s-9jeHfNW7OVd5mgBa34kcVqYMoPNYn5mfg5xndF5GUddIJ4dATwAAwHyuy4kfMs');
}

// ─── Store ID ─────────────────────────────────────────────────────────────────
// Aus LemonSqueezy: Settings → Stores → deine numerische Store ID
if (!defined('NOVA_LS_STORE_ID')) {
    define('NOVA_LS_STORE_ID', '#303381');
}

// ─── Webhook Signing Secret ───────────────────────────────────────────────────
// Aus LemonSqueezy: Settings → Webhooks → Add Webhook → Secret
if (!defined('NOVA_LS_WEBHOOK_SECRET')) {
    define('NOVA_LS_WEBHOOK_SECRET', '');
}

// ─── Webhook direkt an WordPress ─────────────────────────────────────────────
// true = WP empfängt Webhooks direkt (Endpunkt: /wp-json/nova-ai/v1/payments/webhook/lemonsqueezy)
if (!defined('NOVA_LS_WEBHOOK_DIRECT')) {
    define('NOVA_LS_WEBHOOK_DIRECT', false);
}

// ─── Test-Modus ───────────────────────────────────────────────────────────────
// true = Test-Modus (keine echten Zahlungen), false = Live-Modus
if (!defined('NOVA_LS_TEST_MODE')) {
    define('NOVA_LS_TEST_MODE', true);
}

// ─── Payment Provider ─────────────────────────────────────────────────────────
// 'lemonsqueezy' wenn API Key gesetzt und NOVA_LS_WEBHOOK_DIRECT = true
// 'stub'         für Tests ohne echte API (Standard)
if (!defined('NOVA_PAYMENT_PROVIDER')) {
    define('NOVA_PAYMENT_PROVIDER', 'lemonsqueezy');
}
