<?php
/**
 * Hero post template
 *
 * @package Ailinux_Nova_Dark
 */

$layout = $args['layout'] ?? 'grid';
?>
<?php
$hero_classes = [ 'hero-post', 'hero-post--' . sanitize_html_class( $layout ) ];
?>

<?php
$ailinux_hero_words = str_word_count( wp_strip_all_tags( get_post_field( 'post_content', get_the_ID() ) ) );
?>
<article id="hero-post-<?php the_ID(); ?>" <?php post_class( $hero_classes ); ?> data-observe data-words="<?php echo esc_attr( $ailinux_hero_words ); ?>">

    <div class="hero-post__media">
        <?php if ( has_post_thumbnail() ) : ?>
            <a href="<?php the_permalink(); ?>">
                <?php the_post_thumbnail( 'ailinux-hero', [
                    'loading'  => 'lazy',
                    'decoding' => 'async',
                    'class'    => 'hero-post__image',
                ] ); ?>
            </a>
        <?php endif; ?>
    </div>
    <div class="hero-post__content">
        <div class="hero-post__labels">
            <?php
            $categories = get_the_category();
            if ( $categories ) :
                ?>
                <span class="badge badge-category"><?php echo esc_html( $categories[0]->name ); ?></span>
            <?php endif; ?>
            <time datetime="<?php echo esc_attr( get_the_date( DATE_W3C ) ); ?>"><?php echo esc_html( get_the_date() ); ?></time>
        </div>
        <h1 class="hero-post__title"><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h1>
        <p class="hero-post__excerpt"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 40, '...' ) ); ?></p>
        <div class="hero-post__meta">
            <span class="reading-time" data-reading><?php esc_html_e( 'Loading...', 'ailinux-nova-dark' ); ?></span>
            <span class="hero-post__author"><?php echo esc_html( get_the_author() ); ?></span>
        </div>
        <a class="btn btn-primary" href="<?php the_permalink(); ?>"><?php esc_html_e( 'Weiterlesen', 'ailinux-nova-dark' ); ?></a>
    </div>
</article>
