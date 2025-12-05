<?php
/**
 * Related posts block
 *
 * @package Ailinux_Nova_Dark
 */

if ( ! is_singular( 'post' ) ) {
    return;
}

$current_id  = get_the_ID();
$categories  = wp_get_post_categories( $current_id );

if ( empty( $categories ) ) {
    return;
}

$related = new WP_Query([
    'post__not_in'        => [ $current_id ],
    'posts_per_page'      => 3,
    'ignore_sticky_posts' => 1,
    'category__in'        => $categories,
]);

if ( ! $related->have_posts() ) {
    return;
}
?>
<section class="related-posts" aria-label="<?php esc_attr_e( 'Related posts', 'ailinux-nova-dark' ); ?>">
    <div class="related-posts__inner">
        <h2 class="related-posts__title"><?php esc_html_e( 'Verwandte Beitraege', 'ailinux-nova-dark' ); ?></h2>
        <div class="post-grid post-grid--related">
            <?php
            while ( $related->have_posts() ) :
                $related->the_post();
                get_template_part( 'template-parts/content', 'card' );
            endwhile;
            wp_reset_postdata();
            ?>
        </div>
    </div>
</section>
