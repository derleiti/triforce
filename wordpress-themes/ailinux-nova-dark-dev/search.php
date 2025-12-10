<?php
/**
 * Search results
 *
 * @package Ailinux_Nova_Dark
 */

get_header();
?>
<section class="container search-container" data-scroll-section>
    <header class="archive-header">
        <h1 class="archive-title">
            <?php printf( esc_html__( 'Search: %s', 'ailinux-nova-dark' ), '<span>' . esc_html( get_search_query() ) . '</span>' ); ?>
        </h1>
    </header>
    <?php if ( have_posts() ) : ?>
        <div class="post-grid">
            <?php
            while ( have_posts() ) :
                the_post();
                get_template_part( 'template-parts/content', 'card' );
            endwhile;
            ?>
        </div>
        <?php get_template_part( 'template-parts/pagination' ); ?>
    <?php else : ?>
        <?php get_template_part( 'template-parts/content', 'none' ); ?>
    <?php endif; ?>
</section>
<?php
get_footer();
