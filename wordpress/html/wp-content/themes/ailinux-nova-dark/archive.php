<?php
/**
 * Archive template
 *
 * @package Ailinux_Nova_Dark
 */

get_header();
?>
<section class="container archive-container" data-scroll-section>
    <header class="archive-header">
        <h1 class="archive-title"><?php the_archive_title(); ?></h1>
        <?php if ( get_the_archive_description() ) : ?>
            <p class="archive-description"><?php the_archive_description(); ?></p>
        <?php endif; ?>
    </header>
    <?php if ( have_posts() ) : ?>
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
