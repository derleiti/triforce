<?php
/**
 * Footer template
 *
 * @package Ailinux_Nova_Dark
 */
?>
    </main>
</div><!-- #swup -->
<footer id="site-footer" class="site-footer" data-footer>
    <div class="footer-top" aria-hidden="true"></div>
    <div class="container footer-grid">
        <?php if ( is_active_sidebar( 'footer-widgets' ) ) : ?>
            <?php dynamic_sidebar( 'footer-widgets' ); ?>
        <?php endif; ?>
    </div>
    <div class="footer-bottom" style="text-align: center;">
        <p>&copy; 2025 TechMediaGamesBlog@ailinux.me . Alle Rechte vorbehalten.</p>
        <nav class="footer-legal-links" aria-label="<?php esc_attr_e( 'Legal Links', 'ailinux-nova-dark' ); ?>">
            <?php
            $privacy_page = get_option( 'wp_page_for_privacy_policy' );
            if ( $privacy_page ) {
                printf(
                    '<a href="%s">%s</a>',
                    esc_url( get_permalink( $privacy_page ) ),
                    esc_html__( 'Datenschutzerklärung', 'ailinux-nova-dark' )
                );
            }
            ?>
            <a class="cmplz-manage-consent" href="#"><?php esc_html_e( 'Einwilligungen verwalten', 'ailinux-nova-dark' ); ?></a>
            <?php
            $imprint_page = get_page_by_path( 'impressum' );
            if ( $imprint_page ) {
                printf(
                    '<a href="%s">%s</a>',
                    esc_url( get_permalink( $imprint_page ) ),
                    esc_html__( 'Impressum', 'ailinux-nova-dark' )
                );
            }
            ?>
        </nav>
    </div>
</footer>
<?php wp_footer(); ?>
</body>
</html>