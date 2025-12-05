# Dependency Management

## Current Stack (2025 Cutting-Edge)

This project uses the latest stable versions of all dependencies as of Q1 2025.

### Core Framework

- **FastAPI 0.118.0** - Latest stable release with enhanced WebSocket support
- **Uvicorn 0.32.1** - ASGI server with HTTP/2 and performance improvements
- **Pydantic 2.10.3** - Data validation with 10x performance boost over v1
- **Pydantic-Settings 2.7.0** - Environment variable management

### AI Provider SDKs

- **OpenAI 1.57.4** - GPT-4o, o1, DALL-E 3 support
- **Anthropic 0.39.0** - Claude 3.5 Sonnet & Opus support
- **Google Generative AI 0.8.3** - Gemini 2.0 Flash & Pro
- **Mistral AI 1.2.6** - Mixtral 8x22B support

### HTTP & Async

- **HTTPX 0.28.1** - Modern async HTTP client with HTTP/2
- **aiohttp 3.11.11** - Alternative async HTTP framework

### Testing & Quality

- **pytest 8.3.4** - Latest test framework
- **pytest-asyncio 0.24.0** - Async test support
- **pytest-cov 6.0.0** - Code coverage
- **pytest-mock 3.14.0** - Enhanced mocking
- **ruff 0.8.4** - Fastest Python linter (replaces flake8, isort, etc.)
- **black 24.10.0** - Code formatter
- **mypy 1.13.0** - Static type checker

## Upgrade Strategy

### Regular Updates (Monthly)

```bash
# Check for updates
pip list --outdated

# Upgrade specific package
pip install --upgrade <package>

# Update requirements.txt
pip freeze | grep <package> >> requirements.txt
```

### Major Version Upgrades (Quarterly)

1. Check breaking changes in changelog
2. Update requirements.txt
3. Run full test suite
4. Update code for compatibility

### Security Updates (Immediate)

```bash
# Check for vulnerabilities
pip-audit

# Upgrade security patches
pip install --upgrade <vulnerable-package>
```

## Version Pinning Philosophy

We use **exact version pinning** (`==`) for:
- Reproducible builds across environments
- Predictable behavior in production
- Easier debugging and rollback

Upgrade dependencies intentionally, not accidentally.

## Installation

### Fresh Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Upgrade Existing

```bash
pip install --upgrade -r requirements.txt
```

### Development Dependencies

```bash
# Install with dev tools
pip install -r requirements.txt

# Run code quality checks
ruff check .
black --check .
mypy app/
```

## Compatibility Matrix

| Python | FastAPI | Pydantic | Status |
|--------|---------|----------|--------|
| 3.11   | 0.118   | 2.10     | ✅ Tested |
| 3.12   | 0.118   | 2.10     | ✅ Tested |
| 3.13   | 0.118   | 2.10     | ⚠️ Beta |

## Known Issues

### Pydantic v1 vs v2

If you encounter Pydantic v1 compatibility issues:

```bash
# Ensure all packages support Pydantic v2
pip install --upgrade pydantic-core pydantic-settings
```

### FastAPI-Limiter

Currently pinned to 0.1.6 (last stable). Watch for 0.2.x release.

## Future Roadmap

- [ ] Migrate to Pydantic 3.x when stable (2025 Q3)
- [ ] FastAPI 1.0 stable release (2025 Q2)
- [ ] Python 3.13 full support (2025 Q4)
- [ ] HTTP/3 support via Hypercorn (2025 Q2)

## Contributing

When adding new dependencies:

1. Check license compatibility (MIT, Apache 2.0 preferred)
2. Verify active maintenance (commits in last 3 months)
3. Pin exact version in requirements.txt
4. Document in this file
5. Run full test suite

## Support

For dependency issues, check:
- [FastAPI Discussions](https://github.com/tiangolo/fastapi/discussions)
- [Pydantic GitHub](https://github.com/pydantic/pydantic)
- [Python Discord](https://discord.gg/python)
