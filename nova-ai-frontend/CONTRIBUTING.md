# Contributing to Nova AI Frontend

Thank you for your interest in contributing to the Nova AI Frontend WordPress plugin! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites
- WordPress 5.0+ development environment
- PHP 7.4+ with necessary extensions
- Node.js 18+ and npm (for asset compilation)
- Modern web browser for testing

### Local Development

1. **Clone and setup WordPress:**
   ```bash
   # Set up local WordPress installation
   # Configure with Nova AI backend
   ```

2. **Plugin development:**
   ```bash
   cd nova-ai-frontend
   # Edit PHP, JavaScript, and CSS files
   # Test changes in WordPress admin
   ```

3. **Asset compilation:**
   ```bash
   # JavaScript/CSS assets are pre-compiled
   # For development, edit source files directly
   ```

## Code Standards

### PHP Code Style
- Follow WordPress Coding Standards
- Use PHP 7.4+ features appropriately
- Include proper PHPDoc comments
- Validate with PHP CodeSniffer

### JavaScript Code Style
- Modern ES2022 syntax
- Async/await for asynchronous operations
- Proper error handling
- JSDoc comments for functions

### CSS Structure
- BEM methodology for class naming
- Mobile-first responsive design
- CSS custom properties for theming
- Minimize specificity conflicts

## File Organization

```
nova-ai-frontend/
├── assets/           # Compiled frontend assets
├── includes/         # PHP classes and functions
├── README.md         # This documentation
├── CHANGELOG.md      # Version history
└── *.php             # Main plugin files
```

## Testing

### Manual Testing Checklist
- [ ] WordPress admin interface loads correctly
- [ ] Frontend interface displays properly
- [ ] API communication works
- [ ] Error handling functions
- [ ] Mobile responsiveness
- [ ] Cross-browser compatibility

### Browser Testing
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Update** documentation if needed
6. **Submit** a pull request

### PR Requirements
- Clear description of changes
- Screenshots for UI changes
- Test results included
- Documentation updates
- No breaking changes without discussion

## Issue Reporting

### Bug Reports
Please include:
- WordPress version
- PHP version
- Browser and version
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable

### Feature Requests
Please include:
- Use case description
- Proposed implementation
- Benefits and impact

## Security

- Never commit API keys or sensitive data
- Validate all user inputs
- Use WordPress security functions
- Report security issues privately

## License

By contributing, you agree that your contributions will be licensed under the GPL v2 or later.

## Contact

For questions or discussions:
- GitHub Issues for bugs and features
- Development team for technical discussions