<?php
$amazon_access_key = '';
if ( isset( $this->settings['amazon_access_key'] ) ) {
	$amazon_access_key = $this->settings['amazon_access_key'];
}

$amazon_secret_key = '';
if ( isset( $this->settings['amazon_secret_key'] ) ) {
	$amazon_secret_key = $this->settings['amazon_secret_key'];
}

$amazon_partner_tag = '';
if ( isset( $this->settings['amazon_partner_tag'] ) ) {
	$amazon_partner_tag = $this->settings['amazon_partner_tag'];
}

$amazon_host = '';
if ( isset( $this->settings['amazon_host'] ) ) {
	$amazon_host = $this->settings['amazon_host'];
}

$amazon_region = '';
if ( isset( $this->settings['amazon_region'] ) ) {
	$amazon_region = $this->settings['amazon_region'];
}

$amazon_locale_hosts   = feedzy_amazon_get_locale_hosts();
$domain_path_extension = array();
foreach ( $amazon_locale_hosts as $code => $hosts ) {
	$domain_path_extension[] = pathinfo( $hosts, PATHINFO_EXTENSION );
}

$error_message  = '';
$_status        = __( 'Invalid', 'feedzy-rss-feeds-pro' );
$aws_licence    = '';
$status_color   = '#F00';
$aws_last_check = __( 'Never', 'feedzy-rss-feeds-pro' );
if ( isset( $this->settings['aws_licence'] ) ) {
	$aws_licence = $this->settings['aws_licence'];
	if ( 'yes' === $aws_licence ) {
		$_status      = __( 'Valid', 'feedzy-rss-feeds-pro' );
		$status_color = '#62c370';
	}
}
if ( isset( $this->settings['aws_last_check'] ) ) {
	$aws_last_check = $this->settings['aws_last_check'];
}
if ( isset( $this->settings['aws_message'] ) && ! empty( $this->settings['aws_message'] ) ) {
	$error_message = $this->settings['aws_message'];
}
?>
<div class="fz-form-wrap">
	<div class="form-block">
		<div class="fz-form-group mb-20">
			<?php
				echo wp_kses_post(
					wp_sprintf(
						// translators: %1$s to available amazon domain, %2$s example URL with ASIN, %3$s list of available Amazon domains.
						__( 'Please use this URL structure %1$s or %2$s while getting Amazon product information. <br> Here are the available Amazon domains: %3$s', 'feedzy-rss-feeds-pro' ),
						'<strong>amazon.[extension]?keyword=Laptop</strong>',
						'<strong>amazon.com?asin=ASIN_1|ASIN_2</strong>',
						'<strong>' . join( ', ', array_map( 'esc_html', $domain_path_extension ) ) . '</strong>'
					)
				);
				?>
		</div>
		<div class="fz-form-row">
			<div class="fz-form-col-6">
				<div class="fz-form-group">
					<label class="form-label"><?php esc_html_e( 'Access Key', 'feedzy-rss-feeds-pro' ); ?>:</label>
					<input type="password" id="amazon_access_key" class="form-control" name="amazon_access_key" value="<?php echo esc_attr( $amazon_access_key ); ?>" placeholder="<?php echo esc_attr( __( 'Access Key', 'feedzy-rss-feeds-pro' ) ); ?>"/>
				</div>
			</div>
			<div class="fz-form-col-6">
				<div class="fz-form-group">
					<label class="form-label"><?php esc_html_e( 'Secret key', 'feedzy-rss-feeds-pro' ); ?>:</label>
					<input type="password" id="amazon_secret_key" class="form-control" name="amazon_secret_key" value="<?php echo esc_attr( $amazon_secret_key ); ?>" placeholder="<?php echo esc_attr( __( 'Secret key', 'feedzy-rss-feeds-pro' ) ); ?>"/>
				</div>
			</div>
		</div>
		<div class="fz-form-row">
			<div class="fz-form-col-6">
				<div class="fz-form-group">
					<label class="form-label"><?php esc_html_e( 'Host', 'feedzy-rss-feeds-pro' ); ?>:</label>
					<select name="amazon_host" id="amazon_host" class="form-control fz-select-control">
						<?php
						$hosts = feedzy_amazon_get_locale_hosts();
						foreach ( $hosts as $host ) {
							echo '<option value="' . esc_attr( $host ) . '" ' . selected( $amazon_host, $host ) . '>' . esc_html( $host ) . '</option>';
						}
						?>
					</select>
				</div>
			</div>
			<div class="fz-form-col-6">
				<div class="fz-form-group">
					<label class="form-label"><?php esc_html_e( 'Region', 'feedzy-rss-feeds-pro' ); ?>:</label>
					<select name="amazon_region" id="amazon_region" class="form-control fz-select-control">
						<?php
						$regions = feedzy_amazon_get_get_locale_regions();
						foreach ( $regions as $key => $region ) {
							echo '<option value="' . esc_attr( $region ) . '" ' . selected( $amazon_region, $region ) . '>' . esc_html( $region ) . '</option>';
						}
						?>
					</select>
				</div>
			</div>
		</div>
		<div class="fz-form-group">
			<label class="form-label"><?php esc_html_e( 'Partner Tag (store/tracking id)', 'feedzy-rss-feeds-pro' ); ?>:</label>
			<div class="fz-input-group">
				<div class="fz-input-group-left">
					<input type="text" id="amazon_partner_tag" class="form-control" name="amazon_partner_tag" value="<?php echo esc_attr( $amazon_partner_tag ); ?>" placeholder="<?php echo esc_attr( __( 'Partner Tag (store/tracking id)', 'feedzy-rss-feeds-pro' ) ); ?>"/>
					<div class="help-text">
						<?php
						echo wp_kses_post(
							wp_sprintf(
								// translators: %1$s is the API status message.
								__( 'API Status: %1$s', 'feedzy-rss-feeds-pro' ),
								wp_sprintf(
									'<span style="color:%1$s;">%2$s</span>',
									$status_color,
									$_status
								)
							)
							. ' | '
							. wp_sprintf(
								// translators: %1$s is the date of the last API status check.
								__( 'Last check: %1$s', 'feedzy-rss-feeds-pro' ),
								$aws_last_check
							)
						);
						if ( ! empty( $error_message ) ) {
							echo wp_kses_post( wp_sprintf( '<p class="fz-setting-message"><strong>%1$s:</strong> %2$s</p>', __( 'Error', 'feedzy-rss-feeds-pro' ), $error_message ) );
						}
						?>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
<script type="text/javascript">
	function ajaxUpdate( button ) {
		var amazon_credentials = {
			'amazon_access_key': jQuery( '#amazon_access_key' ).val(),
			'amazon_secret_key': jQuery( '#amazon_secret_key' ).val(),
			'amazon_partner_tag': jQuery( '#amazon_partner_tag' ).val(),
			'amazon_host': jQuery( '#amazon_host' ).val(),
			'amazon_region': jQuery( '#amazon_region' ).val(),
		}

		var data = {
			'action': 'update_settings_page',
			'feedzy_settings': amazon_credentials,
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
	}
</script>
