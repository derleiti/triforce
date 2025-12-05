<?php
$spinnerchief_key = '';
if ( isset( $this->settings['spinnerchief_key'] ) ) {
	$spinnerchief_key = $this->settings['spinnerchief_key'];
}

$_status                 = __( 'Invalid', 'feedzy-rss-feeds-pro' );
$spinnerchief_licence    = '';
$license_status_color    = '#F00';
$spinnerchief_last_check = __( 'Never', 'feedzy-rss-feeds-pro' );
if ( isset( $this->settings['spinnerchief_licence'] ) ) {
	$spinnerchief_licence = $this->settings['spinnerchief_licence'];
	if ( 'yes' === $spinnerchief_licence ) {
		$_status              = __( 'Valid', 'feedzy-rss-feeds-pro' );
		$license_status_color = '#62c370';
	}
}
if ( isset( $this->settings['spinnerchief_last_check'] ) ) {
	$spinnerchief_last_check = $this->settings['spinnerchief_last_check'];
}
if ( isset( $this->settings['spinnerchief_message'] ) && ! empty( $this->settings['spinnerchief_message'] ) ) {
	$_status = $this->settings['spinnerchief_message'];
}

$license_key_placeholder = wp_sprintf(
	// translators: %s the name of 3-rd party service used.
	__( '%s API key', 'feedzy-rss-feeds-pro' ),
	__( 'SpinnerChief', 'feedzy-rss-feeds-pro' )
);

?>
<div class="fz-form-wrap">
	<div class="form-block">
		<div class="fz-form-group">
			<label class="form-label">
				<?php
				echo esc_html(
					wp_sprintf(
						// translators: %s the name of 3-rd party service used.
						__( '%s API key', 'feedzy-rss-feeds-pro' ),
						__( 'SpinnerChief', 'feedzy-rss-feeds-pro' )
					)
				);
				?>
			</label>
			<div class="fz-input-group">
				<div class="fz-input-group-left">
					<input
						type="password"
						id="spinnerchief_key"
						class="form-control"
						name="spinnerchief_key" 
						value="<?php echo esc_attr( $spinnerchief_key ); ?>"
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
								$spinnerchief_last_check
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

		var spinnerchief_data = {
			'spinnerchief_key': jQuery( '#spinnerchief_key' ).val(),
		}

		var data = {
			'action': 'update_settings_page',
			'feedzy_settings': spinnerchief_data,
			'_wpnonce': '<?php echo esc_js( wp_create_nonce( 'update_settings_page' ) ); ?>',
		};

		jQuery( button ).prop( 'disabled', true );
		jQuery( button ).html('<?php echo esc_html__( 'Checking', 'feedzy-rss-feeds-pro' ); ?> ...');
		jQuery.post( ajaxurl, data, function( response ) {
			jQuery( button ).prop( 'disabled', false );
			jQuery( button ).html('<?php echo esc_html__( 'Validate & Save', 'feedzy-rss-feeds-pro' ); ?>');
			location.reload();
		}, 'json');

		return false;
	};
</script>
