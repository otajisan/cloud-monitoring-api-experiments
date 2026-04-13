#!/usr/bin/env python3
"""YouTube Data API quota usage report.

Combines Cloud Monitoring API (usage) and Cloud Quotas API (limit)
to show quota consumption for YouTube Data API.

Covers both allocation quotas (per day) and rate quotas (per minute).

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

# Metrics to query, grouped by quota type.
# Note: Monitoring API's quota/limit does not distinguish allocation vs rate,
# so allocation limits come from Cloud Quotas API (which uses refreshInterval).
QUOTA_TYPES = {
    "allocation": {
        "label": "Allocation (per day)",
        "usage": "serviceruntime.googleapis.com/quota/allocation/usage",
        "limit_candidates": [],
    },
    "rate": {
        "label": "Rate (per minute)",
        "usage": "serviceruntime.googleapis.com/quota/rate/net_usage",
        "limit_candidates": [
            "serviceruntime.googleapis.com/quota/rate/limit",
            "serviceruntime.googleapis.com/quota/limit",
        ],
    },
}


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


def fetch_monitoring_metric(session, project, metric_type, service, interval_start, interval_end, fatal=True):
    """Query Cloud Monitoring API for a quota metric."""
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
        if not fatal:
            return None
        print(f"Error: Monitoring API returned HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        if resp.status_code == 403 and "quota project" in resp.text.lower():
            print(
                "\nHint: --quota-project が指定されていません。"
                "  --quota-project YOUR_PROJECT_ID を追加してください。",
                file=sys.stderr,
            )
        sys.exit(1)
    return resp.json()


def fetch_quota_limit(session, project_number, service):
    """Get all QuotaInfo from Cloud Quotas API."""
    parent = f"projects/{project_number}/locations/global/services/{service}"
    url = f"{QUOTAS_BASE}/{parent}/quotaInfos"
    resp = session.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("quotaInfos", [])


def extract_latest_values(time_series_response):
    """Extract metric values from Monitoring API response.

    Returns a dict of {quota_metric_label: latest_int_value}.
    """
    results = {}
    for ts in time_series_response.get("timeSeries", []):
        label = ts.get("metric", {}).get("labels", {}).get("quota_metric", "unknown")
        points = ts.get("points", [])
        if points:
            value = int(points[0].get("value", {}).get("int64Value", 0))
            results[label] = value
    return results


def fetch_usage_and_limit(session, project, service, interval_start, interval_end, quota_type_config):
    """Fetch usage and limit for a given quota type."""
    # Usage
    usage_resp = fetch_monitoring_metric(
        session, project,
        quota_type_config["usage"],
        service, interval_start, interval_end,
        fatal=False,
    )
    usage_map = extract_latest_values(usage_resp) if usage_resp else {}

    # Limit (try candidates)
    limit_map = {}
    for limit_metric in quota_type_config["limit_candidates"]:
        limit_resp = fetch_monitoring_metric(
            session, project,
            limit_metric,
            service, interval_start, interval_end,
            fatal=False,
        )
        if limit_resp:
            limit_map = extract_latest_values(limit_resp)
            if limit_map:
                break

    return usage_map, limit_map


def build_quotas_limit_maps(quotas_info):
    """Build per-type limit maps from Cloud Quotas API response.

    Returns:
        (allocation_limits, rate_limits) - each is {metric: limit_value}

    Uses refreshInterval from Cloud Quotas API to distinguish:
        "day" -> allocation (per day)
        other -> rate (per minute etc.)
    """
    allocation = {}
    rate = {}
    if not quotas_info:
        return allocation, rate
    for qi in quotas_info:
        metric = qi.get("metric", "")
        interval = qi.get("refreshInterval", "")
        dims = qi.get("dimensionsInfos", [])
        if dims:
            val = dims[0].get("details", {}).get("value")
            if val is not None:
                if interval == "day":
                    allocation[metric] = int(val)
                else:
                    rate[metric] = int(val)
    return allocation, rate


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Data API quota usage report (daily + per-minute)",
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

    # Time range: last 24 hours
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    interval_end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    interval_start = start.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fallback limits from Cloud Quotas API (split by quota type)
    quotas_info = fetch_quota_limit(session, args.project_number, args.service)
    allocation_limits, rate_limits = build_quotas_limit_maps(quotas_info)
    fallback_limits = {
        "allocation": allocation_limits,
        "rate": rate_limits,
    }

    # Fetch metrics for each quota type
    all_sections = []
    for qtype, config in QUOTA_TYPES.items():
        usage_map, limit_map = fetch_usage_and_limit(
            session, args.project_number, args.service,
            interval_start, interval_end, config,
        )

        quota_fallback = fallback_limits.get(qtype, {})
        all_metrics = sorted(set(
            list(usage_map.keys()) + list(limit_map.keys()) + list(quota_fallback.keys())
        ))
        if not all_metrics:
            continue
        entries = []
        for metric in all_metrics:
            usage = usage_map.get(metric, 0)
            limit = limit_map.get(metric) or quota_fallback.get(metric)
            entries.append({
                "metric": metric,
                "usage": usage,
                "limit": limit,
                "usage_rate": round(usage / limit * 100, 2) if limit else None,
            })

        all_sections.append({
            "type": qtype,
            "label": config["label"],
            "entries": entries,
        })

    if not all_sections:
        print(
            f"No quota usage data found for service '{args.service}' "
            f"in project '{args.project_number}'.",
            file=sys.stderr,
        )
        print(
            "Hint: YouTube Data API で少なくとも 1 回リクエストを実行してから"
            "数分待つと、Monitoring にデータが反映されます。",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.json:
        print(json.dumps(all_sections, indent=2, ensure_ascii=False))
        return

    # Formatted output
    display_name = args.service.replace(".googleapis.com", "").replace(".", " ").title()
    print(f"\n{display_name} - Quota Usage\n")

    for section in all_sections:
        print(f"[ {section['label']} ]")
        print(f"{'Metric':<50} {'Usage':>10} {'Limit':>10} {'Rate':>8}")
        print("-" * 82)
        for entry in section["entries"]:
            name = entry["metric"].split("/")[-1] if "/" in entry["metric"] else entry["metric"]
            usage_str = str(entry["usage"])
            limit_str = str(entry["limit"]) if entry["limit"] is not None else "N/A"
            if entry["usage_rate"] is not None:
                rate_str = f"{entry['usage_rate']}%"
            else:
                rate_str = "N/A"
            print(f"{name:<50} {usage_str:>10} {limit_str:>10} {rate_str:>8}")
        print()


if __name__ == "__main__":
    main()
