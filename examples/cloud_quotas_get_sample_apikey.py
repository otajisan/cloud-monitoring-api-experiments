#!/usr/bin/env python3
"""Cloud Quotas API GET sample (API Key authentication).

Retrieves QuotaInfo via the Cloud Quotas API and prints the result as JSON.
Uses an API key (from CLOUD_QUOTAS_API_KEY environment variable) for authentication.
No external dependencies required — uses only the Python standard library.

Supports two modes:
  - Direct mode:    --name <full resource name>
  - Discovery mode: --project-number <NUMBER> --service <SERVICE> [--discover]
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


CLOUD_QUOTAS_BASE = "https://cloudquotas.googleapis.com/v1"


def api_get(url, api_key, params=None):
    """Send a GET request with API key authentication."""
    if params is None:
        params = {}
    params["key"] = api_key
    full_url = f"{url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(full_url)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
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


def get_quota_info(api_key, name):
    """GET a single QuotaInfo by full resource name."""
    url = f"{CLOUD_QUOTAS_BASE}/{name}"
    return api_get(url, api_key)


def list_quota_infos(api_key, project_number, service):
    """LIST QuotaInfos for a given project and service."""
    parent = (
        f"projects/{project_number}/locations/global/services/{service}"
    )
    url = f"{CLOUD_QUOTAS_BASE}/{parent}/quotaInfos"
    return api_get(url, api_key, params={"pageSize": 1})


def main():
    parser = argparse.ArgumentParser(
        description="Cloud Quotas API GET sample (API Key auth): retrieve QuotaInfo as JSON",
    )
    parser.add_argument(
        "--name",
        help=(
            "Full resource name for direct GET. "
            "Example: projects/123456789012/locations/global/services/"
            "compute.googleapis.com/quotaInfos/CpusPerProjectPerRegion"
        ),
    )
    parser.add_argument(
        "--project-number",
        help="Google Cloud project number (for discovery mode)",
    )
    parser.add_argument(
        "--service",
        help="Service name, e.g. compute.googleapis.com (for discovery mode)",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Discovery mode: list quotaInfos and GET the first one",
    )
    args = parser.parse_args()

    # Validate arguments
    if args.name:
        pass
    elif args.project_number and args.service:
        pass
    else:
        parser.error(
            "Either --name (direct mode) or "
            "--project-number and --service (discovery mode) are required."
        )

    import os

    api_key = os.environ.get("CLOUD_QUOTAS_API_KEY")
    if not api_key:
        print(
            "Error: CLOUD_QUOTAS_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        print(
            "Create an API key at: https://console.cloud.google.com/apis/credentials",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.name:
        # Direct mode
        data = get_quota_info(api_key, args.name)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        # Discovery mode
        list_data = list_quota_infos(api_key, args.project_number, args.service)
        items = list_data.get("quotaInfos", [])
        if not items:
            print(
                f"Error: No quotaInfos found for service '{args.service}' "
                f"in project '{args.project_number}'.",
                file=sys.stderr,
            )
            print(
                "Hint: Check that the service name is correct "
                "(e.g. compute.googleapis.com) and that the project number "
                "(not project ID) is valid.",
                file=sys.stderr,
            )
            sys.exit(1)

        name = items[0]["name"]
        print(f"Discovered: {name}", file=sys.stderr)
        data = get_quota_info(api_key, name)
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
