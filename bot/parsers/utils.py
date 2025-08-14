
import json, re
from typing import Any, Dict, List, Optional, Tuple

def parse_ld_list(html: str, scripts: List[str]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for s in scripts or []:
        try:
            data = json.loads(s)
            if isinstance(data, list): result.extend([x for x in data if isinstance(x, dict)])
            elif isinstance(data, dict): result.append(data)
        except Exception:
            for m in re.finditer(r'{[\s\S]*?}', s):
                try:
                    obj = json.loads(m.group(0))
                    if isinstance(obj, dict): result.append(obj)
                except Exception:
                    pass
    if html:
        for m in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>([\s\S]*?)</script>', html, re.I):
            raw = m.group(1) or ""
            try:
                data = json.loads(raw)
                if isinstance(data, list): result.extend([x for x in data if isinstance(x, dict)])
                elif isinstance(data, dict): result.append(data)
            except Exception:
                pass
    return result

def first_product(ld: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for obj in ld or []:
        if isinstance(obj, dict) and obj.get("@type") == "Product":
            return obj
        if isinstance(obj, dict) and isinstance(obj.get("@graph"), list):
            for x in obj["@graph"]:
                if isinstance(x, dict) and x.get("@type") == "Product":
                    return x
    return None

def _as_text(v: Any) -> Optional[str]:
    if v is None: return None
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, str):
        s = v.strip()
        return s or None
    return None

def _rating(obj: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    ag = obj.get("aggregateRating")
    if isinstance(ag, dict):
        val = ag.get("ratingValue"); cnt = ag.get("reviewCount")
        try:
            if val is not None:
                val = f"{float(val):.1f}".rstrip("0").rstrip(".")
        except Exception:
            pass
        try:
            if cnt is not None: cnt = int(cnt)
        except Exception:
            cnt = None
        return _as_text(val), cnt
    return None, None

def _images(obj: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("image","images","associatedMedia"):
        v = obj.get(key)
        if isinstance(v, list):
            for it in v:
                if isinstance(it, str):
                    out.append(it)
                elif isinstance(it, dict):
                    u = it.get("url") or it.get("contentUrl") or it.get("src")
                    if u: out.append(u)
        elif isinstance(v, str): out.append(v)
    # dedupe keep order
    seen=set(); res=[]
    for u in out:
        if u not in seen:
            seen.add(u); res.append(u)
    return res

def product_fields(product: Dict[str, Any]):
    title = _as_text(product.get("name"))
    description = _as_text(product.get("description"))
    rating, reviews = _rating(product)
    imgs = _images(product)
    return title, description, rating, reviews, imgs

def normalize_urls(urls: List[str]) -> List[str]:
    out=[]
    for u in urls or []:
        if isinstance(u,str):
            u=u.strip()
            if u.startswith("//"): u="https:"+u
            out.append(u)
    seen=set();res=[]
    for u in out:
        if u not in seen:
            seen.add(u);res.append(u)
    return res
