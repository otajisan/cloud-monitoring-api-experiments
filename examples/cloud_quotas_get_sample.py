#!/usr/bin/env python3
"""Cloud Quotas API GET sample.

Retrieves QuotaInfo via the Cloud Quotas API and prints the result as JSON.
Uses Application Default Credentials (ADC) for authentication.

Supports two modes:
  - Direct mode:    --name <full resource name>
  - Discovery mode: --project-number <NUMBER> --service <SERVICE> [--discover]
"""

import argparse
import json
import sys

import google.auth
import google.auth.transport.requests


CLOUD_QUOTAS_BASE = "https://cloudquotas.googleapis.com/v1"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_authenticated_session():
    """Build an authenticated requests.AuthorizedSession using ADC."""
    try:
        credentials, project = google.auth.default(scopes=SCOPES)
    except google.auth.exceptions.DefaultCredentialsError as e:
        print(f"Error: Could not find default credentials.\n{e}", file=sys.stderr)
        print(
            "Run: gcloud auth application-default login",
            file=sys.stderr,
        )
        sys.exit(1)

    from google.auth.transport.requests import AuthorizedSession

    return AuthorizedSession(credentials)


def get_quota_info(session, name):
    """GET a single QuotaInfo by full resource name."""
    url = f"{CLOUD_QUOTAS_BASE}/{name}"
    resp = session.get(url)
    if resp.status_code != 200:
        print(f"Error: HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)
    return resp.json()


def list_quota_infos(session, project_number, service):
    """LIST QuotaInfos for a given project and service."""
    parent = (
        f"projects/{project_number}/locations/global/services/{service}"
    )
    url = f"{CLOUD_QUOTAS_BASE}/{parent}/quotaInfos"
    resp = session.get(url, params={"pageSize": 1})
    if resp.status_code != 200:
        print(f"Error: HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)
    return resp.json()


def main():
    parser = argparse.ArgumentParser(
        description="Cloud Quotas API GET sample: retrieve QuotaInfo as JSON",
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
        # Direct mode
        pass
    elif args.project_number and args.service:
        # Discovery mode
        pass
    else:
        parser.error(
            "Either --name (direct mode) or "
            "--project-number and --service (discovery mode) are required."
        )

    session = get_authenticated_session()

    if args.name:
        # Direct mode: GET the specified resource
        data = get_quota_info(session, args.name)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        # Discovery mode: list first, then GET
        list_data = list_quota_infos(session, args.project_number, args.service)
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
        data = get_quota_info(session, name)
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
