import sys, json, re, time
from pathlib import Path
from bot.utils.pwhelper import run_get_page_data

def main():
    if len(sys.argv) != 2:
        print("Usage: python debug_dump.py <url>")
        sys.exit(1)
    url = sys.argv[1]
    site = "ozon" if "ozon.ru" in url else "wb" if "wildberries.ru" in url else "common"
    res = run_get_page_data(url, None, site=site)

    Path("debug").mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    if site == "ozon":
        m = re.search(r"/product/[^/]*-(\d+)/?", url)
        pid = m.group(1) if m else ts
        Path(f"debug/ozon_{pid}_{ts}.html").write_text(res.get("html",""), "utf-8")
        comp = res.get("composer")
        if comp:
            Path(f"debug/ozon_{pid}_{ts}_composer.json").write_text(
                json.dumps(comp, ensure_ascii=False, indent=2), "utf-8"
            )
        print("Saved Ozon HTML/Composer into debug/")
    elif site == "wb":
        m = re.search(r"/catalog/(\d+)/detail\.aspx", url)
        pid = m.group(1) if m else ts
        Path(f"debug/wb_{pid}_{ts}.html").write_text(res.get("html",""), "utf-8")
        print("Saved WB HTML into debug/")
    else:
        Path(f"debug/page_{ts}.html").write_text(res.get("html",""), "utf-8")
        print("Saved HTML into debug/")

if __name__ == "__main__":
    main()
