#!/bin/bash
# Install Playwright browsers for Streamlit Cloud deployment
python -m playwright install chromium
python -m playwright install-deps chromium
