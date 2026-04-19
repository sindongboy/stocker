# Kiwoom REST API — Token Issuance

## Endpoint

```
POST /oauth2/token
```

Same path for both live (`api.kiwoom.com`) and mock (`mockapi.kiwoom.com`).

## Request

```http
POST https://api.kiwoom.com/oauth2/token
Content-Type: application/json;charset=UTF-8

{
  "grant_type": "client_credentials",
  "appkey": "<KIWOOM_APP_KEY>",
  "secretkey": "<KIWOOM_APP_SECRET>"
}
```

## Response

```json
{
  "return_code": 0,
  "return_msg": "정상적으로 처리되었습니다",
  "token_type": "Bearer",
  "token": "<access_token>",
  "expires_dt": "20250806151009"
}
```

- `token` — bearer token value (field name is `token`, not `access_token`)
- `expires_dt` — expiry in `YYYYMMDDHHmmss` format (KST)
- `return_code` — `0` means success; any other value is an error

Token TTL is 24 hours. The broker layer caches and refreshes 5 minutes before expiry.

## Usage

All subsequent API calls require:

```http
Authorization: Bearer <token>
```

## Notes

- **Live API requires IP whitelist registration** at https://openapi.kiwoom.com — without it, token issuance returns 500.
- Live and mock keys are issued separately and cannot be swapped.
- Token path is configurable via `KIWOOM_TOKEN_PATH` env var (default: `/oauth2/token`).
