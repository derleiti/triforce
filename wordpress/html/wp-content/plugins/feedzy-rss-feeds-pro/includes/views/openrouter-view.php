<?php
$openrouter_api_key = '';
if ( isset( $this->settings['openrouter_api_key'] ) ) {
	$openrouter_api_key = $this->settings['openrouter_api_key'];
}

$openrouter_api_model = '';
if ( isset( $this->settings['openrouter_api_model'] ) ) {
	$openrouter_api_model = $this->settings['openrouter_api_model'];
}

$_status               = 'Invalid';
$openrouter_licence    = '';
$license_status_color  = '#F00';
$openrouter_last_check = __( 'Never', 'feedzy-rss-feeds-pro' );
if ( isset( $this->settings['openrouter_licence'] ) ) {
	$openrouter_licence = $this->settings['openrouter_licence'];
	if ( 'yes' === $openrouter_licence ) {
		$_status              = 'Valid';
		$license_status_color = '#62c370';
	}
}
if ( isset( $this->settings['openrouter_last_check'] ) ) {
	$openrouter_last_check = $this->settings['openrouter_last_check'];
}
if ( isset( $this->settings['openrouter_message'] ) && ! empty( $this->settings['openrouter_message'] ) ) {
	$_status = $this->settings['openrouter_message'];
}

$license_label = wp_sprintf(
	// translators: %s the name of 3-rd party service used.
	__( 'The %s account API key', 'feedzy-rss-feeds-pro' ),
	__( 'OpenRouter', 'feedzy-rss-feeds-pro' )
);

$license_key_placeholder = wp_sprintf(
	// translators: %s the name of 3-rd party service used.
	__( '%s API key', 'feedzy-rss-feeds-pro' ),
	__( 'OpenRouter', 'feedzy-rss-feeds-pro' )
);

?>
<div class="fz-form-wrap">
	<div class="form-block">
		<div class="fz-form-group mb-24">
			<label class="form-label"><?php echo esc_html( $license_label ); ?>:</label>
			<div class="help-text pb-8">
				<?php
					// translators: %1$s: openrouter key document url, %2$s: link text.
					echo wp_kses_post( sprintf( __( 'Get your OpenRouter API key from <a href="%1$s" target="_blank">%2$s</a>', 'feedzy-rss-feeds-pro' ), esc_url( 'https://openrouter.ai/docs/api-keys' ), __( 'OpenRouter API keys', 'feedzy-rss-feeds-pro' ) ) );
				?>
			</div>
			<input
				type="password"
				class="form-control"
				id="openrouter_api_key"
				name="openrouter_api_key"
				value="<?php echo esc_attr( $openrouter_api_key ); ?>"
				placeholder="<?php echo esc_attr( $license_key_placeholder ); ?>"
			/>
		</div>
		<div class="fz-form-group">
			<label class="form-label"><?php esc_html_e( 'The OpenRouter model', 'feedzy-rss-feeds-pro' ); ?>:</label>
			<div class="help-text pb-8">
				<?php
					// translators: %1$s: openrouter pricing url, %2$s: link text.
					echo wp_kses_post( sprintf( __( 'OpenRouter API models <a href="%1$s" target="_blank">%2$s</a>', 'feedzy-rss-feeds-pro' ), esc_url( 'https://openrouter.ai/models' ), __( 'Pricing', 'feedzy-rss-feeds-pro' ) ) );
				?>
			</div>
			<div class="fz-input-group">
				<div class="fz-input-group-left">
					<input type="text" name="openrouter_api_model" id="openrouter_api_model" class="form-control" value="<?php echo esc_attr( $openrouter_api_model ); ?>">
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
								$openrouter_last_check
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
		var openrouter_data = {
			'openrouter_api_key': jQuery( '#openrouter_api_key' ).val(),
			'openrouter_api_model': jQuery( '#openrouter_api_model' ).val(),
		}

		var data = {
			'action': 'update_settings_page',
			'feedzy_settings': openrouter_data,
			'_wpnonce': '<?php echo esc_js( wp_create_nonce( 'update_settings_page' ) ); ?>',
		};

		jQuery( button ).prop( 'disabled', true );
		jQuery( button ).html('<?php esc_html_e( 'Checking ...', 'feedzy-rss-feeds-pro' ); ?>');
		jQuery.post( ajaxurl, data, function( response ) {
			jQuery( button ).prop( 'disabled', false );
			jQuery( button ).html('<?php esc_html_e( 'Validate & Save', 'feedzy-rss-feeds-pro' ); ?>');
			location.reload();
		}, 'json');

		return false;
	};
</script>
