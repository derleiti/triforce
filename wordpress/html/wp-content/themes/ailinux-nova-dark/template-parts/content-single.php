<?php
/**
 * Single content template
 *
 * @package Ailinux_Nova_Dark
 */
?>

<?php
$post_type = get_post_type();
$ailinux_single_words = str_word_count( wp_strip_all_tags( get_post_field( 'post_content', get_the_ID() ) ) );
?>
<article id="post-<?php the_ID(); ?>" <?php post_class( 'single-post' ); ?> <?php echo ( 'post' === $post_type ) ? 'data-observe' : ''; ?> data-words="<?php echo esc_attr( $ailinux_single_words ); ?>">

    <header class="single-post__header">
        <?php if ( 'post' === $post_type ) : ?>
        <div class="single-post__badge">
            <?php
            $categories = get_the_category();
            if ( $categories ) :
                foreach ( $categories as $category ) :
                    ?>
                    <a class="badge" href="<?php echo esc_url( get_category_link( $category ) ); ?>"><?php echo esc_html( $category->name ); ?></a>
                    <?php
                endforeach;
            endif;
            ?>
        </div>
        <?php endif; ?>
        <h1 class="single-post__title"><?php the_title(); ?></h1>
        <?php if ( 'post' === $post_type ) : ?>
        <div class="single-post__meta">
            <span class="author"><?php printf( esc_html__( 'Von %s', 'ailinux-nova-dark' ), esc_html( get_the_author() ) ); ?></span>
            <time datetime="<?php echo esc_attr( get_the_date( DATE_W3C ) ); ?>"><?php echo esc_html( get_the_date() ); ?></time>
            <span class="reading-time" data-reading><?php esc_html_e( 'Loading...', 'ailinux-nova-dark' ); ?></span>
        </div>
        <?php endif; ?>
        <?php if ( has_post_thumbnail() ) : ?>
            <figure class="single-post__figure">
                <?php the_post_thumbnail( 'ailinux-hero', [
                    'loading'  => 'lazy',
                    'decoding' => 'async',
                    'class'    => 'single-post__image',
                ] ); ?>
                <?php if ( get_the_post_thumbnail_caption() ) : ?>
                    <figcaption><?php echo esc_html( get_the_post_thumbnail_caption() ); ?></figcaption>
                <?php endif; ?>
            </figure>
        <?php endif; ?>
    </header>

    <nav class="post-toc" data-toc hidden>
        <h2 class="post-toc__title"><?php esc_html_e( 'Inhalt', 'ailinux-nova-dark' ); ?></h2>
        <ol class="post-toc__list"></ol>
    </nav>

    <div class="single-post__content">
        <?php
        the_content();

        wp_link_pages( [
            'before' => '<nav class="page-links">' . esc_html__( 'Pages:', 'ailinux-nova-dark' ),
            'after'  => '</nav>',
        ] );
        ?>
    </div>

    <?php if ( 'post' === $post_type ) : ?>
    <footer class="single-post__footer">
        <?php the_tags( '<div class="post-tags">', '', '</div>' ); ?>
        <div class="share-hint" role="note"><?php esc_html_e( 'Teile diesen Beitrag ueber deine bevorzugten Kanaele.', 'ailinux-nova-dark' ); ?></div>
    </footer>
    <?php endif; ?>
</article>
