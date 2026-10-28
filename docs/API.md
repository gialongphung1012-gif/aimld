# AIMLD License API

Base URL: `https://your-domain.example`
All bodies and responses are JSON. Use HTTPS in production.

## `POST /api/license/activate`

```json
{"key":"AIMLD-ABCDE-FGHIJ-KLMNP-QRSTU","device_id":"persistent-device-uuid","device_label":"iPhone"}
```

Success `200`:

```json
{"ok":true,"code":"KEY_VALID","message":"License activated","activation_token":"returned-once","expires_at":"2027-01-01T00:00:00Z","max_devices":1}
```

Errors: `400 INVALID_DEVICE`, `404 KEY_NOT_FOUND`, `403 KEY_EXPIRED|KEY_BLOCKED|KEY_REVOKED`, `409 DEVICE_LIMIT`, `429 RATE_LIMITED`, `500 SERVER_ERROR`.

## `POST /api/license/validate`

Validation uses the activation token returned once by `/activate`; the raw key is not sent repeatedly.

```json
{"activation_token":"token-returned-by-activate","device_id":"persistent-device-uuid"}
```

Success includes `ok`, `code`, `message`, `expires_at`, and `device_limit`. Errors include `INVALID_ACTIVATION`, `ACTIVATION_NOT_FOUND`, `KEY_EXPIRED`, `KEY_BLOCKED`, and `KEY_REVOKED`. The app stores the token in iOS Keychain.

## `POST /api/license/deactivate`

```json
{"device_id":"persistent-device-uuid","activation_token":"token-returned-by-activate"}
```

The activation token is stored hashed on the server. Success: `200 DEACTIVATED`. Keep the token in Keychain and never log it.

## `GET /api/license/status?device_id=...`

Send `Authorization: Bearer <activation_token>`. The key and token are not placed in the URL. Returns current status for the matching activated device.

## Admin

`GET /admin/login` and `POST /admin/login` manage the web session. `GET /api/admin/overview` requires an authenticated admin session. Web admin forms use CSRF tokens. Admin keys are managed in the responsive dashboard: create/bulk create, search/filter, block/unblock, revoke, extend, reset devices, activation history, CSV export. `GET /admin/history` shows recent admin actions and license activation/validation success/failure events; logs intentionally omit raw keys and activation tokens.

## Example cURL

```sh
curl -sS https://your-domain.example/health
curl -sS -X POST https://your-domain.example/api/license/activate \
  -H 'Content-Type: application/json' \
  -d '{"key":"AIMLD-ABCDE-FGHIJ-KLMNP-QRSTU","device_id":"device-uuid-1234","device_label":"iPhone"}'
```
