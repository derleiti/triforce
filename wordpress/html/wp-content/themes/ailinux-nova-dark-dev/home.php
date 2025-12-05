<?php
/**
 * Blog home template
 *
 * @package Ailinux_Nova_Dark
 */

global $wp_query;
get_header();

$sticky_posts = get_option( 'sticky_posts', [] );
$hero_post    = null;

if ( ! empty( $sticky_posts ) ) {
    $hero_query = new WP_Query([
        'post__in'            => $sticky_posts,
        'posts_per_page'      => 1,
        'ignore_sticky_posts' => 1,
    ]);

    if ( $hero_query->have_posts() ) {
        $hero_post = $hero_query->posts[0];
    }
    wp_reset_postdata();
}

if ( ! $hero_post && $wp_query->have_posts() ) {
    $hero_post = $wp_query->posts[0];
}

$hero_id      = $hero_post ? $hero_post->ID : 0;
$hero_layout  = get_theme_mod( 'ailinux_nova_dark_hero_layout', 'grid' );
?>
<section class="home-hero" data-scroll-section>
    <div class="container">
        <?php if ( $hero_post ) :
            $GLOBALS['post'] = $hero_post; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited
            setup_postdata( $hero_post );
            get_template_part( 'template-parts/content', 'hero', [ 'layout' => $hero_layout ] );
            wp_reset_postdata();
        else : ?>
            <p class="no-hero"><?php esc_html_e( 'No featured posts available yet.', 'ailinux-nova-dark' ); ?></p>
        <?php endif; ?>
    </div>
</section>
<section class="home-grid" data-scroll-section data-layout="<?php echo esc_attr( $hero_layout ); ?>">
    <div class="container">
        <?php if ( have_posts() ) : ?>
            <?php get_template_part( 'template-parts/pagination' ); ?>
            <div class="post-grid" data-interactive>
                <?php
                while ( have_posts() ) :
                    the_post();

                    if ( get_the_ID() === $hero_id ) {
                        continue;
                    }

                    get_template_part( 'template-parts/content', 'card' );
                endwhile;
                ?>
            </div>
            <?php get_template_part( 'template-parts/pagination' ); ?>
        <?php else : ?>
            <?php get_template_part( 'template-parts/content', 'none' ); ?>
        <?php endif; ?>
    </div>
</section>
<?php
get_footer();
