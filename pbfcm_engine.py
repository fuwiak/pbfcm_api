# pbfcm_engine.py
# Fast Playwright scraper for https://www.pbfcm.com/taxsale.html
# - Single page, no pagination
# - Extracts:
#     tax-list-entity-title
#     tax-list-file (text)
#     tax-list-file href (URL)
# - Also returns a normalized mapping:
#     entity_title, file_label, file_url, file_type
# - Shares the same performance ideas as your first scraper:
#     headless Chromium, resource blocking, single-pass DOM evaluate

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urldefrag, urlparse
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

PBF_URL = "https://www.pbfcm.com/taxsale.html"

class PBFcmsScraper:
    def __init__(
        self,
        headless: bool = True,
        default_timeout_ms: int = 30_000,
        timezone_id: str = "America/Chicago",
        locale: str = "en-US",
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124 Safari/537.36"
        ),
        block_resources: bool = True,
    ):
        self.headless = headless
        self.default_timeout_ms = default_timeout_ms
        self.timezone_id = timezone_id
        self.locale = locale
        self.user_agent = user_agent
        self.block_resources = block_resources
        self._pw = None
        self._browser: Optional[Browser] = None

    async def start(self):
        if self._browser:
            return
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)

    async def stop(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None

    async def _new_context(self) -> BrowserContext:
        assert self._browser is not None, "Call start() first."
        ctx = await self._browser.new_context(
            user_agent=self.user_agent,
            viewport={"width": 1400, "height": 900},
            java_script_enabled=True,
            timezone_id=self.timezone_id,
            locale=self.locale,
        )
        ctx.set_default_timeout(self.default_timeout_ms)
        ctx.set_default_navigation_timeout(self.default_timeout_ms)

        if self.block_resources:
            async def _route(route, request):
                rt = request.resource_type
                if rt in ("image", "media", "font", "stylesheet"):
                    await route.abort()
                else:
                    await route.continue_()
            await ctx.route("**/*", _route)

        return ctx

    # ---------- extraction ----------

    async def _extract_js(self, page: Page) -> List[Dict[str, Optional[str]]]:
        """
        Return a list of dicts:
          {
            "tax-list-entity-title": str|None,
            "tax-list-file": str|None,
            "tax-list-file href": str|None
          }
        """
        js = """
(() => {
  const out = [];

  // Primary path: explicit class names
  const entities = Array.from(document.querySelectorAll(".tax-list-entity-title"));
  const hasExplicit = entities.length > 0;

  const record = (title, elFile) => {
    if (!elFile) return;
    let a = elFile.matches('a') ? elFile : elFile.querySelector('a');
    const label = (a ? a.innerText : elFile.innerText) ? (a ? a.innerText.trim() : elFile.innerText.trim()) : null;
    const href  = a ? a.getAttribute('href') : null;
    out.push({
      "tax-list-entity-title": title ? title.trim() : null,
      "tax-list-file": label,
      "tax-list-file href": href
    });
  };

  if (hasExplicit) {
    for (const titleEl of entities) {
      const title = titleEl.innerText || titleEl.textContent || "";
      // common wrappers
      const root = titleEl.closest(".tax-list-entity") || titleEl.parentElement || document;
      const files = root.querySelectorAll(".tax-list-file, .tax-list-file a");
      if (files.length > 0) {
        files.forEach(el => record(title, el));
      } else {
        // Fallback: same container links (PDFs or sale links)
        (root.querySelectorAll("a[href$='.pdf'], a[href*='sale'], a[href^='http'], a[href^='/']") || [])
          .forEach(a => record(title, a));
      }
    }
  } else {
    // Robust fallback if the page lacks those classes:
    // Find section headers (e.g., counties) then list following links.
    const sections = Array.from(document.querySelectorAll("h1,h2,h3,strong,b,li"));
    for (const s of sections) {
      const txt = (s.innerText || "").trim();
      if (!txt) continue;
      // Heuristic: likely "X COUNTY" or "Pct" style entries
      if (!/[A-Za-z]/.test(txt)) continue;
      if (!/county|pct|sale|isd|sheriff/i.test(txt)) continue;

      let container = s.closest("li,section,div,ul,ol") || s.parentElement || document;
      const links = container.querySelectorAll("a[href]");
      let hit = false;
      links.forEach(a => {
        const label = (a.innerText || a.textContent || "").trim();
        const href  = a.getAttribute('href');
        if (!href) return;
        // basic filter: avoid page anchors only
        if (href.startsWith("#")) return;
        out.push({
          "tax-list-entity-title": txt,
          "tax-list-file": label || null,
          "tax-list-file href": href
        });
        hit = true;
      });
      if (hit) {
        // do not over-collect from same container multiple times
        // rely on duplication-removal on Python side
      }
    }
  }

  return out;
})();
        """
        rows = await page.evaluate(js)
        # absolutize URLs and dedupe
        seen = set()
        cleaned: List[Dict[str, Optional[str]]] = []
        for r in rows:
            href = r.get("tax-list-file href")
            if href:
                absu = urljoin(PBF_URL, href)
                absu, _ = urldefrag(absu)
                r["tax-list-file href"] = absu
            key = (r.get("tax-list-entity-title") or "", r.get("tax-list-file") or "", r.get("tax-list-file href") or "")
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(r)
        return cleaned

    # ---------- normalization ----------

    @staticmethod
    def _file_type(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        path = urlparse(url).path.lower()
        if path.endswith(".pdf"):
            return "pdf"
        if path.endswith(".doc") or path.endswith(".docx"):
            return "doc"
        if path.endswith(".xls") or path.endswith(".xlsx"):
            return "xls"
        return None

    def _normalize(self, raw: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        entity = (raw.get("tax-list-entity-title") or "").strip() or None
        label  = (raw.get("tax-list-file") or "").strip() or None
        href   = raw.get("tax-list-file href") or None
        return {
            "entity_title": entity,
            "file_label": label,
            "file_url": href,
            "file_type": self._file_type(href),
        }

    # ---------- public API ----------

    async def scrape(self) -> Dict[str, Any]:
        await self.start()
        ctx = await self._new_context()
        page = await ctx.new_page()
        await page.goto(PBF_URL, wait_until="domcontentloaded")
        try:
            # give the page a brief moment to finish layout
            await page.wait_for_timeout(400)
        except Exception:
            pass

        raw_rows = await self._extract_js(page)
        norm_rows = [self._normalize(r) for r in raw_rows]

        await ctx.close()
        return {
            "source_url": PBF_URL,
            "count": len(raw_rows),
            "raw": raw_rows,           # exact field names requested
            "normalized": norm_rows,   # stable, human-friendly names
        }
