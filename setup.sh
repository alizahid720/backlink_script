#!/bin/bash
# Install Playwright browsers for Streamlit Cloud deployment

# Set environment variables for headless operation
export DISPLAY=:99
export PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

# Install Playwright browsers
python -m playwright install chromium
python -m playwright install-deps chromium

# Verify installation
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.stop(); print('Playwright installation successful')"
