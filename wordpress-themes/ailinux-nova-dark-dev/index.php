<?php
/**
 * Default index template
 *
 * @package Ailinux_Nova_Dark
 */

global $ailinux_nova_dark_layout;
get_header();
?>
<section class="standard-loop container" data-scroll-section>
    <?php if ( have_posts() ) : ?>
        <header class="archive-header">
            <h1 class="archive-title"><?php esc_html_e( 'Latest Articles', 'ailinux-nova-dark' ); ?></h1>
        </header>
        <?php get_template_part( 'template-parts/pagination' ); ?>
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
