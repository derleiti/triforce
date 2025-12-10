<?php
/**
 * Topics Loop - Custom Template
 * Modernes Card-Design für Topics
 */

// Exit if accessed directly
defined( 'ABSPATH' ) || exit;

do_action( 'bbp_template_before_topics_loop' ); ?>

<div class="bbp-topics-list">

	<?php while ( bbp_topics() ) : bbp_the_topic(); ?>

		<article class="bbp-topic-item <?php echo bbp_is_topic_sticky() ? 'bbp-topic-item--sticky' : ''; ?> <?php echo bbp_is_topic_closed() ? 'bbp-topic-item--closed' : ''; ?>" data-observe>

			<div class="bbp-topic-item__main">
				<div class="bbp-topic-item__badges">
					<?php if ( bbp_is_topic_sticky() ) : ?>
						<span class="bbp-badge bbp-badge--sticky">
							<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
								<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
							</svg>
							Angepinnt
						</span>
					<?php endif; ?>
					<?php if ( bbp_is_topic_closed() ) : ?>
						<span class="bbp-badge bbp-badge--closed">
							<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
								<path d="M7 11V7a5 5 0 0 1 10 0v4"/>
							</svg>
							Geschlossen
						</span>
					<?php endif; ?>
				</div>

				<h3 class="bbp-topic-item__title">
					<a href="<?php bbp_topic_permalink(); ?>" class="bbp-topic-item__link">
						<?php bbp_topic_title(); ?>
					</a>
				</h3>

				<div class="bbp-topic-item__meta">
					<span class="bbp-topic-meta__author">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
							<circle cx="12" cy="7" r="4"/>
						</svg>
						<?php
						printf(
							'<a href="%s">%s</a>',
							bbp_get_topic_author_link( array( 'type' => 'url' ) ),
							bbp_get_topic_author()
						);
						?>
					</span>
					<span class="bbp-topic-meta__sep">•</span>
					<span class="bbp-topic-meta__time">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<circle cx="12" cy="12" r="10"/>
							<polyline points="12 6 12 12 16 14"/>
						</svg>
						<?php bbp_topic_post_date(); ?>
					</span>
					<?php if ( bbp_get_topic_forum_title() ) : ?>
						<span class="bbp-topic-meta__sep">•</span>
						<span class="bbp-topic-meta__forum">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
							</svg>
							<a href="<?php bbp_forum_permalink( bbp_get_topic_forum_id() ); ?>">
								<?php bbp_topic_forum_title(); ?>
							</a>
						</span>
					<?php endif; ?>
				</div>
			</div>

			<div class="bbp-topic-item__stats">
				<div class="bbp-topic-stat">
					<span class="bbp-topic-stat__value"><?php bbp_show_lead_topic() ? bbp_topic_reply_count() : bbp_topic_post_count(); ?></span>
					<span class="bbp-topic-stat__label">Antworten</span>
				</div>
				<div class="bbp-topic-stat">
					<span class="bbp-topic-stat__value"><?php bbp_topic_voice_count(); ?></span>
					<span class="bbp-topic-stat__label">Stimmen</span>
				</div>
			</div>

			<?php if ( bbp_get_topic_last_active_time() ) : ?>
				<div class="bbp-topic-item__activity">
					<div class="bbp-topic-freshness">
						<div class="bbp-topic-freshness__label">Letzte Aktivität</div>
						<div class="bbp-topic-freshness__time"><?php bbp_topic_last_active_time(); ?></div>
						<?php if ( bbp_get_topic_last_active_id() ) : ?>
							<div class="bbp-topic-freshness__author">
								von <?php
								printf(
									'<a href="%s">%s</a>',
									bbp_get_user_profile_url( bbp_get_topic_last_active_id() ),
									get_the_author_meta( 'display_name', bbp_get_topic_last_active_id() )
								);
								?>
							</div>
						<?php endif; ?>
					</div>
				</div>
			<?php endif; ?>

		</article>

	<?php endwhile; ?>

</div><!-- .bbp-topics-list -->

<?php do_action( 'bbp_template_after_topics_loop' ); ?>
