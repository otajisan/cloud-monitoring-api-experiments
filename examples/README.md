# Examples

YouTube Data API を使い、そのクォータ使用状況を Cloud Quotas API で確認するためのサンプルスクリプト集です。

| スクリプト | 目的 |
|---|---|
| `youtube_search_sample.py` | YouTube Data API v3 でキーワード検索 (クォータを消費する) |
| `cloud_quotas_get_sample.py` | Cloud Quotas API で YouTube Data API のクォータ上限情報を取得 (ADC 認証) |
| `youtube_quota_usage.py` | YouTube Data API の日次クォータ使用率を表示 (Monitoring + Quotas API) |

> **Note**: Cloud Quotas API は API Key 認証をサポートしていません (OAuth2 必須)。
> そのため ADC (Application Default Credentials) を使用します。
> 詳細は末尾の「[検証: API Key 認証について](#検証-api-key-認証について)」を参照してください。

## 全体の流れ

```
1. YouTube Data API で検索を実行        → クォータが消費される
2. Cloud Quotas API で QuotaInfo を取得  → クォータ上限設定を JSON で確認
3. youtube_quota_usage.py を実行         → 使用量・上限・使用率をまとめて表示
```

---

## 事前準備

### 共通

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成または選択
2. **プロジェクト番号** (数字) と **プロジェクト ID** (文字列) の両方を控えておく:
   ```bash
   # プロジェクト番号を確認 (例: 123456789012)
   gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'
   ```
   > **注意**: `--project-number` にはプロジェクト **番号** (数字のみ) を指定してください。
   > プロジェクト ID (例: `salmon-run-scenario-hub`) を渡すとエラーになります。

### YouTube Data API

1. [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com) を有効化
2. [API キーを作成](https://console.cloud.google.com/apis/credentials)

### Cloud Quotas API / Cloud Monitoring API

1. [Cloud Quotas API](https://console.cloud.google.com/apis/library/cloudquotas.googleapis.com) を有効化
2. [Cloud Monitoring API](https://console.cloud.google.com/apis/library/monitoring.googleapis.com) を有効化 (`youtube_quota_usage.py` で使用)
3. ADC をセットアップ:
   ```bash
   gcloud auth application-default login
   ```
4. 実行ユーザーに以下の権限が必要:
   - `cloudquotas.quotas.get`（または `roles/cloudquotas.viewer`）
   - `monitoring.timeSeries.list`（または `roles/monitoring.viewer`）
5. ADC でエンドユーザー認証を使う場合、**クォータプロジェクト** の指定が必要です。
   スクリプト実行時に `--quota-project YOUR_PROJECT_ID` を付けてください

## 依存ライブラリ

```bash
pip install google-auth requests
```

- `youtube_search_sample.py` — 標準ライブラリのみ（外部依存なし）
- `cloud_quotas_get_sample.py` — `google-auth` と `requests` が必要
- `youtube_quota_usage.py` — `google-auth` と `requests` が必要

## 環境変数

| 変数名 | 用途 | 必須 |
|---|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API の API キー | YouTube サンプルで必須 |
| `GCP_PROJECT_NUMBER` | プロジェクト番号 (数字、例: `123456789012`) | Cloud Quotas サンプルで必須 (または `--project-number`) |
| `GCP_QUOTA_PROJECT` | クォータプロジェクト ID (例: `salmon-run-scenario-hub`) | Cloud Quotas サンプルで必須 (または `--quota-project`) |
| `GCP_SERVICE` | 対象サービス名 (例: `youtube.googleapis.com`) | Cloud Quotas サンプルで任意 (または `--service`) |

CLI 引数を指定した場合は環境変数より優先されます。
Cloud Quotas API の認証自体は `gcloud auth application-default login` (ADC) で行います。

`.env.example` をコピーして `.env` を作成し、値を設定してください:

```bash
cp examples/.env.example examples/.env
```

---

## YouTube Data API のクォータ使用状況を確認する手順

### Step 1: YouTube Data API で検索を実行する

```bash
YOUTUBE_API_KEY=your-key python examples/youtube_search_sample.py
```

これで YouTube Data API のクォータが消費されます（search.list は 1 回あたり 100 units）。

オプションでキーワードや件数を変更できます:

```bash
python examples/youtube_search_sample.py --q "Minecraft" --max-results 3
```

### Step 2: Cloud Quotas API でクォータ情報を確認する

YouTube Data API のクォータ情報を取得するには、`--service` に **`youtube.googleapis.com`** を指定します。

環境変数を設定済みであれば、引数を省略できます:

```bash
# .env を読み込む場合
export $(grep -v '^#' examples/.env | xargs)
```

#### 方法 A: Discovery mode（まず何のクォータがあるか調べる）

quota 名が分からない場合は、まず discovery mode で一覧から探します:

```bash
# 環境変数を設定済みの場合
python examples/cloud_quotas_get_sample.py --discover

# または引数で直接指定
python examples/cloud_quotas_get_sample.py \
  --project-number 123456789012 \
  --service youtube.googleapis.com \
  --quota-project YOUR_PROJECT_ID \
  --discover
```

#### 方法 B: Direct mode（クォータ名を直接指定する）

Discovery mode で `name` が判明したら、次回以降は直接指定できます:

```bash
python examples/cloud_quotas_get_sample.py \
  --name projects/123456789012/locations/global/services/youtube.googleapis.com/quotaInfos/YOUR_QUOTA_ID
```

> **Note**: Cloud Quotas API が返すのはクォータの **上限設定** です。
> 現在の **使用量** を確認するには Step 3 を参照してください。

### Step 3: 日次クォータの使用率を確認する

Cloud Monitoring API から使用量を、Cloud Quotas API から上限を取得し、使用率を表示します:

```bash
# 環境変数を設定済みの場合
python examples/youtube_quota_usage.py

# または引数で直接指定
python examples/youtube_quota_usage.py \
  --project-number 123456789012 \
  --quota-project YOUR_PROJECT_ID
```

テーブル形式で出力されます:

```
Youtube - Quota Usage (daily, last 24h)

Metric                                                  Usage      Limit     Rate
----------------------------------------------------------------------------------
default                                                   200     10000     2.0%
```

`--json` オプションで JSON 出力も可能です:

```bash
python examples/youtube_quota_usage.py --json
```

```json
[
  {
    "metric": "youtube.googleapis.com/default",
    "usage": 200,
    "limit": 10000,
    "usage_rate": 2.0
  }
]
```

---

## 成功時の出力例

### YouTube Data API 検索

```json
{
  "kind": "youtube#searchListResponse",
  "etag": "xxxxxxxxxxxx",
  "regionCode": "JP",
  "pageInfo": {
    "totalResults": 1000000,
    "resultsPerPage": 5
  },
  "items": [
    {
      "kind": "youtube#searchResult",
      "etag": "xxxxxxxxxxxx",
      "id": {
        "kind": "youtube#video",
        "videoId": "dQw4w9WgXcQ"
      },
      "snippet": {
        "publishedAt": "2025-01-01T00:00:00Z",
        "channelId": "UCxxxxxxxx",
        "title": "Sample Video Title",
        "description": "Sample description...",
        "channelTitle": "Sample Channel"
      }
    }
  ]
}
```

### Cloud Quotas API (YouTube Data API のクォータ情報)

```json
{
  "name": "projects/123456789012/locations/global/services/youtube.googleapis.com/quotaInfos/QueryPerDayPerProject",
  "quotaId": "QueryPerDayPerProject",
  "metric": "youtube.googleapis.com/quota",
  "service": "youtube.googleapis.com",
  "isPrecise": true,
  "containerType": "PROJECT",
  "quotaDisplayName": "Queries per day",
  "dimensionsInfos": [
    {
      "details": {
        "value": 10000
      }
    }
  ]
}
```

> **Note**: 実際のレスポンス構造は API バージョンやクォータの種類によって異なる場合があります。
> 上記はダミー例です。取得した raw JSON をそのまま確認してください。

---

## 失敗時の典型例

### API が有効化されていない

```
Error: HTTP 403
{
  "error": {
    "code": 403,
    "message": "YouTube Data API v3 has not been used in project ... before or it is disabled.",
    ...
  }
}
```

**対処**: Google Cloud Console で対象 API (YouTube Data API v3 / Cloud Quotas API) を有効化してください。

### クォータプロジェクト未指定

```
Error: HTTP 403
{
  "error": {
    "code": 403,
    "message": "Your application is authenticating by using local Application Default Credentials. The cloudquotas.googleapis.com API requires a quota project, which is not set by default.",
    ...
  }
}
```

**対処**: `--quota-project YOUR_PROJECT_ID` を指定してください:

```bash
python examples/cloud_quotas_get_sample.py \
  --project-number 123456789012 \
  --service youtube.googleapis.com \
  --quota-project YOUR_PROJECT_ID \
  --discover
```

### 認証不足

```
Error: Could not find default credentials.
Run: gcloud auth application-default login
```

**対処**: `gcloud auth application-default login` を実行してください。

### project number と project ID を取り違えている

`--project-number` にプロジェクト ID (文字列) を渡した場合:

```
error: --project-number must be a numeric project number (e.g. 123456789012), not a project ID ('salmon-run-scenario-hub').
Run: gcloud projects describe salmon-run-scenario-hub --format='value(projectNumber)'
```

**対処**: `--project-number` には **プロジェクト番号** (数字のみ、例: `123456789012`) を指定してください。確認方法:

```bash
gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'
```

> `--quota-project` にはプロジェクト **ID** (文字列、例: `salmon-run-scenario-hub`) を指定します。
> 2 つの引数で使う値が違うので注意してください。

### service 名の指定が不正

```
Error: HTTP 400
```

**対処**: YouTube Data API のクォータを確認する場合、service 名は **`youtube.googleapis.com`** です。

### Discovery mode で quota が見つからない

```
Error: No quotaInfos found for service 'youtube.googleapis.com' in project '123456789012'.
Hint: Check that the service name is correct (e.g. youtube.googleapis.com) and that the project number (not project ID) is valid.
```

**対処**:
- プロジェクト番号（project ID ではなく数字のみの番号）が正しいか確認
- Cloud Quotas API が有効化されているか確認
- YouTube Data API v3 がそのプロジェクトで有効化されているか確認（有効化されていないサービスにはクォータ情報がない場合があります）

---

## 検証: API Key 認証について

Cloud Quotas API に対して API Key のみで認証できるか検証しましたが、**利用不可** でした。

### 検証内容

API Key を使って Cloud Quotas API の `quotaInfos.list` エンドポイントを呼び出したところ、以下の `401 UNAUTHENTICATED` エラーが返されました:

```
Error: HTTP 401 Unauthorized
{
  "error": {
    "code": 401,
    "message": "API keys are not supported by this API. Expected OAuth2 access token or other authentication credentials that assert a principal. See https://cloud.google.com/docs/authentication",
    "status": "UNAUTHENTICATED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
        "reason": "CREDENTIALS_MISSING",
        "domain": "googleapis.com",
        "metadata": {
          "method": "google.api.cloudquotas.v1.CloudQuotas.ListQuotaInfos",
          "service": "cloudquotas.googleapis.com"
        }
      }
    ]
  }
}
```

### 結論

- Cloud Quotas API は **API Key 認証を明示的に拒否** しており、OAuth2 アクセストークン等の principal を持つ認証情報が必須
- そのため本リポジトリでは **ADC (Application Default Credentials)** を使用する方式のみ提供している
- YouTube Data API のように API Key だけで利用できる API とは認証要件が異なる点に注意
