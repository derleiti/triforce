<?php
/**
 * Feedzy license setting field template.
 *
 * @since 3.0.0
 * @package feedzy-rss-feeds-pro
 */

$license_status = apply_filters( 'product_feedzy_license_status', false );
$license_key    = apply_filters( 'product_feedzy_license_key', 'free' );
$license_plan   = apply_filters( 'product_feedzy_license_plan_label', '' );

?>
<div class="form-block fz-license-section">
	<label for="fz-license" class="form-label">
		<?php
		esc_html_e( 'License Key', 'feedzy-rss-feeds-pro' );

		if ( 'valid' === $license_status ) {
			?>
			<span class="fz-license-badge" >
				<?php echo esc_html( $license_plan ); ?>
			</span>
			<?php
		}
		?>
	</label>
	<div class="fz-form-row">
		<div class="fz-form-col-6">
			<div class="fz-form-group">
				<input type="text" id="license_key" class="form-control" value="<?php echo esc_attr( ( ( 'valid' === $license_status ) ? ( str_repeat( '*', 30 ) . substr( $license_key, - 5 ) ) : $license_key ) ); ?>" <?php disabled( true, 'valid' === $license_status ); ?> placeholder="<?php esc_attr_e( 'Enter License Key', 'feedzy-rss-feeds-pro' ); ?>" >
				<div class="help-text pt-8">
					<?php
					$text = sprintf(
							// translators: %s store link.
						__( 'Enter your license from <a href="%s" target="_blank" rel="external noreferrer noopener">Themeisle</a> purchase history in order to get plugin updates.', 'feedzy-rss-feeds-pro' ),
						esc_url( 'https://store.themeisle.com/' )
					);
					if ( 'invalid' === $license_status ) {
						$text = '<span class="dashicons dashicons-dismiss"></span>' . __( 'Invalid license provided', 'feedzy-rss-feeds-pro' );
					} elseif ( 'valid' === $license_status ) {
						$license_data            = get_option( 'feedzy_rss_feeds_pro_license_data', array() );
						$license_expiration_date = false;
						if ( isset( $license_data->expires ) ) {
							$parsed                  = date_parse( $license_data->expires );
							$time                    = mktime( $parsed['hour'], $parsed['minute'], $parsed['second'], $parsed['month'], $parsed['day'], $parsed['year'] );
							$license_expiration_date = gmdate( 'F Y', $time );
						}
						$text = '<span class="dashicons dashicons-yes"></span>' . __( 'Valid — Expires', 'feedzy-rss-feeds-pro' ) . ' ' . $license_expiration_date;
					}
					echo wp_kses(
						$text,
						array(
							'span' => array(
								'class' => true,
							),
							'a'    => array(
								'href'   => true,
								'target' => true,
								'rel'    => true,
							),
						)
					);
					?>
				</div>
			</div>
		</div>
		<div class="fz-form-col-6">
			<div class="fz-form-group">
				<div class="fz-input-group">
					<div class="fz-input-group-btn">
						<?php
						$btn_text = esc_html__( 'Activate', 'feedzy-rss-feeds-pro' );
						if ( 'valid' === $license_status ) {
							$btn_text = esc_html__( 'Deactivate', 'feedzy-rss-feeds-pro' );
						}
						?>
						<input type="hidden" value="<?php echo esc_attr( 'valid' === $license_status ? $license_key : '' ); ?>" name="license_key">
						<input type="hidden" name="nonce" value="<?php echo esc_attr( wp_create_nonce( FEEDZY_PRO_BASE ) ); ?>">
						<input type="hidden" name="action" value="feedzy_ti_toggle_license">
						<input type="hidden" name="_action" value="<?php echo 'valid' === $license_status ? 'deactivate' : 'activate'; ?>">
						<button id="check_ti_license" type="button" class="btn btn-outline-primary"<?php echo empty( $license_key ) ? ' disabled' : ''; ?>> <?php echo esc_html( $btn_text ); ?> <span class="dashicons dashicons-update"></span></button>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
