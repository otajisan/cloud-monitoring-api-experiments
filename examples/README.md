# Examples

3 本の独立したサンプルスクリプトです。

1. **YouTube Data API v3** - キーワード検索サンプル
2. **Cloud Quotas API (ADC 認証)** - QuotaInfo GET サンプル
3. **Cloud Quotas API (API Key 認証)** - QuotaInfo GET サンプル (標準ライブラリのみ)

## 事前準備

### YouTube Data API

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成または選択
2. [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com) を有効化
3. [API キーを作成](https://console.cloud.google.com/apis/credentials)

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

- `youtube_search_sample.py` は標準ライブラリのみで動作します（外部依存なし）
- `cloud_quotas_get_sample.py` は `google-auth` と `requests` が必要です
- `cloud_quotas_get_sample_apikey.py` は標準ライブラリのみで動作します（外部依存なし）

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

## 実行例

### YouTube Data API 検索サンプル

```bash
# デフォルト (ポケモン で検索)
YOUTUBE_API_KEY=your-key python examples/youtube_search_sample.py

# キーワードと件数を指定
python examples/youtube_search_sample.py --q "Minecraft" --max-results 3
```

### Cloud Quotas API GET サンプル (ADC 認証)

#### Discovery mode (推奨: quota 名が分からない場合)

```bash
python examples/cloud_quotas_get_sample.py \
  --project-number 123456789012 \
  --service compute.googleapis.com \
  --discover
```

#### Direct mode (quota 名が分かっている場合)

```bash
python examples/cloud_quotas_get_sample.py \
  --name projects/123456789012/locations/global/services/compute.googleapis.com/quotaInfos/CpusPerProjectPerRegion
```

### Cloud Quotas API GET サンプル (API Key 認証)

外部依存なし・標準ライブラリのみで動作します。

#### Discovery mode

```bash
CLOUD_QUOTAS_API_KEY=your-key python examples/cloud_quotas_get_sample_apikey.py \
  --project-number 123456789012 \
  --service compute.googleapis.com \
  --discover
```

#### Direct mode

```bash
CLOUD_QUOTAS_API_KEY=your-key python examples/cloud_quotas_get_sample_apikey.py \
  --name projects/123456789012/locations/global/services/compute.googleapis.com/quotaInfos/CpusPerProjectPerRegion
```

## 成功時の出力例

### YouTube Data API

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

### Cloud Quotas API

```json
{
  "name": "projects/123456789012/locations/global/services/compute.googleapis.com/quotaInfos/CpusPerProjectPerRegion",
  "quotaId": "CpusPerProjectPerRegion",
  "metric": "compute.googleapis.com/cpus",
  "service": "compute.googleapis.com",
  "isPrecise": true,
  "containerType": "PROJECT",
  "dimensions": ["region"],
  "quotaDisplayName": "CPUs",
  "dimensionsInfos": [
    {
      "dimensions": {
        "region": "us-central1"
      },
      "details": {
        "value": 24
      }
    }
  ]
}
```

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

**対処**: Google Cloud Console で対象 API を有効化してください。

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

### service 名や quota 名の指定が不正

```
Error: HTTP 400
```

**対処**: service 名は `compute.googleapis.com` のような完全な形式で指定してください。

### Discovery mode で quota が見つからない

```
Error: No quotaInfos found for service 'invalid.googleapis.com' in project '123456789012'.
Hint: Check that the service name is correct (e.g. compute.googleapis.com) and that the project number (not project ID) is valid.
```

**対処**: service 名が正しいか、Cloud Quotas API が有効化されているか確認してください。
