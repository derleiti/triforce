<?php
/**
 * Replies Loop - Single Reply
 * Moderne Reply-Darstellung
 */

// Exit if accessed directly
defined( 'ABSPATH' ) || exit;

?>

<article id="post-<?php bbp_reply_id(); ?>" class="bbp-reply <?php echo bbp_get_reply_author_role() === 'bbp_keymaster' ? 'bbp-reply--admin' : ''; ?>" data-observe>

	<div class="bbp-reply__sidebar">
		<div class="bbp-reply__author">
			<div class="bbp-reply-author__avatar">
				<?php bbp_reply_author_link( array( 'type' => 'avatar', 'size' => 80 ) ); ?>
			</div>
			<div class="bbp-reply-author__name">
				<?php bbp_reply_author_link( array( 'type' => 'name' ) ); ?>
			</div>
			<?php if ( $role = bbp_get_reply_author_role() ) : ?>
				<div class="bbp-reply-author__role">
					<?php
					$role_labels = array(
						'bbp_keymaster' => 'Administrator',
						'bbp_moderator' => 'Moderator',
						'bbp_participant' => 'Mitglied',
						'bbp_spectator' => 'Besucher',
						'bbp_blocked' => 'Blockiert'
					);
					echo isset( $role_labels[ $role ] ) ? $role_labels[ $role ] : ucfirst( str_replace( 'bbp_', '', $role ) );
					?>
				</div>
			<?php endif; ?>
			<div class="bbp-reply-author__stats">
				<div class="bbp-author-stat">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
					</svg>
					<span><?php bbp_author_topic_count(); ?> Themen</span>
				</div>
				<div class="bbp-author-stat">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
					</svg>
					<span><?php bbp_author_reply_count(); ?> Antworten</span>
				</div>
			</div>
		</div>
	</div>

	<div class="bbp-reply__main">
		<header class="bbp-reply__header">
			<div class="bbp-reply-meta">
				<a href="<?php bbp_reply_url(); ?>" class="bbp-reply-meta__permalink" title="<?php esc_attr_e( 'Permalink zu dieser Antwort', 'ailinux-nova-dark' ); ?>">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
						<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
					</svg>
					#<?php bbp_reply_id(); ?>
				</a>
				<span class="bbp-reply-meta__sep">•</span>
				<time class="bbp-reply-meta__time" datetime="<?php bbp_get_reply_post_date( null, true ); ?>">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="10"/>
						<polyline points="12 6 12 12 16 14"/>
					</svg>
					<?php bbp_reply_post_date(); ?>
				</time>
			</div>

			<?php if ( current_user_can( 'moderate', bbp_get_reply_id() ) || bbp_is_reply_author( bbp_get_reply_id() ) ) : ?>
				<div class="bbp-reply__actions">
					<?php do_action( 'bbp_theme_before_reply_admin_links' ); ?>
					<?php bbp_reply_admin_links(); ?>
					<?php do_action( 'bbp_theme_after_reply_admin_links' ); ?>
				</div>
			<?php endif; ?>
		</header>

		<div class="bbp-reply__content">
			<?php do_action( 'bbp_theme_before_reply_content' ); ?>
			<?php bbp_reply_content(); ?>
			<?php do_action( 'bbp_theme_after_reply_content' ); ?>
		</div>

	</div>

</article><!-- #post-<?php bbp_reply_id(); ?> -->
