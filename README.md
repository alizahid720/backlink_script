# Backlink Runner (Python + Streamlit)

A minimal frontend to submit one or more target URLs and comma-separated keywords to a set of backlink tools using a headless browser (Playwright). Displays a deduplicated list of discovered links and counts.

## Prerequisites
- Python 3.9+ installed and available as `python` or `py`
- Internet connection (tools are external websites)

## Setup (Windows)
1. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Install Playwright browser (Chromium):
   ```powershell
   python -m playwright install chromium
   ```

## Run
```powershell
streamlit run app.py
```
Then open the local URL shown in the terminal.

## Notes
- Many backlink tools are inconsistent, use CAPTCHA, or do not display generated links. The app uses heuristics to locate fields and buttons; some tools may fail silently.
- Keywords are optional. If a tool doesn't have a keywords field, only the URL will be submitted.
- Results are best-effort and for demonstration/testing purposes. 