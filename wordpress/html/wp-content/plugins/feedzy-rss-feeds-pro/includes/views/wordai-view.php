<?php
$wordai_username = '';
if ( isset( $this->settings['wordai_username'] ) ) {
	$wordai_username = $this->settings['wordai_username'];
}

$wordai_pass = '';
if ( isset( $this->settings['wordai_hash'] ) ) {
	$wordai_pass = $this->settings['wordai_hash'];
}

$_status              = __( 'Invalid', 'feedzy-rss-feeds-pro' );
$wordai_licence       = '';
$license_status_color = '#F00';
$wordai_last_check    = __( 'Never', 'feedzy-rss-feeds-pro' );
if ( isset( $this->settings['wordai_licence'] ) ) {
	$wordai_licence = $this->settings['wordai_licence'];
	if ( 'yes' === $wordai_licence ) {
		$_status              = __( 'Valid', 'feedzy-rss-feeds-pro' );
		$license_status_color = '#62c370';
	}
}
if ( isset( $this->settings['wordai_last_check'] ) ) {
	$wordai_last_check = $this->settings['wordai_last_check'];
}
if ( isset( $this->settings['wordai_message'] ) && ! empty( $this->settings['wordai_message'] ) ) {
	$_status = $this->settings['wordai_message'];
}

$license_label = wp_sprintf(
	// translators: %s the name of 3-rd party service used.
	__( 'The %s account API key', 'feedzy-rss-feeds-pro' ),
	__( 'WordAi', 'feedzy-rss-feeds-pro' )
);

$license_key_placeholder = wp_sprintf(
	// translators: %s the name of 3-rd party service used.
	__( '%s API key', 'feedzy-rss-feeds-pro' ),
	__( 'WordAi', 'feedzy-rss-feeds-pro' )
);

?>			
<div class="fz-form-wrap">
	<div class="form-block">
		<div class="fz-form-group mb-24">
			<label class="form-label"><?php esc_html_e( 'The WordAi account email', 'feedzy-rss-feeds-pro' ); ?>:</label>
			<input type="text" class="form-control" id="wordai_username" name="wordai_username" value="<?php echo esc_attr( $wordai_username ); ?>" placeholder="<?php echo esc_attr( __( 'WordAi Email', 'feedzy-rss-feeds-pro' ) ); ?>"/>
		</div>
		<div class="fz-form-group">
			<label class="form-label"><?php echo esc_html( $license_label ); ?>:</label>
			<div class="fz-input-group">
				<div class="fz-input-group-left">
					<input
						type="password"
						id="wordai_pass"
						class="form-control"
						name="wordai_pass"
						value="<?php echo esc_attr( $wordai_pass ); ?>"
						placeholder="<?php echo esc_attr( $license_key_placeholder ); ?>"
					/>
					<div class="help-text">
						<?php
						echo wp_kses_post(
							wp_sprintf(
								// translators: %1$s is the API status message.
								__( 'API Status: %1$s', 'feedzy-rss-feeds-pro' ),
								wp_sprintf(
									'<span style="color:%1$s;">%2$s</span>',
									$license_status_color,
									$_status
								)
							)
							. ' | '
							. wp_sprintf(
								// translators: %1$s is the date of the last API status check.
								__( 'Last check: %1$s', 'feedzy-rss-feeds-pro' ),
								$wordai_last_check
							)
						);
						?>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<script type="text/javascript">
	function ajaxUpdate( button ) {

		var wordai_data = {
			'wordai_username': jQuery( '#wordai_username' ).val(),
			'wordai_pass': jQuery( '#wordai_pass' ).val(),
		}

		var data = {
			'action': 'update_settings_page',
			'feedzy_settings': wordai_data,
			'_wpnonce': '<?php echo esc_js( wp_create_nonce( 'update_settings_page' ) ); ?>',
		};

		jQuery( button ).prop( 'disabled', true );
		jQuery( button ).html('<?php esc_html_e( 'Checking', 'feedzy-rss-feeds-pro' ); ?> ...');
		jQuery.post( ajaxurl, data, function( response ) {
			jQuery( button ).prop( 'disabled', false );
			jQuery( button ).html('<?php esc_html_e( 'Validate & Save', 'feedzy-rss-feeds-pro' ); ?>');
			location.reload();
		}, 'json');

		return false;
	};
</script>
