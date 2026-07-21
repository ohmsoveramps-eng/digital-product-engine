#!/usr/bin/env python3
"""Manage local Gumroad product listing pages: list, create, push, preview.

Gumroad's public API cannot create products or upload files -- that is
web-dashboard only (see https://github.com/antiwork/gumroad/issues/4019,
an open feature request for exactly this). So the four commands split the
work accordingly:

  list     GET  /v2/products            -- table of live products
  create   (no API call)                -- scaffold gumroad/<slug>.json,
                                            open the dashboard "new product"
                                            page for manual creation
  push     PUT  /v2/products/:id        -- sync name/price/description/tags
                                            to an EXISTING product id you
                                            pasted into the listing file
  preview  (no API call)                -- render the listing as text + a
                                            local HTML file, no network use

`push` cannot attach or replace the downloadable file or cover image --
verify those on the dashboard after pushing. The exact form-encoded param
names Gumroad's v2 API accepts for "tags" are not fully documented; push
prints the raw API response so you can confirm what actually took effect.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

API_BASE = "https://api.gumroad.com/v2"
PAGES_DIR = Path.home() / "digital-product-engine" / "gumroad"
PREVIEW_DIR = Path.home() / "digital-product-engine" / "build" / "previews"
TOKEN_ENV_VAR = "GUMROAD_ACCESS_TOKEN"
TOKEN_HELP_URL = "https://app.gumroad.com/settings/advanced (Applications section)"

TEMPLATE = {
    "product_title": "REPLACE ME",
    "tagline": "",
    "price": 0,
    "tags": [],
    "file": "",
    "cover_image_spec": "1280x720px, dark background",
    "description": "",
    "product_id": None,
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_token() -> str:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        fail(
            f"{TOKEN_ENV_VAR} is not set. Generate an access token at {TOKEN_HELP_URL} "
            f"and export it: export {TOKEN_ENV_VAR}=..."
        )
    return token


def page_path(slug: str) -> Path:
    return PAGES_DIR / f"{slug}.json"


def load_page(slug: str) -> dict:
    path = page_path(slug)
    if not path.exists():
        fail(f"No listing file found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")


def price_dollars(data: dict) -> float:
    value = data.get("price", data.get("price_normal"))
    if value is None:
        fail("Listing has no 'price' or 'price_normal' field.")
    return float(value)


def api_request(method: str, path: str, token: str, **kwargs) -> dict:
    url = f"{API_BASE}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    params = kwargs.pop("params", {}) or {}
    params.setdefault("access_token", token)
    try:
        response = requests.request(
            method, url, headers=headers, params=params, timeout=30, **kwargs
        )
    except requests.RequestException as exc:
        fail(f"Request to Gumroad API failed: {exc}")

    try:
        payload = response.json()
    except ValueError:
        fail(
            f"Gumroad API returned non-JSON response ({response.status_code}): "
            f"{response.text[:500]}"
        )

    if not response.ok or payload.get("success") is False:
        fail(f"Gumroad API error ({response.status_code}):\n{json.dumps(payload, indent=2)}")
    return payload


def cmd_list(_args: argparse.Namespace) -> None:
    token = require_token()
    payload = api_request("GET", "/products", token)
    products = payload.get("products", [])
    if not products:
        print("No products found on this Gumroad account.")
        return
    print(f"{'ID':<24} {'PUBLISHED':<10} {'PRICE':>10}  NAME")
    for p in products:
        price = p.get("formatted_price", p.get("price", ""))
        published = "yes" if p.get("published") else "no"
        print(f"{p.get('id', ''):<24} {published:<10} {str(price):>10}  {p.get('name', '')}")


def cmd_create(args: argparse.Namespace) -> None:
    path = page_path(args.slug)
    if path.exists() and not args.force:
        fail(f"{path} already exists. Use --force to overwrite.")
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(TEMPLATE, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote template: {path}")
    print("Next steps:")
    print("  1. Fill in product_title, tagline, price, tags, file, description.")
    print("  2. Create the product manually at https://app.gumroad.com/products/new")
    print("     (Gumroad's API cannot create products or upload files.)")
    print(f"  3. Copy the new product's id into 'product_id' in {path.name}.")
    print(f"  4. Run: gumroad_pages.py push {args.slug}")
    if not args.no_browser:
        subprocess.run(["open", "https://app.gumroad.com/products/new"], check=False)


def cmd_push(args: argparse.Namespace) -> None:
    token = require_token()
    data = load_page(args.slug)
    product_id = data.get("product_id")
    if not product_id:
        fail(
            f"'product_id' is not set in {page_path(args.slug)}. "
            "Create the product manually on Gumroad first, then add its id."
        )
    body = {
        "name": data.get("product_title"),
        "price": round(price_dollars(data) * 100),
        "description": data.get("description", ""),
    }
    if data.get("tags"):
        body["tags[]"] = data["tags"]

    payload = api_request("PUT", f"/products/{product_id}", token, data=body)
    print(f"Pushed metadata to product {product_id}.")
    print(json.dumps(payload.get("product", payload), indent=2))
    print(
        "\nNote: Gumroad's API cannot upload/replace the downloadable file or cover "
        "image, and 'tags[]' support is unverified -- confirm both on the dashboard."
    )


def render_preview_html(slug: str, data: dict) -> str:
    price = data.get("price", data.get("price_normal"))
    rows = [
        ("Title", data.get("product_title", "")),
        ("Tagline", data.get("tagline", "")),
        ("Price", f"${price}" if price is not None else ""),
        ("Tags", ", ".join(data.get("tags", []))),
        ("File", data.get("file", "(none -- service listing)")),
        ("Product ID", data.get("product_id") or "(not yet created)"),
    ]
    rows_html = "\n".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    description_html = "".join(
        f"<p>{para}</p>" for para in data.get("description", "").split("\n\n")
    )
    title = data.get("product_title", slug)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title} -- preview</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
table {{ border-collapse: collapse; margin-bottom: 24px; width: 100%; }}
th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #ddd; }}
th {{ width: 140px; color: #555; }}
p {{ line-height: 1.5; }}
</style></head>
<body>
<h1>{title}</h1>
<table>{rows_html}</table>
{description_html}
</body></html>
"""


def cmd_preview(args: argparse.Namespace) -> None:
    data = load_page(args.slug)
    price = data.get("price", data.get("price_normal"))
    print(f"--- {args.slug} ---")
    print(f"Title:      {data.get('product_title', '')}")
    print(f"Tagline:    {data.get('tagline', '')}")
    print(f"Price:      ${price}" if price is not None else "Price:      (unset)")
    print(f"Tags:       {', '.join(data.get('tags', []))}")
    print(f"File:       {data.get('file', '(none -- service listing)')}")
    print(f"Product ID: {data.get('product_id') or '(not yet created)'}")
    print()
    print(data.get("description", ""))

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    html_path = PREVIEW_DIR / f"{args.slug}.html"
    html_path.write_text(render_preview_html(args.slug, data), encoding="utf-8")
    print(f"\nWrote HTML preview: {html_path}")
    if not args.no_browser:
        subprocess.run(["open", str(html_path)], check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage local Gumroad product listing pages.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List products on the connected Gumroad account.")
    p_list.set_defaults(func=cmd_list)

    p_create = sub.add_parser("create", help="Scaffold a new local listing JSON.")
    p_create.add_argument("slug", help="Filename slug, e.g. mpc-loop-packs")
    p_create.add_argument("--force", action="store_true", help="Overwrite an existing file.")
    p_create.add_argument(
        "--no-browser", action="store_true", help="Do not open the Gumroad dashboard."
    )
    p_create.set_defaults(func=cmd_create)

    p_push = sub.add_parser(
        "push", help="Sync a local listing's metadata to its live Gumroad product."
    )
    p_push.add_argument("slug", help="Filename slug matching gumroad/<slug>.json")
    p_push.set_defaults(func=cmd_push)

    p_preview = sub.add_parser(
        "preview", help="Render a local listing as text + HTML, no network call."
    )
    p_preview.add_argument("slug", help="Filename slug matching gumroad/<slug>.json")
    p_preview.add_argument(
        "--no-browser", action="store_true", help="Do not open the HTML preview."
    )
    p_preview.set_defaults(func=cmd_preview)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
