<?php
/**
 * Post card template
 *
 * @package Ailinux_Nova_Dark
 */
?>

<?php
$post_type = get_post_type();
$ailinux_card_words = str_word_count( wp_strip_all_tags( get_post_field( 'post_content', get_the_ID() ) ) );
?>
<article id="post-<?php the_ID(); ?>" <?php post_class( 'post-card' ); ?> data-observe data-words="<?php echo esc_attr( $ailinux_card_words ); ?>">

    <a class="post-card__thumb" href="<?php the_permalink(); ?>" aria-hidden="true" tabindex="-1">
        <?php if ( has_post_thumbnail() ) : ?>
            <?php the_post_thumbnail( 'ailinux-card', [
                'loading'  => 'lazy',
                'decoding' => 'async',
                'class'    => 'post-card__image',
            ] ); ?>
        <?php else : ?>
            <div class="post-card__placeholder" aria-hidden="true"></div>
        <?php endif; ?>
    </a>
    <div class="post-card__body">
        <?php if ( 'post' === $post_type ) : ?>
        <div class="post-card__meta">
            <?php
            $categories = get_the_category();
            $primary_category = $categories ? $categories[0]->name : __( 'General', 'ailinux-nova-dark' );
            ?>
            <span class="badge badge-category"><?php echo esc_html( $primary_category ); ?></span>
            <time datetime="<?php echo esc_attr( get_the_date( DATE_W3C ) ); ?>"><?php echo esc_html( get_the_date() ); ?></time>
            <span class="reading-time" data-reading><?php esc_html_e( 'Loading...', 'ailinux-nova-dark' ); ?></span>
        </div>
        <?php endif; ?>
        <h2 class="post-card__title">
            <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
        </h2>
        <p class="post-card__excerpt"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 26, '...' ) ); ?></p>
        <a class="post-card__cta" href="<?php the_permalink(); ?>"><?php esc_html_e( 'Weiterlesen', 'ailinux-nova-dark' ); ?></a>
    </div>
</article>
