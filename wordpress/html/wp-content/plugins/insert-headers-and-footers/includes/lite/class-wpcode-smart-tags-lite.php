<?php
/**
 * Smart tags class for the lite version.
 *
 * @package WPCode
 */

/**
 * WPCode_Smart_Tags_Lite class.
 */
class WPCode_Smart_Tags_Lite extends WPCode_Smart_Tags {

	/**
	 * UTM medium parameter.
	 *
	 * @var string
	 */
	public $utm_medium = 'snippet-manager';

	/**
	 * UTM content parameter.
	 *
	 * @var string
	 */
	public $utm_content = 'upgrade-cta';

	/**
	 * Upgrade notice data.
	 *
	 * @return array
	 */
	public function upgrade_notice_data() {
		return array(
			'title'  => __( 'Smart Tags are a Premium feature', 'insert-headers-and-footers' ),
			'text'   => __( 'Upgrade to PRO today and simplify the way you write advanced snippets using smart tags without having to write any PHP code.', 'insert-headers-and-footers' ),
			'button' => __( 'Upgrade to PRO', 'insert-headers-and-footers' ),
			'link'   => wpcode_utm_url( 'https://wpcode.com/lite/', $this->utm_medium, 'smart-tags', $this->utm_content ),
		);
	}
}
