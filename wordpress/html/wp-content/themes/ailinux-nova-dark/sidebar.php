<?php
/**
 * Sidebar template
 *
 * @package Ailinux_Nova_Dark
 */

if ( ! is_active_sidebar( 'sidebar-1' ) ) {
    return;
}
?>
<aside id="secondary" class="sidebar" role="complementary">
    <?php dynamic_sidebar( 'sidebar-1' ); ?>
</aside>
