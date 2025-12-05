=== Nova AI WebGPU Frontend ===
Contributors: ailinux
Tags: ai, webgpu, image-processing, vision, overlay, preprocessing
Requires at least: 5.0
Tested up to: 6.4
Stable tag: 0.1.0
License: GPL v2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

WebGPU-accelerated UI for AI-powered image post-processing, vision overlays, and preprocessing.

== Description ==

This WordPress plugin provides a hardware-accelerated frontend for AI image processing using WebGPU technology. It offers:

* Real-time image filtering and effects
* Vision overlay rendering and editing
* Interactive mask drawing tools
* GPU-accelerated preprocessing
* Fallback support for older browsers

== Features ==

* **Hardware Acceleration**: Leverages WebGPU for GPU-accelerated image processing
* **Real-time Effects**: Apply filters and effects with instant preview
* **Vision Overlays**: AI-generated overlay rendering and manipulation
* **Interactive Tools**: Draw and edit masks with precision
* **Browser Compatibility**: Automatic fallback to WebGL/Canvas2D
* **WordPress Integration**: Seamless integration with Nova AI backend

== Installation ==

1. Upload the plugin files to `/wp-content/plugins/wp-webgpu/`
2. Activate the plugin through the WordPress admin
3. Configure the Nova AI backend connection
4. Use the shortcode `[nova_ai_gpu]` in your posts/pages

== Requirements ==

* WordPress 5.0+
* Modern browser with WebGPU support (Chrome 113+, Edge 113+)
* Nova AI backend server
* PHP 7.4+

== Usage ==

Use the shortcode in any post or page:

[nova_ai_gpu]

The interface will automatically detect WebGPU support and provide appropriate fallbacks.

== Technical Details ==

* **WebGPU Support**: Full hardware acceleration on supported browsers
* **Fallback Rendering**: WebGL and Canvas2D fallbacks for compatibility
* **Shader-based Processing**: Custom WGSL shaders for image effects
* **TypeScript**: Fully typed codebase for reliability
* **Modern Build**: Vite-based build system with hot reload

== Browser Support ==

* **Full Support**: Chrome 113+, Edge 113+, Opera 99+
* **Fallback Support**: Safari 16.4+, Firefox (WebGL)
* **Limited Support**: Older browsers (Canvas2D only)

== Changelog ==

= 0.1.0 =
* Initial release
* WebGPU device detection and initialization
* Basic image processing shaders
* Vision overlay interface
* Interactive mask drawing
* WordPress plugin integration
* Automatic fallback rendering

== Frequently Asked Questions ==

= Does this plugin require special hardware? =

While WebGPU acceleration provides the best performance, the plugin includes automatic fallbacks for systems without WebGPU support.

= What browsers are supported? =

Modern browsers with WebGPU support get full acceleration. Older browsers automatically use WebGL or Canvas2D fallbacks.

= Do I need the Nova AI backend? =

Yes, this frontend component requires the Nova AI backend server for AI-powered features like vision overlays.

== Support ==

For support and bug reports, please visit the GitHub repository or contact the development team.

== License ==

This plugin is licensed under the GPL v2 or later.

Copyright (C) 2024 AILinux