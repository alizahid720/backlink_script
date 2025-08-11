#!/bin/bash
# Install Playwright browsers for Streamlit Cloud deployment

# Set environment variables for headless operation
export DISPLAY=:99
export PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

# Install all Playwright browsers (not just chromium)
python -m playwright install
python -m playwright install-deps

# Verify installation
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.stop(); print('Playwright installation successful')"
