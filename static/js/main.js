/**
 * PC Shop — Frontend Interactivity & Theme Engine
 * Lightweight Vanilla JS (Theme Toggle, Alerts, Confirmations, Clipboard)
 */
(function () {
    'use strict';

    const THEME_STORAGE_KEY = 'pcshop_theme';

    function getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    }

    function applyTheme(theme, persist = true) {
        const normalized = theme === 'dark' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', normalized);
        if (persist) {
            try {
                localStorage.setItem(THEME_STORAGE_KEY, normalized);
            } catch (e) {
                // Ignore storage quota errors
            }
        }
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.setAttribute(
                'aria-label',
                normalized === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'
            );
            toggleBtn.setAttribute(
                'title',
                normalized === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'
            );
        }
        window.dispatchEvent(new CustomEvent('pcshop:themechange', { detail: { theme: normalized } }));
    }

    document.addEventListener('DOMContentLoaded', function () {
        // 1. Theme Toggle Button
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            applyTheme(getCurrentTheme(), false);
            toggleBtn.addEventListener('click', function () {
                const nextTheme = getCurrentTheme() === 'dark' ? 'light' : 'dark';
                applyTheme(nextTheme, true);
            });
        }

        // Listen for OS theme changes if user hasn't explicitly chosen a theme
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            if (mediaQuery.addEventListener) {
                mediaQuery.addEventListener('change', function (e) {
                    try {
                        if (!localStorage.getItem(THEME_STORAGE_KEY)) {
                            applyTheme(e.matches ? 'dark' : 'light', false);
                        }
                    } catch (err) {}
                });
            }
        }

        // 2. Dismissible Alert Banners
        document.querySelectorAll('.alert-close').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const alertBox = btn.closest('.alert');
                if (alertBox) {
                    alertBox.remove();
                }
            });
        });

        // 3. Copy Promo Code Pill
        document.querySelectorAll('[data-copy-code]').forEach(function (el) {
            el.addEventListener('click', function () {
                const code = el.getAttribute('data-copy-code');
                if (code && navigator.clipboard) {
                    navigator.clipboard.writeText(code).then(function () {
                        const originalText = el.textContent;
                        el.textContent = 'Copied: ' + code;
                        setTimeout(function () {
                            el.textContent = originalText;
                        }, 1800);
                    });
                }
            });
        });

        // 4. Confirmation Dialogs for Delete / Cancel Forms
        document.querySelectorAll('form[data-confirm]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                const message = form.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
                if (!window.confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    });
})();

