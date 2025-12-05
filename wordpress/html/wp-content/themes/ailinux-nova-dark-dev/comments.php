<?php
/**
 * Comments template
 *
 * @package Ailinux_Nova_Dark
 */

if ( post_password_required() ) {
    return;
}
?>
<div id="comments" class="comments-area" data-scroll-section>
    <?php if ( have_comments() ) : ?>
        <h2 class="comments-title">
            <?php
            $count = get_comments_number();
            printf(
                esc_html( _n( '%s Comment', '%s Comments', $count, 'ailinux-nova-dark' ) ),
                number_format_i18n( $count )
            );
            ?>
        </h2>

        <ol class="comment-list">
            <?php
            wp_list_comments( [
                'style'      => 'ol',
                'short_ping' => true,
                'avatar_size'=> 48,
            ] );
            ?>
        </ol>

        <?php if ( get_comment_pages_count() > 1 && get_option( 'page_comments' ) ) : ?>
            <nav class="comment-navigation" aria-label="<?php esc_attr_e( 'Comment navigation', 'ailinux-nova-dark' ); ?>">
                <span class="nav-previous"><?php previous_comments_link( esc_html__( 'Older Comments', 'ailinux-nova-dark' ) ); ?></span>
                <span class="nav-next"><?php next_comments_link( esc_html__( 'Newer Comments', 'ailinux-nova-dark' ) ); ?></span>
            </nav>
        <?php endif; ?>
    <?php endif; ?>

    <?php if ( ! comments_open() ) : ?>
        <p class="no-comments"><?php esc_html_e( 'Comments are closed.', 'ailinux-nova-dark' ); ?></p>
    <?php endif; ?>

    <?php
    comment_form( [
        'class_form'         => 'comment-form styled-form',
        'title_reply_before' => '<h3 id="reply-title" class="comment-reply-title">',
        'title_reply_after'  => '</h3>',
    ] );
    ?>
</div>
