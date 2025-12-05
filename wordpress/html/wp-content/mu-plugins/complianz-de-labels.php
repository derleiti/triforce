<?php
/**
 * Plugin Name: AILinux – Complianz DE Labels
 * Description: Vereinheitlicht die deutschen Labels des Consent-Banners via gettext.
 * Author: AILinux
 * Version: 1.0.0
 */

add_filter('gettext', function($translated, $text, $domain){
    if ($domain === 'complianz-gdpr') {
        $map = [
            'Manage Consent'                => 'Einwilligungen verwalten',
            'Accept'                        => 'Alle akzeptieren',
            'Accept all'                    => 'Alle akzeptieren',
            'Deny'                          => 'Nur funktionale Cookies',
            'View preferences'              => 'Einstellungen',
            'Save preferences'              => 'Auswahl speichern',
            'Functional'                    => 'Funktional',
            'Functional Always active'      => 'Funktional (immer aktiv)',
            'Preferences'                   => 'Präferenzen',
            'Statistics'                    => 'Statistik',
            'Marketing'                     => 'Marketing',
            'Always active'                 => 'Immer aktiv',
            'Cookie Policy'                 => 'Cookie-Richtlinie',
            'Privacy Statement'             => 'Datenschutzerklärung',
            'Manage {vendor_count} vendors' => 'Dienste verwalten',
        ];
        if (isset($map[$text])) return $map[$text];
    }
    return $translated;
}, 10, 3);
