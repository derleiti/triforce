<?php
/**
 * 404 template
 *
 * @package Ailinux_Nova_Dark
 */

get_header();
?>
<section class="container not-found" data-scroll-section>
    <div class="error-card">
        <h1><?php esc_html_e( 'Page not found', 'ailinux-nova-dark' ); ?></h1>
        <p><?php esc_html_e( 'Die angeforderte Seite existiert nicht oder wurde verschoben.', 'ailinux-nova-dark' ); ?></p>
        <a class="btn" href="<?php echo esc_url( home_url( '/' ) ); ?>"><?php esc_html_e( 'Zur Startseite', 'ailinux-nova-dark' ); ?></a>
    </div>
</section>
<?php
get_footer();
