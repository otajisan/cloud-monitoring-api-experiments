#!/usr/bin/env python3
"""YouTube Data API v3 search sample.

Searches YouTube for videos and prints the response JSON to stdout.
API key is read from the YOUTUBE_API_KEY environment variable.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Data API v3 search sample",
    )
    parser.add_argument(
        "--q",
        default="ポケモン",
        help="Search query (default: ポケモン)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results (default: 5)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YOUTUBE_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get an API key at: https://console.cloud.google.com/apis/credentials", file=sys.stderr)
        sys.exit(1)

    params = urllib.parse.urlencode({
        "key": api_key,
        "q": args.q,
        "part": "snippet",
        "type": "video",
        "maxResults": args.max_results,
    })
    url = f"{YOUTUBE_SEARCH_URL}?{params}"

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} {e.reason}", file=sys.stderr)
        try:
            body = e.read().decode("utf-8")
            print(body, file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: {e.reason}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
