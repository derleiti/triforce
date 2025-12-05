<?php
/**
 * Plugin Name: AILinux – Consent Conditional Scripts
 * Description: Lädt optionale Scripts nur nach erteilter Einwilligung (Beispiel).
 * Author: AILinux
 * Version: 1.0.0
 */

/**
 * Beispiel: Analytics-Scripts nur bei Statistik-Einwilligung laden
 *
 * Passe die Script-URLs und -Handles nach deinen Bedürfnissen an.
 * Verfügbare Consent-Funktionen:
 * - cmplz_statistics() - TRUE wenn Statistik erlaubt
 * - cmplz_marketing() - TRUE wenn Marketing erlaubt
 * - cmplz_preferences() - TRUE wenn Präferenzen erlaubt
 */
add_action('wp_enqueue_scripts', function() {

    // Beispiel 1: Google Analytics nur bei Statistik-Consent
    if (function_exists('cmplz_statistics') && cmplz_statistics()) {
        // wp_enqueue_script('google-analytics', 'https://www.googletagmanager.com/gtag/js?id=UA-XXXXXX', [], null, true);
    }

    // Beispiel 2: Nova AI Playground nur bei Statistik-Consent
    // Passe den Pfad zur tatsächlichen playground.js-Datei an
    if (function_exists('cmplz_statistics') && cmplz_statistics()) {
        // wp_enqueue_script(
        //     'nova-playground',
        //     get_stylesheet_directory_uri() . '/js/nova-playground.js',
        //     [],
        //     filemtime(get_stylesheet_directory() . '/js/nova-playground.js'),
        //     true
        // );
    }

    // Beispiel 3: Marketing-Pixel nur bei Marketing-Consent
    if (function_exists('cmplz_marketing') && cmplz_marketing()) {
        // wp_enqueue_script('facebook-pixel', 'https://connect.facebook.net/en_US/fbevents.js', [], null, true);
    }

}, 100); // Hohe Priorität, damit es nach Theme-Scripts läuft

/**
 * Hinweis:
 * Die auskommentierten Beispiele müssen aktiviert und an deine tatsächlichen
 * Script-Pfade angepasst werden. Ersetze die URLs/Pfade mit deinen eigenen.
 */
