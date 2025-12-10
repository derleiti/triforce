<?php
/**
 * Erweiterte Pagination mit mehr Seitenzahlen und Sprungmöglichkeiten
 *
 * @package Ailinux_Nova_Dark
 */

global $wp_query;

$total_pages = $wp_query->max_num_pages;
$current_page = max( 1, get_query_var( 'paged' ) );

if ( $total_pages <= 1 ) {
    return;
}

// Berechne Sprungziele
$jump_intervals = array( 10, 25, 50, 100 );
$quick_jumps = array();

foreach ( $jump_intervals as $interval ) {
    $jump_page = $current_page + $interval;
    if ( $jump_page <= $total_pages ) {
        $quick_jumps[] = $jump_page;
    }
    $jump_page = $current_page - $interval;
    if ( $jump_page > 0 ) {
        $quick_jumps[] = $jump_page;
    }
}
$quick_jumps = array_unique( $quick_jumps );
sort( $quick_jumps );

$pagination = paginate_links( [
    'type'      => 'list',
    'prev_text' => '&laquo; ' . __( 'Zurück', 'ailinux-nova-dark' ),
    'next_text' => __( 'Weiter', 'ailinux-nova-dark' ) . ' &raquo;',
    'mid_size'  => 5,
    'end_size'  => 3,
] );

?>
<nav class="pagination-wrapper" aria-label="<?php esc_attr_e( 'Posts navigation', 'ailinux-nova-dark' ); ?>">
    <?php if ( ! empty( $quick_jumps ) ) : ?>
    <div class="pagination-jumps">
        <span class="pagination-jumps-label"><?php esc_html_e( 'Schnellsprung:', 'ailinux-nova-dark' ); ?></span>
        <?php foreach ( $quick_jumps as $jump_page ) : ?>
            <a href="<?php echo esc_url( get_pagenum_link( $jump_page ) ); ?>" class="pagination-jump-link">
                <?php
                $direction = $jump_page > $current_page ? '+' : '';
                $diff = abs( $jump_page - $current_page );
                echo esc_html( sprintf( '%s%d (Seite %d)', $direction, $diff, $jump_page ) );
                ?>
            </a>
        <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <?php if ( $pagination ) : ?>
    <div class="pagination" role="navigation">
        <?php echo wp_kses_post( $pagination ); ?>
    </div>
    <?php endif; ?>

    <div class="pagination-info">
        <?php
        printf(
            esc_html__( 'Seite %1$s von %2$s', 'ailinux-nova-dark' ),
            '<strong>' . number_format_i18n( $current_page ) . '</strong>',
            '<strong>' . number_format_i18n( $total_pages ) . '</strong>'
        );
        ?>
    </div>
</nav>
