<?php
/**
 * Single Topic Content Part - Lead Topic
 * Haupt-Topic mit modernem Design
 */

// Exit if accessed directly
defined( 'ABSPATH' ) || exit;

?>

<article id="bbp-topic-<?php bbp_topic_id(); ?>" class="bbp-lead-topic" data-observe>

	<header class="bbp-lead-topic__header">
  <nav class="bbp-breadcrumb-mini" aria-label="Breadcrumb">
    <a href="<?php echo esc_url( bbp_get_forums_url() ); ?>" data-no-swup>&larr; <?php esc_html_e('Zur Foren-Übersicht','ailinux-nova-dark'); ?></a>
  </nav>
		<div class="bbp-lead-topic__title-wrapper">
			<h1 class="bbp-lead-topic__title"><?php bbp_topic_title(); ?></h1>
			<div class="bbp-lead-topic__badges">
				<?php if ( bbp_is_topic_sticky() ) : ?>
					<span class="bbp-badge bbp-badge--sticky">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
							<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
						</svg>
						Angepinnt
					</span>
				<?php endif; ?>
				<?php if ( bbp_is_topic_closed() ) : ?>
					<span class="bbp-badge bbp-badge--closed">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
							<path d="M7 11V7a5 5 0 0 1 10 0v4"/>
						</svg>
						Geschlossen
					</span>
				<?php endif; ?>
			</div>
		</div>

		<div class="bbp-lead-topic__meta">
			<div class="bbp-topic-author">
				<div class="bbp-topic-author__avatar">
					<?php bbp_topic_author_link( array( 'type' => 'avatar', 'size' => 48 ) ); ?>
				</div>
				<div class="bbp-topic-author__info">
					<div class="bbp-topic-author__name">
						<?php bbp_topic_author_link( array( 'type' => 'name' ) ); ?>
					</div>
					<div class="bbp-topic-author__details">
						<time datetime="<?php bbp_get_topic_post_date( null, true ); ?>">
							<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<circle cx="12" cy="12" r="10"/>
								<polyline points="12 6 12 12 16 14"/>
							</svg>
							<?php bbp_topic_post_date(); ?>
						</time>
						<?php if ( bbp_get_topic_forum_title() ) : ?>
							<span class="bbp-meta-sep">in</span>
							<a href="<?php bbp_forum_permalink( bbp_get_topic_forum_id() ); ?>" class="bbp-topic-forum-link">
								<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
								</svg>
								<?php bbp_topic_forum_title(); ?>
							</a>
						<?php endif; ?>
					</div>
				</div>
			</div>

			<div class="bbp-lead-topic__stats">
				<div class="bbp-topic-stat-card">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
					</svg>
					<div class="bbp-stat-card__content">
						<div class="bbp-stat-card__value"><?php bbp_show_lead_topic() ? bbp_topic_reply_count() : bbp_topic_post_count(); ?></div>
						<div class="bbp-stat-card__label">Antworten</div>
					</div>
				</div>
				<div class="bbp-topic-stat-card">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
						<circle cx="12" cy="7" r="4"/>
					</svg>
					<div class="bbp-stat-card__content">
						<div class="bbp-stat-card__value"><?php bbp_topic_voice_count(); ?></div>
						<div class="bbp-stat-card__label">Teilnehmer</div>
					</div>
				</div>
			</div>
		</div>
	</header>

	<div class="bbp-lead-topic__content">
		<?php do_action( 'bbp_theme_before_topic_content' ); ?>
		<?php bbp_topic_content(); ?>
		<?php do_action( 'bbp_theme_after_topic_content' ); ?>
	</div>

	<?php if ( current_user_can( 'moderate', bbp_get_topic_id() ) || bbp_is_topic_author() ) : ?>
		<footer class="bbp-lead-topic__footer">
			<div class="bbp-lead-topic__actions">
				<?php do_action( 'bbp_theme_before_topic_admin_links' ); ?>
				<?php bbp_topic_admin_links(); ?>
				<?php do_action( 'bbp_theme_after_topic_admin_links' ); ?>
			</div>
		</footer>
	<?php endif; ?>

</article><!-- #bbp-topic-<?php bbp_topic_id(); ?> -->
