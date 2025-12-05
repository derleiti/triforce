<?php
/**
 * Plugin Name: Link Test
 * Description: Einfacher Link-Test
 * Version: 1.0
 * Author: Derleiti
 */

add_shortcode('link_test', function() {
    return '<p><a href="/downloads/test.txt">Test-Link zum Download</a></p>';
});
