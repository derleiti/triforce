<?php
/**
 * Search form template
 *
 * @package Ailinux_Nova_Dark
 */
?>
<form role="search" method="get" class="search-form" action="<?php echo esc_url( home_url( '/' ) ); ?>">
    <label class="screen-reader-text" for="search-field"><?php esc_html_e( 'Search for:', 'ailinux-nova-dark' ); ?></label>
    <input type="search" id="search-field" class="search-field" placeholder="<?php esc_attr_e( 'Suche...', 'ailinux-nova-dark' ); ?>" value="<?php echo esc_attr( get_search_query() ); ?>" name="s" />
    <button type="submit" class="search-submit"><?php esc_html_e( 'Search', 'ailinux-nova-dark' ); ?></button>
</form>
