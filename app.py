import sys
import asyncio

# Ensure Windows uses ProactorEventLoop which supports subprocesses (required by Playwright)
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import streamlit as st
import pandas as pd
from typing import List, Dict
from backlink_runner import BacklinkRunner, BacklinkResult

st.set_page_config(page_title="Backlink Runner", page_icon="🔗", layout="wide")

st.title("🔗 Backlink Generator Runner (Python)")
st.caption("Enter one or more target URLs and comma-separated keywords. Click Run to submit to multiple backlink tools and collect any reported links.")

# Initialize session state for dynamic rows
if "targets" not in st.session_state:
    st.session_state.targets = [{"url": "", "keywords": ""}]

# Controls to add/remove rows
with st.container():
    st.subheader("Targets")
    rows_to_remove: List[int] = []
    for idx, row in enumerate(st.session_state.targets):
        cols = st.columns([4, 4, 1])
        st.session_state.targets[idx]["url"] = cols[0].text_input(
            label=f"URL #{idx+1}",
            placeholder="https://example.com",
            value=row.get("url", ""),
            key=f"url_{idx}",
        )
        st.session_state.targets[idx]["keywords"] = cols[1].text_input(
            label=f"Keywords #{idx+1} (comma-separated)",
            placeholder="keyword1, keyword2",
            value=row.get("keywords", ""),
            key=f"keywords_{idx}",
        )
        if cols[2].button("✖", key=f"remove_{idx}"):
            rows_to_remove.append(idx)

    # Remove selected rows
    if rows_to_remove:
        st.session_state.targets = [r for i, r in enumerate(st.session_state.targets) if i not in rows_to_remove]

    add_col1, add_col2 = st.columns([1, 8])
    if add_col1.button("➕ Add URL + Keywords"):
        st.session_state.targets.append({"url": "", "keywords": ""})

# Run button
run_clicked = st.button("🚀 Run Backlink Tools", type="primary")

results_placeholder = st.empty()
progress_placeholder = st.empty()


def normalize_targets(raw_targets: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    for t in raw_targets:
        url = (t.get("url") or "").strip()
        keywords = (t.get("keywords") or "").strip()
        if not url:
            continue
        cleaned.append({"url": url, "keywords": keywords})
    return cleaned


if run_clicked:
    targets = normalize_targets(st.session_state.targets)
    if not targets:
        st.warning("Please enter at least one URL.")
        st.stop()

    progress = st.progress(0.0, text="Starting...")
    results: List[BacklinkResult] = []

    try:
        # Initialize runner with longer timeout for cloud deployment
        runner = BacklinkRunner(headless=True, per_tool_timeout_sec=60)
    except Exception as exc:
        st.error(
            "Failed to initialize browser automation. This might be due to system dependencies or Playwright installation issues.\n\n"
            f"Error details: {str(exc)}\n\n"
            "Please try refreshing the page or contact support if the issue persists."
        )
        st.stop()

    total_tasks = len(targets) * len(runner.tools)
    completed_tasks = 0

    try:
        for target_idx, target in enumerate(targets, start=1):
            url = target["url"]
            keywords = target["keywords"]
            st.write(f"Processing: {url} | Keywords: {keywords}")
            target_results = runner.run_for_target(url=url, keywords=keywords)
            results.extend(target_results)

            completed_tasks += len(runner.tools)
            progress.progress(min(1.0, completed_tasks / max(1, total_tasks)), text=f"Completed {completed_tasks}/{total_tasks} tool submissions")

    except Exception as exc:
        st.error(f"An error occurred during processing: {str(exc)}")
    finally:
        try:
            runner.shutdown()
        except:
            pass

    # Aggregate and show
    if results:
        df = pd.DataFrame([r.__dict__ for r in results])
        total_count = len(df)
        st.success(f"Collected {total_count} backlink URLs")

        # Deduplicate by backlink_url
        df_unique = df.drop_duplicates(subset=["backlink_url"]).reset_index(drop=True)

        # Display summary counts
        st.subheader("Counts")
        c1, c2 = st.columns(2)
        c1.metric("Total links (raw)", f"{total_count}")
        c2.metric("Unique links", f"{len(df_unique)}")

        # Show table
        st.subheader("Backlinks")
        st.dataframe(df_unique, use_container_width=True)

        # Download
        csv = df_unique.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="backlinks.csv", mime="text/csv")
    else:
        st.info("No backlinks were detected from the tools. Some tools may require manual CAPTCHA or do not expose generated links.") 