/**
 * Global Error Handler for Ailinux Nova Dark Theme
 *
 * Provides robust error handling, logging, and fallbacks
 *
 * @package Ailinux_Nova_Dark
 * @since 1.1.0
 */

(function() {
    'use strict';

    /**
     * Error Handler Singleton
     */
    const ErrorHandler = {
        /**
         * Error queue for batch reporting
         */
        errorQueue: [],

        /**
         * Maximum errors to queue
         */
        maxQueueSize: 50,

        /**
         * Error reporting endpoint
         */
        reportEndpoint: '/wp-json/ailinux/v1/log-error',

        /**
         * Initialize error handler
         */
        init() {
            // Global error listener
            window.addEventListener('error', this.handleError.bind(this));

            // Unhandled promise rejections
            window.addEventListener('unhandledrejection', this.handleRejection.bind(this));

            // Report errors on page unload
            window.addEventListener('beforeunload', this.flushQueue.bind(this));

            console.log('[ErrorHandler] Initialized');
        },

        /**
         * Handle JavaScript errors
         *
         * @param {ErrorEvent} event Error event
         */
        handleError(event) {
            const error = {
                type: 'error',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error ? event.error.stack : null,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                userAgent: navigator.userAgent
            };

            this.logError(error);
            this.queueError(error);

            // Don't suppress default error handling
            return false;
        },

        /**
         * Handle unhandled promise rejections
         *
         * @param {PromiseRejectionEvent} event Rejection event
         */
        handleRejection(event) {
            const error = {
                type: 'unhandledRejection',
                message: event.reason ? event.reason.message || String(event.reason) : 'Unknown error',
                stack: event.reason ? event.reason.stack : null,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                userAgent: navigator.userAgent
            };

            this.logError(error);
            this.queueError(error);

            // Prevent default rejection handling
            event.preventDefault();
        },

        /**
         * Log error to console
         *
         * @param {Object} error Error object
         */
        logError(error) {
            if (typeof console !== 'undefined' && console.error) {
                console.error('[ErrorHandler]', error.message, error);
            }
        },

        /**
         * Add error to queue for batch reporting
         *
         * @param {Object} error Error object
         */
        queueError(error) {
            if (this.errorQueue.length >= this.maxQueueSize) {
                // Drop oldest error
                this.errorQueue.shift();
            }

            this.errorQueue.push(error);

            // Auto-flush after 10 errors
            if (this.errorQueue.length >= 10) {
                this.flushQueue();
            }
        },

        /**
         * Send queued errors to server
         */
        flushQueue() {
            if (this.errorQueue.length === 0) {
                return;
            }

            const errors = [...this.errorQueue];
            this.errorQueue = [];

            // Use sendBeacon for reliability (works even during page unload)
            if (navigator.sendBeacon) {
                const blob = new Blob([JSON.stringify({ errors })], { type: 'application/json' });
                navigator.sendBeacon(this.reportEndpoint, blob);
            } else {
                // Fallback: async fetch (may not complete if page is unloading)
                fetch(this.reportEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ errors }),
                    keepalive: true
                }).catch(err => console.error('[ErrorHandler] Failed to report errors:', err));
            }
        },

        /**
         * Wrap a function with error handling
         *
         * @param {Function} fn Function to wrap
         * @param {*} context Context (this)
         * @return {Function} Wrapped function
         */
        wrap(fn, context = null) {
            return function(...args) {
                try {
                    return fn.apply(context, args);
                } catch (error) {
                    ErrorHandler.handleError({
                        message: error.message,
                        filename: 'wrapped-function',
                        lineno: 0,
                        colno: 0,
                        error: error
                    });
                    return null;
                }
            };
        },

        /**
         * Wrap an async function with error handling
         *
         * @param {Function} fn Async function to wrap
         * @param {*} context Context (this)
         * @return {Function} Wrapped async function
         */
        wrapAsync(fn, context = null) {
            return async function(...args) {
                try {
                    return await fn.apply(context, args);
                } catch (error) {
                    ErrorHandler.handleRejection({
                        reason: error,
                        preventDefault: () => {}
                    });
                    return null;
                }
            };
        },

        /**
         * Safe execution with fallback
         *
         * @param {Function} fn Function to execute
         * @param {Function} fallback Fallback function if error occurs
         * @param {*} context Context (this)
         * @return {*} Result or fallback result
         */
        safe(fn, fallback = () => null, context = null) {
            try {
                return fn.call(context);
            } catch (error) {
                this.handleError({
                    message: error.message,
                    filename: 'safe-execution',
                    lineno: 0,
                    colno: 0,
                    error: error
                });
                return fallback.call(context);
            }
        },

        /**
         * Safe async execution with fallback
         *
         * @param {Function} fn Async function to execute
         * @param {Function} fallback Async fallback function
         * @param {*} context Context (this)
         * @return {Promise} Result or fallback result
         */
        async safeAsync(fn, fallback = async () => null, context = null) {
            try {
                return await fn.call(context);
            } catch (error) {
                this.handleRejection({
                    reason: error,
                    preventDefault: () => {}
                });
                return await fallback.call(context);
            }
        }
    };

    // Auto-initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => ErrorHandler.init());
    } else {
        ErrorHandler.init();
    }

    // Expose globally
    window.AilinuxErrorHandler = ErrorHandler;
})();
