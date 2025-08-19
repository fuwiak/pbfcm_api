# pbfcm_cli.py
# Colorful CLI for PBF tax sale list scraper
# - Streams both RAW (requested field names) and normalized CSV/NDJSON if desired

import sys, csv, argparse, asyncio, json
from typing import Optional

from pbfcm_engine import PBFcmsScraper

# optional colors
try:
    from rich.console import Console
    from rich.text import Text
    RICH = True
except Exception:
    RICH = False
    Console = None
    Text = None

RAW_HEADERS = ["tax-list-entity-title", "tax-list-file", "tax-list-file href"]
CSV_FIELDS = ["entity_title", "file_label", "file_url", "file_type"]

def _short(s: Optional[str], n: int = 100) -> str:
    if not s: return ""
    s = " ".join(s.split())
    return s if len(s) <= n else (s[: n-1] + "…")

async def main():
    ap = argparse.ArgumentParser(description="Scrape https://www.pbfcm.com/taxsale.html")
    ap.add_argument("--out-raw-tsv", type=str, help="Write RAW fields (TSV) to file")
    ap.add_argument("--raw-stdout", action="store_true", help="Stream RAW TSV to stdout")
    ap.add_argument("--out-csv", type=str, help="Write normalized CSV to file")
    ap.add_argument("--ndjson", type=str, help="Write normalized NDJSON to file")
    ap.add_argument("--no-colors", action="store_true", help="Disable colored logs")
    ap.add_argument("--no-progress", action="store_true", help="Disable progress lines")
    ap.add_argument("--no-headless", action="store_true", help="Show browser window")
    args = ap.parse_args()

    raw_tsv = None
    if args.out_raw_tsv:
        raw_tsv = open(args.out_raw_tsv, "w", encoding="utf-8", newline="")
        raw_tsv.write("\t".join(RAW_HEADERS) + "\n")
    elif args.raw_stdout:
        raw_tsv = sys.stdout
        raw_tsv.write("\t".join(RAW_HEADERS) + "\n")

    csv_out = open(args.out_csv, "w", encoding="utf-8", newline="") if args.out_csv else None
    csv_writer = None
    if csv_out:
        csv_writer = csv.DictWriter(csv_out, fieldnames=CSV_FIELDS)
        csv_writer.writeheader()

    ndjson_out = open(args.ndjson, "w", encoding="utf-8") if args.ndjson else None

    console = Console(stderr=True) if (RICH and not args.no_colors and not args.no_progress) else None

    scraper = PBFcmsScraper(headless=not args.no_headless)
    try:
        data = await scraper.scrape()
        raw = data["raw"]
        norm = data["normalized"]

        # print progress
        if not args.no_progress:
            for i, n in enumerate(norm, 1):
                line = f"[{i:03d}] {_short(n.get('entity_title'))}  —  {_short(n.get('file_label'))}"
                if console:
                    t = Text(line)
                    if (n.get("file_type") or "") == "pdf":
                        t.stylize("bold white")
                    else:
                        t.stylize("dim")
                    console.print(t)
                else:
                    print(line, file=sys.stderr)

        # stream outputs
        if raw_tsv:
            for r in raw:
                row = [ (r.get(h) or "").replace("\t"," ").replace("\n"," ").strip() for h in RAW_HEADERS ]
                raw_tsv.write("\t".join(row) + "\n")
            raw_tsv.flush()

        if csv_writer:
            for n in norm:
                csv_writer.writerow(n)
            csv_out.flush()

        if ndjson_out:
            for n in norm:
                ndjson_out.write(json.dumps(n, ensure_ascii=False) + "\n")
            ndjson_out.flush()

    finally:
        if raw_tsv and raw_tsv is not sys.stdout:
            raw_tsv.close()
        if csv_out:
            csv_out.close()
        if ndjson_out:
            ndjson_out.close()
        await scraper.stop()

if __name__ == "__main__":
    asyncio.run(main())
