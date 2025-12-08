# Nova AI Frontend - WordPress Plugin

A comprehensive WordPress plugin that provides AI-powered features including chat, image generation, vision analysis, and discussion capabilities.

## Features

### 🤖 AI Chat Interface
- Real-time chat with multiple AI models (GPT-OSS, Gemini, Mistral, Ollama)
- Streaming responses for better user experience
- Model selection and switching
- Chat history management

### 🎨 Image Generation
- Text-to-image generation using ComfyUI backend
- Support for SD 1.5 and SDXL models
- Automatic memory management and fallback
- Image download and sharing capabilities

### 👁️ Vision Analysis
- Image upload and URL analysis
- AI-powered image understanding
- Vision model integration
- Real-time processing

### 💬 Discussion System
- Community discussion features
- AI-moderated conversations
- Thread management
- User engagement tools

### ⚙️ Admin Dashboard
- Comprehensive plugin settings
- API key management
- Model configuration
- Usage analytics and monitoring

## Installation

1. Download the plugin files
2. Upload to your WordPress `wp-content/plugins/` directory
3. Activate the plugin through the WordPress admin dashboard
4. Configure API keys and settings in the admin panel

## Configuration

### Required Settings
- **API Base URL**: Backend API endpoint (default: https://api.ailinux.me:9100)
- **API Keys**: Configure keys for supported AI providers:
  - GPT-OSS API Key
  - Google Gemini API Key
  - Mistral API Key

### Optional Settings
- **CORS Origins**: Allowed frontend domains
- **Rate Limiting**: Request throttling settings
- **Model Preferences**: Default model selection
- **UI Customization**: Theme and styling options

## File Structure

```
nova-ai-frontend/
├── assets/
│   ├── icons/           # Plugin icons and favicons
│   ├── admin.css        # Admin dashboard styles
│   ├── admin.js         # Admin dashboard functionality
│   ├── api-client.js    # API communication utilities
│   ├── app.css          # Main application styles
│   ├── app.v2.js        # Main application logic
│   ├── discuss.css      # Discussion system styles
│   ├── discuss.js       # Discussion system logic
│   ├── index.html       # Main HTML template
│   ├── manifest.json    # PWA manifest
│   ├── sw.js           # Service worker
│   ├── widget.css      # Widget styles
│   └── widget.js       # Widget functionality
├── includes/
│   ├── class-nova-ai-admin-dashboard.php    # Admin dashboard class
│   └── class-nova-ai-frontend.php           # Frontend functionality class
├── nova-ai-frontend.php                     # Main plugin file
└── README.md                               # This documentation
```

## API Endpoints

### Chat Endpoints
- `POST /v1/chat` - Send chat messages
- `POST /v1/chat/completions` - OpenAI-compatible completions

### Image Endpoints
- `POST /v1/txt2img` - Generate images from text prompts
- `POST /v1/images/generate` - Legacy image generation (deprecated)
- `POST /v1/images/analyze` - Analyze uploaded images
- `POST /v1/images/analyze/upload` - Analyze images via upload

### Model Management
- `GET /v1/models` - List available models

### Admin Endpoints
- `GET /v1/admin/config-sanity` - Configuration validation
- `POST /v1/admin/reload-config` - Reload configuration

## Shortcodes

### Main Interface
```
[nova_ai_frontend]
```

### GPU-Accelerated Interface
```
[nova_ai_gpu]
```

### Discussion System
```
[nova_ai_discuss]
```

## JavaScript API

### NovaAPIClient Class
```javascript
const client = new NovaAPIClient(baseUrl, clientHeader);

// Chat example
const response = await client.post('/v1/chat', {
  model: 'gpt-oss:latest',
  messages: [{ role: 'user', content: 'Hello!' }]
});

// Image generation example
const response = await client.post('/v1/txt2img', {
  prompt: 'A beautiful sunset',
  workflow_type: 'sd15',
  width: 512,
  height: 512
});
```

## CSS Classes

### Main Components
- `.nova-panel` - Main panel containers
- `.nova-tabs` - Tab navigation
- `.nova-form` - Form elements
- `.nova-result` - Result display areas

### Status Indicators
- `.nova-online` - Online status
- `.nova-offline` - Offline status
- `.nova-loading` - Loading states
- `.nova-error` - Error states

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Dependencies

### Backend Requirements
- FastAPI backend server
- Redis for rate limiting
- AI model providers (Ollama, GPT-OSS, Gemini, etc.)

### Frontend Dependencies
- Modern browser with ES2020 support
- Service Worker API (for PWA features)
- WebGL/WebGPU (for advanced features)

## Troubleshooting

### Common Issues

**Plugin not loading**
- Check PHP version (7.4+ required)
- Verify file permissions
- Check WordPress debug logs

**API connection failed**
- Verify API base URL configuration
- Check API key validity
- Confirm CORS settings

**Image generation failed**
- Check ComfyUI backend availability
- Verify GPU memory availability
- Confirm model configurations

### Debug Mode
Enable WordPress debug mode to see detailed error logs:
```php
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This plugin is licensed under the GPL v2 or later.

## Changelog

### Version 2.0.1
- Added ComfyUI integration for image generation
- Improved error handling and user feedback
- Enhanced admin dashboard
- Added streaming chat responses

### Version 2.0.0
- Complete rewrite with modern JavaScript
- Added vision analysis capabilities
- Improved accessibility
- Enhanced mobile responsiveness

### Version 1.0.0
- Initial release
- Basic chat functionality
- Simple image generation
- Admin configuration panel

## Support

For support and bug reports, please use the GitHub issues page or contact the development team.