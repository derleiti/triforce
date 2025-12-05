<?php
/**
 * Static page template
 *
 * @package Ailinux_Nova_Dark
 */

get_header();
?>
<div class="container page-container" data-scroll-section>
    <div class="single-layout">
        <div class="single-content">
            <?php
            while ( have_posts() ) :
                the_post();
                get_template_part( 'template-parts/content', 'single' );

                if ( comments_open() || get_comments_number() ) {
                    comments_template();
                }
            endwhile;
            ?>
        </div>
        <?php if ( is_active_sidebar( 'sidebar-1' ) ) : ?>
            <aside class="single-sidebar" role="complementary">
                <?php dynamic_sidebar( 'sidebar-1' ); ?>
            </aside>
        <?php endif; ?>
    </div>
</div>
<?php
get_footer();
