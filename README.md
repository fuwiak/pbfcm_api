# PBFCM API

A web scraping API for Polish Business Financial and Capital Market data.

## API Endpoint

The API is deployed at: `https://pbfcmapi-production.up.railway.app`

## Testing with curl

Here are copy-pasteable `curl` commands to test the API:

### Health Check

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/health" | jq .
```

### Full JSON (raw + normalized)

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/scrape" | jq .
```

### Only the normalized array

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/scrape" | jq '.normalized'
```

### Normalized → NDJSON (one item per line)

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/scrape" \
  | jq -c '.normalized[]' > pbfcm_normalized.ndjson
```

### Normalized → CSV

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/scrape" | jq -r '
  .normalized[] |
  [
    .entity_title, .file_label, .file_url, .file_type
  ] | @csv
' > pbfcm_normalized.csv
```

### Only the raw fields (as returned)

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/scrape" | jq '.raw'
```

### Raw → NDJSON

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/scrape" \
  | jq -c '.raw[]' > pbfcm_raw.ndjson
```

### Raw → TSV (columns: tax-list-entity-title, tax-list-file, tax-list-file href)

```bash
curl -sS "https://pbfcmapi-production.up.railway.app/pbfcm/scrape" | jq -r '
  .raw[] |
  [
    (."tax-list-entity-title" // ""),
    (."tax-list-file" // ""),
    (."tax-list-file href" // "")
  ] | @tsv
' > pbfcm_raw.tsv
```

## Usage Notes

- All commands use `jq` for JSON formatting and processing
- The API returns both raw scraped data and normalized structured data
- Perfect for n8n workflows and quick shell exports
- Use `-sS` flags with curl for silent mode with error reporting
