(function ($) {
  'use strict';

  const NovaAIAdmin = {
    apiBase: novaAIAdmin.apiBase || 'https://api.ailinux.me:9000',
    ajaxUrl: novaAIAdmin.ajaxUrl,
    nonce: novaAIAdmin.nonce,

    init() {
      // Check which page we're on
      if ($('#nova-crawler-jobs-container').length) {
        this.loadCrawlerJobs();
        setInterval(() => this.loadCrawlerJobs(), 10000);
      } else if ($('.nova-ai-dashboard').length) {
        this.loadDashboardStats();
        setInterval(() => this.loadDashboardStats(), 30000);
      }
      this.bindEvents();
    },

    bindEvents() {
      $('#nova-trigger-publish').on('click', () => this.triggerPublish());
    },

    async loadDashboardStats() {
      try {
        // Backend Health Check
        const health = await this.fetchAPI('/health').catch(() => ({ ok: false }));
        if (health.ok) {
          $('#nova-publisher-status').html('✅ Aktiv');
        } else {
          $('#nova-publisher-status').html('❌ Offline');
          // If backend is offline, show error for all stats
          $('#nova-crawler-status').html('❌ Offline');
          $('#nova-pending-results').html('❌ Offline');
          $('#nova-posts-today').html('❌ Offline');
          return;
        }

        // Auto-Crawler Status (24/7)
        const autoCrawlerStatus = await this.fetchAPI('/v1/auto-crawler/status').catch(() => null);
        if (autoCrawlerStatus && autoCrawlerStatus.status === 'running') {
          const categories = Object.keys(autoCrawlerStatus.categories || {});
          $('#nova-crawler-status').html(`🤖 24/7 (${categories.length} Kategorien)`);
        } else {
          // Fallback: Crawler Jobs
          const jobs = await this.fetchAPI('/v1/crawler/jobs').catch(() => []);
          const activeJobs = jobs.filter(j => j.status === 'running').length;
          $('#nova-crawler-status').html(`${activeJobs} aktive`);
        }

        // Search for unposted results
        const searchResults = await this.fetchAPI('/v1/crawler/search', {
          method: 'POST',
          body: JSON.stringify({
            query: '',
            limit: 50,
            min_score: 0.6,
          }),
        }).catch(() => []);

        const unposted = searchResults.filter(r => !r.posted_at).length;
        $('#nova-pending-results').html(unposted);

        // Recent Auto-Posts (via WordPress AJAX)
        $.post(
          this.ajaxUrl,
          {
            action: 'nova_ai_get_stats',
            nonce: this.nonce,
          },
          (response) => {
            if (response.success) {
              $('#nova-posts-today').html(response.data.posts_today);
              this.renderRecentPosts(response.data.recent_posts);
            } else {
              $('#nova-posts-today').html('❌');
              $('#nova-recent-posts-tbody').html('<tr><td colspan="5" style="text-align:center;">Fehler beim Laden</td></tr>');
            }
          }
        ).fail(() => {
          $('#nova-posts-today').html('❌');
          $('#nova-recent-posts-tbody').html('<tr><td colspan="5" style="text-align:center;">WordPress AJAX Fehler</td></tr>');
        });

      } catch (error) {
        console.error('Dashboard stats error:', error);
        $('#nova-publisher-status').html('❌ Fehler');
        $('#nova-crawler-status').html('❌');
        $('#nova-pending-results').html('❌');
        $('#nova-posts-today').html('❌');
      }
    },

    renderRecentPosts(posts) {
      if (!posts || posts.length === 0) {
        $('#nova-recent-posts-tbody').html('<tr><td colspan="5" style="text-align:center;">Keine Posts</td></tr>');
        return;
      }

      const rows = posts.map(post => `
        <tr>
          <td><strong>${this.escapeHtml(post.title)}</strong></td>
          <td>-</td>
          <td>Auto-Crawler</td>
          <td>${new Date(post.date).toLocaleString('de-DE')}</td>
          <td>
            <a href="${post.url}" target="_blank" class="button button-small">
              Ansehen
            </a>
          </td>
        </tr>
      `).join('');

      $('#nova-recent-posts-tbody').html(rows);
    },

    async triggerPublish() {
      const $button = $('#nova-trigger-publish');
      const $result = $('#nova-trigger-result');

      $button.prop('disabled', true).text('Wird ausgeführt...');

      try {
        // Trigger via WordPress AJAX
        const response = await $.post(this.ajaxUrl, {
          action: 'nova_ai_trigger_publish',
          nonce: this.nonce,
        });

        if (response.success) {
          $result.html(`<div class="notice notice-success"><p>${response.data.message}</p></div>`);
          // Reload stats nach 2 Sekunden
          setTimeout(() => this.loadDashboardStats(), 2000);
        } else {
          $result.html(`<div class="notice notice-error"><p>Fehler: ${response.data}</p></div>`);
        }
      } catch (error) {
        $result.html(`<div class="notice notice-error"><p>Fehler: ${error.message}</p></div>`);
      } finally {
        $button.prop('disabled', false).text('Jetzt veröffentlichen');
      }
    },

    async fetchAPI(endpoint, options = {}) {
      const url = this.apiBase + endpoint;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000); // 30s timeout

      const defaults = {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-AILinux-Client': 'nova-ai-frontend/1.0',
        },
        signal: controller.signal,
      };

      try {
        const response = await fetch(url, { ...defaults, ...options });
        clearTimeout(timeout);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
      } catch (error) {
        clearTimeout(timeout);
        if (error.name === 'AbortError') {
          throw new Error('Request timeout after 30 seconds');
        }
        throw error;
      }
    },

    async loadCrawlerJobs() {
      const $container = $('#nova-crawler-jobs-container');

      try {
        const jobs = await this.fetchAPI('/v1/crawler/jobs').catch(() => []);

        if (!jobs || jobs.length === 0) {
          $container.html('<p>Keine Crawl-Jobs gefunden.</p>');
          return;
        }

        const table = `
          <table class="wp-list-table widefat fixed striped">
            <thead>
              <tr>
                <th>ID</th>
                <th>URL</th>
                <th>Status</th>
                <th>Seiten</th>
                <th>Ergebnisse</th>
                <th>Erstellt</th>
              </tr>
            </thead>
            <tbody>
              ${jobs.map(job => `
                <tr>
                  <td>${this.escapeHtml(job.id || '-')}</td>
                  <td>${this.escapeHtml((job.url || '-').substring(0, 50))}${job.url && job.url.length > 50 ? '...' : ''}</td>
                  <td><span class="status-badge ${job.status || 'unknown'}">${this.escapeHtml(job.status || 'unknown')}</span></td>
                  <td>${job.pages_crawled || 0}</td>
                  <td>${job.results ? job.results.length : 0}</td>
                  <td>${job.created_at ? new Date(job.created_at).toLocaleString('de-DE') : '-'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;

        $container.html(table);
      } catch (error) {
        console.error('Crawler jobs error:', error);
        $container.html(`<div class="notice notice-error"><p>Fehler beim Laden: ${this.escapeHtml(error.message)}</p></div>`);
      }
    },

    escapeHtml(text) {
      const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
      };
      return String(text).replace(/[&<>"']/g, m => map[m]);
    },
  };

  // Init on DOM ready
  $(document).ready(() => NovaAIAdmin.init());

})(jQuery);
