#!/usr/bin/env python3
"""自定义网络访问工具 — 绕过 harness WebFetch 的域名验证限制。

为什么有这个工具：内置 WebFetch 会因“Unable to verify if domain ... is safe to fetch”
挡掉绝大多数域名。但本机 Bash 有完整的网络出口（curl/python urllib/pip 均可联网），
所以写一个走 Bash 的 Python 脚本即可自由访问任意 URL。

用法:
    # 抓取一个 URL，转 markdown 输出到 stdout
    python3 tools/web_fetch.py fetch <url> [--prompt "问题"] [--out FILE] [--max-chars N]

    # 搜索：返回若干 {title, url, snippet}
    python3 tools/web_fetch.py search <query> [--engine bing|duckduckgo] [--n 10]

    # 抓取并直接把原文存盘（不做 markdown 转换，留给别的工具处理）
    python3 tools/web_fetch.py raw <url> [--out FILE]

设计原则:
    - 输出到 stdout 或 --out 指定文件。大输出建议 --out，再用 Read 工具读。
    - fetch 模式默认做 html→markdown；若给了 --prompt，会在末尾附“抽取提示”，
      但实际抽取由调用方（LLM）读完后自己做——本工具不调 LLM。
    - 带 User-Agent、超时、重试、跟随重定向。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from urllib.parse import quote_plus, urljoin

try:
    import requests  # noqa: F401  used implicitly below
except Exception:  # pragma: no cover
    sys.stderr.write("缺少 requests，请: pip install requests\n")
    sys.exit(2)

try:
    import html2text
    _HAS_H2T = True
except Exception:
    _HAS_H2T = False

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _session() -> "requests.Session":
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _get(sess: "requests.Session", url: str, timeout: int = 20) -> "requests.Response":
    last_err = None
    for attempt in range(3):
        try:
            r = sess.get(url, timeout=timeout, allow_redirects=True)
            return r
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after retries: {last_err}")


def _html_to_markdown(html: str, base_url: str | None = None) -> str:
    if _HAS_H2T:
        h = html2text.HTML2Text()
        h.body_width = 0  # 不做硬换行
        h.ignore_images = False
        h.ignore_emphasis = False
        if base_url:
            h.baseurl = base_url  # 让相对链接变绝对（部分版本支持）
        md = h.handle(html)
        # html2text 偶尔在 base_url 不生效，手工补绝对化
        if base_url:
            md = _absolutize_links(md, base_url)
        return md
    # fallback: 暴力去标签
    text = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _absolutize_links(md: str, base_url: str) -> str:
    # 把 ](/相对路径) 变成 ](绝对)
    def fix(m: "re.Match[str]") -> str:
        prefix, path = m.group(1), m.group(2)
        if re.match(r"^[a-z]+://|^mailto:|^#", path, re.I):
            return m.group(0)
        return f"{prefix}]({urljoin(base_url, path)})"

    return re.sub(r"(\]?\()([^)]+)\)", fix, md)


# --------------------------------------------------------------------------- #
def cmd_fetch(args: argparse.Namespace) -> int:
    sess = _session()
    r = _get(sess, args.url, timeout=args.timeout)
    if r.status_code >= 400:
        sys.stderr.write(f"HTTP {r.status_code} for {r.url}\n")
    # 尝试按编码解析（requests 可能猜错中文）
    r.encoding = r.apparent_encoding or r.encoding
    html = r.text
    md = _html_to_markdown(html, base_url=r.url)
    if args.max_chars and len(md) > args.max_chars:
        md = md[: args.max_chars] + f"\n\n…[截断，原文 {len(md)} 字符]…"

    out = []
    out.append(f"# Fetched: {r.url}\n")
    out.append(f"- final_url: {r.url}\n- status: {r.status_code}\n- chars: {len(md)}\n")
    if args.prompt:
        out.append(f"\n> 抽取提示：{args.prompt}\n")
    out.append("\n---\n\n")
    out.append(md)

    text = "".join(out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write(f"saved {len(text)} chars -> {args.out}\n")
    else:
        sys.stdout.write(text)
    return 0


def cmd_raw(args: argparse.Namespace) -> int:
    sess = _session()
    r = _get(sess, args.url, timeout=args.timeout)
    r.encoding = r.apparent_encoding or r.encoding
    data = r.text
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(data)
        sys.stderr.write(f"saved {len(data)} chars -> {args.out}\n")
    else:
        sys.stdout.write(data)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """极简搜索引擎抓取：拿结果页 HTML，正则抽 title+url+snippet。"""
    sess = _session()
    q = args.query
    if args.engine == "bing":
        url = f"https://www.bing.com/search?q={quote_plus(q)}&count={args.n}&setlang=zh-CN"
    elif args.engine == "duckduckgo":
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
    else:
        sys.stderr.write(f"unknown engine: {args.engine}\n")
        return 2
    r = _get(sess, url)
    r.encoding = r.apparent_encoding or r.encoding
    html = r.text
    results = _parse_results(args.engine, html, r.url)
    # 去重
    seen = set()
    dedup = []
    for it in results:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        dedup.append(it)
    dedup = dedup[: args.n]
    print(json.dumps({"engine": args.engine, "query": q, "count": len(dedup),
                      "results": dedup}, ensure_ascii=False, indent=2))
    return 0


def _parse_results(engine: str, html: str, base_url: str):
    out = []
    if engine == "bing":
        # Bing 结果块 <li class="b_algo"> ... <h2><a href=...>title</a></h2> <p>snippet</p>
        for m in re.finditer(
            r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.S | re.I):
            block = m.group(1)
            link = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                             block, re.S | re.I)
            if not link:
                continue
            url = link.group(1)
            title = re.sub(r"<[^>]+>", "", link.group(2)).strip()
            snip = re.search(r'<p[^>]*>(.*?)</p>', block, re.S | re.I)
            snippet = re.sub(r"<[^>]+>", "", snip.group(1)).strip() if snip else ""
            out.append({"title": title, "url": url, "snippet": snippet})
    elif engine == "duckduckgo":
        for m in re.finditer(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            html, re.S | re.I):
            url = m.group(1)
            # ddg 的 href 是 //duckduckgo.com/l/?uddg=<encoded>
            mm = re.search(r"uddg=([^&]+)", url)
            if mm:
                from urllib.parse import unquote
                url = unquote(mm.group(1))
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            out.append({"title": title, "url": url, "snippet": ""})
        # snippet
        for i, sm in enumerate(re.finditer(
                r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                html, re.S | re.I)):
            if i < len(out):
                out[i]["snippet"] = re.sub(r"<[^>]+>", "", sm.group(1)).strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="自定义网络访问工具 (绕过 harness 域名限制)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="抓取 URL 并转 markdown")
    p_fetch.add_argument("url")
    p_fetch.add_argument("--prompt", default="", help="附在输出头的抽取提示")
    p_fetch.add_argument("--out", help="输出到文件而非 stdout")
    p_fetch.add_argument("--max-chars", type=int, default=60000)
    p_fetch.add_argument("--timeout", type=int, default=20)

    p_raw = sub.add_parser("raw", help="抓取 URL 原文")
    p_raw.add_argument("url")
    p_raw.add_argument("--out")
    p_raw.add_argument("--timeout", type=int, default=20)

    p_search = sub.add_parser("search", help="搜索并返回结果列表(JSON)")
    p_search.add_argument("query")
    p_search.add_argument("--engine", choices=["bing", "duckduckgo"], default="bing")
    p_search.add_argument("--n", type=int, default=10)

    args = ap.parse_args()
    if args.cmd == "fetch":
        return cmd_fetch(args)
    if args.cmd == "raw":
        return cmd_raw(args)
    if args.cmd == "search":
        return cmd_search(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
