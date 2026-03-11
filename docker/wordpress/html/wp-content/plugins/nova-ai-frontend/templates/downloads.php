<?php
/**
 * Downloads Template v2.5
 * Shortcode: [ailinux_downloads]
 */
defined('ABSPATH') || exit;

$service = \NovAI\Services\DownloadsService::instance();
$path = isset($atts['path']) ? sanitize_text_field($atts['path']) : '';
$data = $service->get_directory_contents($path);
?>
<div class="nov-downloads" data-base-url="<?php echo esc_attr(home_url('/downloads')); ?>">
    <nav class="nov-crumb">
        <?php foreach ($data['breadcrumb'] as $i => $crumb): ?>
            <?php if ($i === count($data['breadcrumb']) - 1): ?>
                <span><?php echo esc_html($crumb['name']); ?></span>
            <?php else: ?>
                <a href="#" data-path="<?php echo esc_attr($crumb['path']); ?>"><?php echo esc_html($crumb['name']); ?></a> / 
            <?php endif; ?>
        <?php endforeach; ?>
    </nav>
    
    <ul class="nov-list">
        <?php if (empty($data['files'])): ?>
            <li class="nov-item">
                <span class="nov-icon">📂</span>
                <span class="nov-name">Empty folder</span>
                <span class="nov-size">-</span>
            </li>
        <?php else: ?>
            <?php foreach ($data['files'] as $file): ?>
                <li class="nov-item <?php echo $file['type'] === 'folder' ? 'is-folder' : ''; ?>" 
                    data-path="<?php echo esc_attr($file['path']); ?>">
                    <span class="nov-icon"><?php echo $file['icon']; ?></span>
                    <span class="nov-name">
                        <?php if ($file['type'] === 'folder'): ?>
                            <?php echo esc_html($file['name']); ?>
                        <?php else: ?>
                            <a href="<?php echo esc_url($file['url']); ?>" download><?php echo esc_html($file['name']); ?></a>
                        <?php endif; ?>
                    </span>
                    <span class="nov-size"><?php echo esc_html($file['size']); ?></span>
                </li>
            <?php endforeach; ?>
        <?php endif; ?>
    </ul>
</div>
