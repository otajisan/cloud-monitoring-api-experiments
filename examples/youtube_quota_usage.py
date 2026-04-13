#!/usr/bin/env python3
"""YouTube Data API quota usage report.

Combines Cloud Monitoring API (usage) and Cloud Quotas API (limit)
to show quota consumption for YouTube Data API.

Shows all quota types: per day, per minute, per minute per user.

Requires:
  - google-auth, requests
  - ADC: gcloud auth application-default login
  - Cloud Monitoring API enabled
  - Cloud Quotas API enabled
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import google.auth
import google.auth.transport.requests
from google.auth.transport.requests import AuthorizedSession


MONITORING_BASE = "https://monitoring.googleapis.com/v3"
QUOTAS_BASE = "https://cloudquotas.googleapis.com/v1"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_session(quota_project=None):
    """Build an authenticated session using ADC."""
    try:
        credentials, _ = google.auth.default(scopes=SCOPES)
    except google.auth.exceptions.DefaultCredentialsError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run: gcloud auth application-default login", file=sys.stderr)
        sys.exit(1)

    if quota_project:
        credentials = credentials.with_quota_project(quota_project)

    return AuthorizedSession(credentials)


def fetch_monitoring_metric(session, project, metric_type, service, interval_start, interval_end):
    """Query Cloud Monitoring API. Returns {quota_metric_label: value} or {}."""
    url = f"{MONITORING_BASE}/projects/{project}/timeSeries"
    params = {
        "filter": (
            f'metric.type="{metric_type}" '
            f'AND resource.type="consumer_quota" '
            f'AND resource.label.service="{service}"'
        ),
        "interval.startTime": interval_start,
        "interval.endTime": interval_end,
    }
    resp = session.get(url, params=params)
    if resp.status_code != 200:
        if resp.status_code == 403 and "quota project" in resp.text.lower():
            print(f"Error: Monitoring API returned HTTP {resp.status_code}", file=sys.stderr)
            print(resp.text, file=sys.stderr)
            print(
                "\nHint: --quota-project が指定されていません。"
                "  --quota-project YOUR_PROJECT_ID を追加してください。",
                file=sys.stderr,
            )
            sys.exit(1)
        return {}

    results = {}
    for ts in resp.json().get("timeSeries", []):
        label = ts.get("metric", {}).get("labels", {}).get("quota_metric", "")
        points = ts.get("points", [])
        if label and points:
            results[label] = int(points[0].get("value", {}).get("int64Value", 0))
    return results


def fetch_all_quota_infos(session, project_number, service):
    """Get all QuotaInfo from Cloud Quotas API with pagination."""
    parent = f"projects/{project_number}/locations/global/services/{service}"
    url = f"{QUOTAS_BASE}/{parent}/quotaInfos"
    all_items = []
    page_token = None

    while True:
        params = {}
        if page_token:
            params["pageToken"] = page_token
        resp = session.get(url, params=params)
        if resp.status_code != 200:
            print(f"Warning: Cloud Quotas API returned HTTP {resp.status_code}", file=sys.stderr)
            break
        data = resp.json()
        all_items.extend(data.get("quotaInfos", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_items


def build_report(quota_infos, allocation_usage, rate_usage):
    """Merge quota definitions with usage data.

    Maps usage to quotas by matching:
      - quota_metric label (e.g. youtube.googleapis.com/default) -> quotaInfo.metric
      - allocation/usage  -> quotas with refreshInterval "day"
      - rate/net_usage    -> quotas with refreshInterval "minute" (etc.)
    """
    report = []
    for qi in quota_infos:
        quota_id = qi.get("quotaId", "")
        metric = qi.get("metric", "")
        display_name = qi.get("metricDisplayName") or qi.get("quotaDisplayName") or quota_id
        refresh = qi.get("refreshInterval", "")

        # Pick the right usage source based on refreshInterval
        if refresh == "day":
            usage = allocation_usage.get(metric, 0)
            interval_label = "per day"
        else:
            usage = rate_usage.get(metric, 0)
            interval_label = f"per {refresh}" if refresh else ""

        # Determine limit
        limit = None
        dims = qi.get("dimensionsInfos", [])
        if dims:
            val = dims[0].get("details", {}).get("value")
            if val is not None:
                limit = int(val)

        # Build display name: e.g. "Queries per day"
        if interval_label:
            # Add scope (per project / per user) from quotaId
            scope = ""
            qid_lower = quota_id.lower()
            if "peruser" in qid_lower:
                scope = " per user"
            full_name = f"{display_name} {interval_label}{scope}"
        else:
            full_name = display_name

        report.append({
            "quota_id": quota_id,
            "display_name": full_name,
            "refresh_interval": refresh,
            "usage": usage,
            "limit": limit,
            "usage_rate": round(usage / limit * 100, 2) if limit else None,
        })

    return report


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Data API quota usage report",
    )
    parser.add_argument(
        "--project-number",
        default=os.environ.get("GCP_PROJECT_NUMBER"),
        help="Google Cloud project number (env: GCP_PROJECT_NUMBER)",
    )
    parser.add_argument(
        "--quota-project",
        default=os.environ.get("GCP_QUOTA_PROJECT"),
        help="Quota project ID for API billing (env: GCP_QUOTA_PROJECT)",
    )
    parser.add_argument(
        "--service",
        default=os.environ.get("GCP_SERVICE", "youtube.googleapis.com"),
        help="Target service (default: youtube.googleapis.com, env: GCP_SERVICE)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted report",
    )
    args = parser.parse_args()

    if not args.project_number:
        parser.error(
            "--project-number (or GCP_PROJECT_NUMBER env) is required."
        )
    if not args.project_number.isdigit():
        parser.error(
            f"--project-number must be numeric, got '{args.project_number}'. "
            f"Run: gcloud projects describe {args.project_number} --format='value(projectNumber)'"
        )

    session = get_session(quota_project=args.quota_project)

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    interval_end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    interval_start = start.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Quota definitions (limits + display names) from Cloud Quotas API
    quota_infos = fetch_all_quota_infos(session, args.project_number, args.service)
    if not quota_infos:
        print(
            f"No quota info found for service '{args.service}' "
            f"in project '{args.project_number}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Usage from Cloud Monitoring API
    allocation_usage = fetch_monitoring_metric(
        session, args.project_number,
        "serviceruntime.googleapis.com/quota/allocation/usage",
        args.service, interval_start, interval_end,
    )
    rate_usage = fetch_monitoring_metric(
        session, args.project_number,
        "serviceruntime.googleapis.com/quota/rate/net_usage",
        args.service, interval_start, interval_end,
    )

    # 3. Merge
    report = build_report(quota_infos, allocation_usage, rate_usage)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    # Formatted output
    service_label = args.service.replace(".googleapis.com", "").replace(".", " ").title()
    print(f"\n{service_label} - Quota Usage\n")
    for entry in report:
        name = entry["display_name"]
        usage = entry["usage"]
        limit = entry["limit"]
        if limit is not None:
            rate = entry["usage_rate"]
            print(f"  {name}: {usage:,} / {limit:,} ({rate}%)")
        else:
            print(f"  {name}: {usage:,} / N/A")
    print()


if __name__ == "__main__":
    main()
