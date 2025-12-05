<?php
/**
 * Single post template
 *
 * @package Ailinux_Nova_Dark
 */

get_header();
?>
<div class="container single-container" data-scroll-section>
    <div class="single-layout">
        <div class="single-content">
            <?php
            while ( have_posts() ) :
                the_post();
                get_template_part( 'template-parts/content', 'single' );

                the_post_navigation( [
                    'prev_text' => '<span class="nav-subtitle">' . esc_html__( 'Previous', 'ailinux-nova-dark' ) . '</span><span class="nav-title">%title</span>',
                    'next_text' => '<span class="nav-subtitle">' . esc_html__( 'Next', 'ailinux-nova-dark' ) . '</span><span class="nav-title">%title</span>',
                ] );

                get_template_part( 'template-parts/related-posts' );

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
