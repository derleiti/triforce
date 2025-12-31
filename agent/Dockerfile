################################################################################
# Codex MCP Agent Sidecar
# Minimal image for TriForce MCP integration
################################################################################
FROM node:20-slim

LABEL maintainer="Markus Leitermann <markus@ailinux.me>"
LABEL description="Codex MCP Agent Sidecar für TriForce"

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Codex CLI globally
RUN npm install -g @openai/codex && \
    npm cache clean --force

# Create TriForce directory structure
ENV TRIFORCE_ROOT=/opt/triforce
RUN mkdir -p ${TRIFORCE_ROOT}/config/mcp \
             ${TRIFORCE_ROOT}/runtime/codex \
             ${TRIFORCE_ROOT}/secrets

# Copy wrapper scripts
COPY bin/codex-triforce /usr/local/bin/codex-triforce
COPY bin/keep-alive.sh /usr/local/bin/keep-alive.sh
RUN chmod +x /usr/local/bin/codex-triforce /usr/local/bin/keep-alive.sh

# Copy MCP configuration
COPY config/mcp/triforce-mcp.json ${TRIFORCE_ROOT}/config/mcp/triforce-mcp.json

# Environment
ENV CODEX_BINARY=/usr/local/bin/codex
ENV MCP_ENDPOINT=http://host.docker.internal:9100/v1/mcp
ENV CHECK_INTERVAL=60
ENV TZ=Europe/Berlin

WORKDIR ${TRIFORCE_ROOT}

# Keep-alive with periodic health checks
CMD ["/usr/local/bin/keep-alive.sh"]
