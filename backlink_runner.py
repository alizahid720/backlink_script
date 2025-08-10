from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError


@dataclass
class BacklinkResult:
    target_url: str
    keywords: str
    tool_url: str
    backlink_url: str


class BacklinkRunner:
    def __init__(self, headless: bool = True, per_tool_timeout_sec: int = 45) -> None:
        self.per_tool_timeout_ms = per_tool_timeout_sec * 1000
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.tools: List[str] = self._load_tools()

    def shutdown(self) -> None:
        try:
            self.context.close()
        finally:
            try:
                self.browser.close()
            finally:
                self.playwright.stop()

    def _load_tools(self) -> List[str]:
        raw_tools = [
            "https://searchenginereports.net/backlink-maker",
            "http://www.indexkings.com/",
            "https://www.backlinkr.net/",
            "http://www.imtalk.org/cmps_index.php?pageid=IMT-Website-Submitter",
            "http://sitowebinfo.com/back/",
            "https://useme.org/",
            "http://247backlinks.info/",
            "http://real-backlinks.com/en",
            "http://www.freebacklinkbuilder.net/",
            "https://smallseotools.com/backlink-maker/",
            "https://w3seo.info/backlink-maker",
            "https://sitechecker.pro/backlinks-generator/",
            "https://seo1seotools.com/",
            "https://free-backlinks.org/",
            "http://ping-my-url.net/",
            "https://freebacklinks.info/",
            "http://ping-my-url.com/beta.html",
            "http://free-backlinks.info/",
            "https://free-backlinks.net/free-backlink-generator.html",
            "http://sitowebinfo.com/back/",
            "http://buy-backlinks.info/free-backlinks/",
            "https://seo1seotools.com/free-backlink-generator.html",
            "http://freebacklinkgenerator.net/free-backlink-generator.html",
            "https://buy-backlinks.net/free-backlink-generator.html",
            "https://addurl.official.my/",
            "http://100downloads.xyz/edugov/",
            "https://smartseotools.org/backlink-maker",
            "https://sitowebinfo.com/back/",
            "http://connectionbuilder.co.uk/",
            "https://www.duplichecker.com/backlink-maker.php",
            "https://seowagon.com/backlink-maker",
            "http://bulklink.org/",
            "https://www.coderduck.com/backlink-maker",
            "https://www.xwebtools.com/backlink-generator/",
            "https://www.w3era.com/tool/backlink-maker/",
        ]
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for u in raw_tools:
            if u not in seen:
                deduped.append(u)
                seen.add(u)
        return deduped

    def run_for_target(self, url: str, keywords: str) -> List[BacklinkResult]:
        results: List[BacklinkResult] = []
        for tool in self.tools:
            try:
                tool_results = self._run_single_tool(tool_url=tool, target_url=url, keywords=keywords)
                results.extend(tool_results)
            except Exception:
                # Ignore failures per tool to keep the batch running
                continue
        return results

    # --------------- Internal helpers ---------------

    def _run_single_tool(self, tool_url: str, target_url: str, keywords: str) -> List[BacklinkResult]:
        page = self.context.new_page()
        page.set_default_timeout(self.per_tool_timeout_ms)
        try:
            page.goto(tool_url, wait_until="domcontentloaded")
            # Attempt to find URL and Keywords fields
            url_input = self._find_best_field(page, ["url", "website", "site", "link"])
            if url_input is not None:
                url_input.fill("")
                url_input.type(target_url, delay=10)
            # Keywords may be optional
            kw_input = self._find_best_field(page, ["keyword", "keywords", "tags", "anchor"])  # heuristics
            if kw_input is not None and keywords:
                kw_input.fill("")
                kw_input.type(keywords, delay=10)

            # Try to submit the form
            submitted = self._click_submit(page)
            if not submitted:
                # Try pressing Enter if URL input exists
                if url_input is not None:
                    url_input.press("Enter")
            # Wait for network to settle or content to change
            self._wait_for_results(page)

            # Collect outbound links as potential backlinks
            backlinks = self._extract_links(page)
            results = [
                BacklinkResult(
                    target_url=target_url,
                    keywords=keywords,
                    tool_url=tool_url,
                    backlink_url=link,
                )
                for link in backlinks
            ]
            return results
        finally:
            try:
                page.close()
            except Exception:
                pass

    def _find_best_field(self, page: Page, keyword_variants: List[str]):
        # Try accessible roles first
        for kw in keyword_variants:
            try:
                el = page.get_by_label(re.compile(kw, re.I)).first
                if el and el.count() > 0:
                    return el
            except Exception:
                pass
        # XPath search for input/textarea with matching attributes
        kw_union = " or ".join([
            f"contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')"
            + f" or contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')"
            + f" or contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')"
            + f" or contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')"
            for kw in keyword_variants
        ])
        xpath = (
            "xpath=(//input[(" + kw_union + ")] | //textarea[(" + kw_union + ")])[1]"
        )
        try:
            locator = page.locator(xpath)
            if locator and locator.count() > 0:
                return locator
        except Exception:
            pass
        return None

    def _click_submit(self, page: Page) -> bool:
        button_texts = [
            "submit", "generate", "create", "make", "build", "start", "go", "check", "search", "run",
        ]
        # Try input[type=submit]
        try:
            candidate = page.locator("input[type=submit], button[type=submit]").first
            if candidate and candidate.count() > 0:
                candidate.click()
                return True
        except Exception:
            pass
        # Try buttons by text
        for txt in button_texts:
            try:
                btn = page.get_by_role("button", name=re.compile(txt, re.I)).first
                if btn and btn.count() > 0:
                    btn.click()
                    return True
            except Exception:
                pass
            try:
                btn2 = page.locator(f"button:has-text('{txt}')").first
                if btn2 and btn2.count() > 0:
                    btn2.click()
                    return True
            except Exception:
                pass
            try:
                input_btn = page.locator(f"input[type=button][value*='{txt}'], input[value*='{txt}']").first
                if input_btn and input_btn.count() > 0:
                    input_btn.click()
                    return True
            except Exception:
                pass
        # Try pressing Enter on any focused input
        try:
            page.keyboard.press("Enter")
            return True
        except Exception:
            return False

    def _wait_for_results(self, page: Page) -> None:
        try:
            page.wait_for_load_state("networkidle", timeout=self.per_tool_timeout_ms)
        except PlaywrightTimeoutError:
            pass
        # small grace period to let content update
        time.sleep(1.0)

    def _extract_links(self, page: Page) -> List[str]:
        current_host = urlparse(page.url).netloc
        try:
            html = page.content()
        except Exception:
            return []
        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.find_all("a", href=True)
        found: List[str] = []
        for a in anchors:
            href: str = a.get("href", "").strip()
            if not href:
                continue
            if href.startswith("javascript:") or href.startswith("#"):
                continue
            if href.startswith("mailto:"):
                continue
            parsed = urlparse(href)
            if not parsed.scheme:
                # Make absolute relative to page
                try:
                    abs_url = page.url.rstrip("/") + ("/" if not href.startswith("/") else "") + href
                except Exception:
                    abs_url = href
            else:
                abs_url = href
            host = urlparse(abs_url).netloc
            if not host:
                continue
            if host == current_host:
                # Skip links to the tool site itself
                continue
            found.append(abs_url)
        # Deduplicate, preserve order
        seen = set()
        unique_links = []
        for u in found:
            if u not in seen:
                unique_links.append(u)
                seen.add(u)
        return unique_links 