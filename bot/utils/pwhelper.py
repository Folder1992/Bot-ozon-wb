
import concurrent.futures, pathlib, logging, time, json, os
from types import SimpleNamespace
from .logging import setup_logging
setup_logging()
log = logging.getLogger("bot.pw")

def _try_click_banners(page):
    sels = [
        "button:has-text('ОК')", "button:has-text('Окей')", "button:has-text('OK')",
        "button:has-text('Понятно')", "button:has-text('Принять')",
        "button:has-text('Согласен')", "button:has-text('Разрешить')",
        "[data-widget*='cookie'] button", "button#onetrust-accept-btn-handler",
        ".cookies-agree", ".cookies__btn", ".cookie-agree", ".cookie-accept",
    ]
    clicked = False
    for sel in sels:
        try:
            el = page.query_selector(sel)
            if el:
                el.click(timeout=500)
                page.wait_for_timeout(200)
                clicked = True
        except Exception:
            pass
    if not clicked:
        try:
            page.evaluate('''for (const el of document.querySelectorAll("div,section,aside")) {
                  const st = getComputedStyle(el);
                  if ((st.position==="fixed" || st.position==="sticky") && el.innerText &&
                      /cookies|куки|рекомендательн|рек. технологии/i.test(el.innerText)) {
                    el.style.display="none";
                  }
                }''')
        except Exception:
            pass

def _fetch_ozon_composer(page):
    try:
        data = page.evaluate('''() => {
            const path = location.pathname + location.search;
            return fetch(`/api/composer-api.bx/page/json/v2?url=${path}&__rr=1`, {credentials:'include'})
                .then(r => r.json()).catch(() => null);
        }''')
        return data
    except Exception as e:
        log.debug("composer fetch failed: %s", e)
        return None

def _grab_gallery_srcs(page):
    urls = set()
    sels = [
        "img[src*='wbstatic']",
        "img[src*='images.wbstatic']",
        "img[data-src*='wbstatic']",
        "img[data-original*='wbstatic']",
        "picture source[srcset]",
        ".product-page__gallery img",
        "[data-gallery] img",
        "img[srcset]",
    ]
    for sel in sels:
        for el in page.query_selector_all(sel):
            try:
                src = el.get_attribute("src") or el.get_attribute("data-src") or el.get_attribute("data-original")
                if not src:
                    srcset = el.get_attribute("srcset") or el.get_attribute("data-srcset")
                    if srcset:
                        src = srcset.split(",")[-1].strip().split(" ")[0]
                if src:
                    if src.startswith("//"): src = "https:" + src
                    urls.add(src)
            except Exception:
                pass
    return list(urls)

def _get_state_script_text(page, ids=("state-card-app","state-portal-app","state-product-app","__INITIAL_STATE__")):
    for sid in ids:
        try:
            el = page.query_selector(f"script#{sid}")
            if el:
                return el.inner_text()
        except Exception:
            continue
    try:
        el = page.query_selector("[data-state]")
        if el:
            return el.get_attribute("data-state")
    except Exception:
        pass
    return None

def _run_sync_job(url: str, settings, site: str):
    from playwright.sync_api import sync_playwright
    debug_dir = pathlib.Path(settings.debug_dir); debug_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not settings.show_browser,
            slow_mo=settings.slow_mo_ms if settings.show_browser else 0,
            args=["--disable-blink-features=AutomationControlled","--disable-dev-shm-usage","--no-sandbox","--disable-gpu"],
        )
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/127.0.0.0 Safari/537.36"),
            viewport={"width": 1440, "height": 920},
            locale="ru-RU", timezone_id="Europe/Moscow",
            geolocation={"latitude": 55.75, "longitude": 37.61},
            permissions=["geolocation"],
        )
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = ctx.new_page()
        page.set_default_timeout(settings.playwright_timeout_ms)

        log.info("PW goto (%s): %s", site, url)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(700)
        _try_click_banners(page)

        if site == "wb":
            try:
                page.wait_for_selector("h1", timeout=7000)
            except Exception:
                pass
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
                page.wait_for_timeout(500)
            except Exception:
                pass

        try:
            page.wait_for_selector('script[type="application/ld+json"]', timeout=settings.wait_jsonld_ms)
        except Exception:
            pass

        ld_scripts = [el.inner_text() for el in page.query_selector_all('script[type="application/ld+json"]')]

        def _attr(sel):
            el = page.query_selector(sel)
            return el.get_attribute("content") if el else None

        og_title = _attr('meta[property="og:title"]') or ""
        og_images = [n.get_attribute("content") for n in page.query_selector_all('meta[property="og:image"]') if n.get_attribute("content")]

        try:
            h1 = page.locator("h1").first.inner_text()
        except Exception:
            h1 = ""

        state_text = _get_state_script_text(page) if site == "wb" else None
        composer = _fetch_ozon_composer(page) if site == "ozon" else None

        gallery_imgs = _grab_gallery_srcs(page)

        shot = debug_dir / f"{site}_{int(time.time()*1000)}.png"
        try:
            page.screenshot(path=str(shot), full_page=True)
            log.info("PW screenshot saved: %s", shot)
        except Exception as e:
            log.debug("screenshot failed: %s", e)

        html = ""
        try:
            html = page.content()
        except Exception:
            pass

        final_url = page.url
        ctx.close(); browser.close()

        return {
            "html": html,
            "ld_scripts": ld_scripts,
            "og_title": og_title,
            "og_images": og_images,
            "h1": h1,
            "state_text": state_text,
            "composer": composer,
            "gallery_imgs": gallery_imgs,
            "screenshot": str(shot),
            "url": final_url,
        }

def _settings_or_default(settings):
    """Вернёт переданные settings или создаст дефолтные из .env/окружения."""
    if settings is not None:
        return settings
    def _b(name, default=False):
        v = os.getenv(name)
        return (str(v).lower() in ("1", "true", "yes", "y", "on")) if v is not None else default
    return SimpleNamespace(
        debug_dir=os.getenv("DEBUG_DIR", "debug"),
        show_browser=_b("SHOW_BROWSER", False),
        slow_mo_ms=int(os.getenv("PW_SLOWMO", "0")),
        playwright_timeout_ms=int(os.getenv("PW_TIMEOUT_MS", "25000")),
        wait_jsonld_ms=int(os.getenv("PW_WAIT_JSONLD_MS", "1200")),
    )


def run_get_page_data(url: str, settings, site: str):
    settings = _settings_or_default(settings)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_run_sync_job, url, settings, site)
        return fut.result(timeout=(settings.playwright_timeout_ms/1000)+25)
