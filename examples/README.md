# Examples

YouTube Data API を使い、そのクォータ使用状況を Cloud Quotas API で確認するためのサンプルスクリプト集です。

| スクリプト | 目的 |
|---|---|
| `youtube_search_sample.py` | YouTube Data API v3 でキーワード検索 (クォータを消費する) |
| `cloud_quotas_get_sample.py` | Cloud Quotas API で YouTube Data API のクォータ情報を取得 (ADC 認証) |
| `cloud_quotas_get_sample_apikey.py` | 同上 (API Key 認証 / 標準ライブラリのみ) |

## 全体の流れ

```
1. YouTube Data API で検索を実行 → クォータが消費される
2. Cloud Quotas API で QuotaInfo を取得 → YouTube Data API のクォータ状況を JSON で確認
```

---

## 事前準備

### 共通

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成または選択
2. プロジェクト番号を控えておく:
   ```bash
   gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'
   ```

### YouTube Data API

1. [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com) を有効化
2. [API キーを作成](https://console.cloud.google.com/apis/credentials)

### Cloud Quotas API

1. [Cloud Quotas API](https://console.cloud.google.com/apis/library/cloudquotas.googleapis.com) を有効化
2. 認証方式を選択:

   **ADC 版** (`cloud_quotas_get_sample.py`) を使う場合:
   ```bash
   gcloud auth application-default login
   ```
   実行ユーザーに `cloudquotas.quotas.get` 権限（または `roles/cloudquotas.viewer` ロール）が必要

   **API Key 版** (`cloud_quotas_get_sample_apikey.py`) を使う場合:
   [API キーを作成](https://console.cloud.google.com/apis/credentials) し、Cloud Quotas API へのアクセスを許可

## 依存ライブラリ

```bash
pip install google-auth requests
```

- `youtube_search_sample.py` — 標準ライブラリのみ（外部依存なし）
- `cloud_quotas_get_sample.py` — `google-auth` と `requests` が必要
- `cloud_quotas_get_sample_apikey.py` — 標準ライブラリのみ（外部依存なし）

## 環境変数

| 変数名 | 用途 | 必須 |
|---|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API の API キー | YouTube サンプルで必須 |
| `CLOUD_QUOTAS_API_KEY` | Cloud Quotas API の API キー | API Key 版で必須 |

Cloud Quotas API の ADC 版は環境変数ではなく `gcloud auth application-default login` で認証します。

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

#### 方法 A: Discovery mode（まず何のクォータがあるか調べる）

quota 名が分からない場合は、まず discovery mode で一覧から探します:

**ADC 版:**
```bash
python examples/cloud_quotas_get_sample.py \
  --project-number YOUR_PROJECT_NUMBER \
  --service youtube.googleapis.com \
  --discover
```

**API Key 版:**
```bash
CLOUD_QUOTAS_API_KEY=your-key python examples/cloud_quotas_get_sample_apikey.py \
  --project-number YOUR_PROJECT_NUMBER \
  --service youtube.googleapis.com \
  --discover
```

#### 方法 B: Direct mode（クォータ名を直接指定する）

Discovery mode で `name` が判明したら、次回以降は直接指定できます:

**ADC 版:**
```bash
python examples/cloud_quotas_get_sample.py \
  --name projects/YOUR_PROJECT_NUMBER/locations/global/services/youtube.googleapis.com/quotaInfos/YOUR_QUOTA_ID
```

**API Key 版:**
```bash
CLOUD_QUOTAS_API_KEY=your-key python examples/cloud_quotas_get_sample_apikey.py \
  --name projects/YOUR_PROJECT_NUMBER/locations/global/services/youtube.googleapis.com/quotaInfos/YOUR_QUOTA_ID
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

### 認証不足 (ADC 版)

```
Error: Could not find default credentials.
Run: gcloud auth application-default login
```

**対処**: `gcloud auth application-default login` を実行してください。

### API キー未設定 (API Key 版)

```
Error: CLOUD_QUOTAS_API_KEY environment variable is not set.
Create an API key at: https://console.cloud.google.com/apis/credentials
```

**対処**: 環境変数 `CLOUD_QUOTAS_API_KEY` に API キーを設定してください。

### project number と project id を取り違えている

```
Error: HTTP 404
{
  "error": {
    "code": 404,
    "message": "Requested entity was not found."
  }
}
```

**対処**: `--project-number` には **プロジェクト番号** (数字のみ、例: `123456789012`) を指定してください。プロジェクト ID (例: `my-project`) ではありません。確認方法:

```bash
gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'
```

### service 名の指定が不正

```
Error: HTTP 400
```

**対処**: YouTube Data API のクォータを確認する場合、service 名は **`youtube.googleapis.com`** です。

### Discovery mode で quota が見つからない

```
Error: No quotaInfos found for service 'youtube.googleapis.com' in project '123456789012'.
Hint: Check that the service name is correct (e.g. compute.googleapis.com) and that the project number (not project ID) is valid.
```

**対処**:
- プロジェクト番号（project ID ではなく数字のみの番号）が正しいか確認
- Cloud Quotas API が有効化されているか確認
- YouTube Data API v3 がそのプロジェクトで有効化されているか確認（有効化されていないサービスにはクォータ情報がない場合があります）
