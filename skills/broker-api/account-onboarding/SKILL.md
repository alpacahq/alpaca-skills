---
name: alpaca-broker-account-onboarding
description: Open and manage brokerage accounts via the Alpaca Broker API — account creation, KYC/CIP, identity & disclosures, agreements, document upload (incl. W-8BEN), account status lifecycle, and account updates/closure. Use when a developer is building onboarding, KYC, or account-management flows on Alpaca in any language.
---

# Alpaca Broker API — Account Onboarding & KYC

Create and manage end-user brokerage accounts under your firm. This is the **first** step of any Broker API integration: no funding, journaling, or trading can happen until an account reaches `ACTIVE`.

> Read `alpaca-broker-integration` first for base URLs and auth (client-credentials Bearer token; legacy Basic still works).

## Reference
- Guide: `https://docs.alpaca.markets/docs/getting-started-with-broker-api`, `https://docs.alpaca.markets/docs/accounts`
- API ref: `https://docs.alpaca.markets/reference/createaccount`
- Live schema: `alpaca-docs` MCP → `get-endpoint` title `"Broker API"` path `/v1/accounts`

## 1. Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/accounts` | Create account (submit application) |
| GET | `/v1/accounts` | List/query accounts (returns up to 1000) |
| GET | `/v1/accounts/{account_id}` | Get one account (`AccountExtended`) |
| PATCH | `/v1/accounts/{account_id}` | Update account |
| POST | `/v1/accounts/{account_id}/actions/close` | Close account (returns 204) |
| POST | `/v1/accounts/{account_id}/documents/upload` | Upload owner/KYC documents (array body) |
| GET | `/v1/accounts/{account_id}/documents` | List uploaded documents |
| POST / GET | `/v1/accounts/{account_id}/cip` | Submit / retrieve CIP results |
| GET | `/v1/country-info` | Supported-country data |
| GET | `/v1/events/accounts/status` | SSE stream of account-status changes → see `alpaca-broker-sse-events` |

## 2. Create-account request (`POST /v1/accounts`)

Four objects are **required**: `contact`, `identity`, `disclosures`, `agreements`. `documents` and `trusted_contact` are optional but usually needed for KYC.

```json
{
  "contact": {
    "email_address": "jane@example.com",
    "phone_number": "+15555555555",
    "street_address": ["20 N San Mateo Dr"],
    "city": "San Mateo",
    "state": "CA",            // required if country / country_of_tax_residence is USA
    "postal_code": "94401",
    "country": "USA"          // ISO 3166-1 alpha-3
  },
  "identity": {
    "given_name": "Jane",
    "family_name": "Doe",
    "date_of_birth": "1990-01-01",
    "tax_id_type": "USA_SSN", // see enum below
    "tax_id": "666-55-4321",
    "country_of_tax_residence": "USA",
    "funding_source": ["employment_income"]
  },
  "disclosures": {
    "is_control_person": false,
    "is_affiliated_exchange_or_finra": false,
    "is_politically_exposed": false,
    "immediate_family_exposed": false
  },
  "agreements": [
    { "agreement": "customer_agreement", "signed_at": "2026-01-02T18:09:33Z", "ip_address": "185.13.21.99" }
  ],
  "documents": [ /* OwnerDocumentUploadRequest[] — see §4 */ ],
  "trusted_contact": { "given_name": "Jim", "family_name": "Doe", "email_address": "jim@example.com" }
}
```

**Key field rules:**
- `contact.street_address` is an **array** (max 3 lines). `contact.state` required when country/tax-residence is `USA`.
- `identity.funding_source` is an array; one+ of `employment_income`, `investments`, `inheritance`, `business_income`, `savings`, `family`.
- `tax_id_type` enum is large and country-specific: `USA_SSN`, `USA_ITIN`, `IND_PAN`, `MEX_RFC`, `GBR_NINO`, … plus generic `NATIONAL_ID`, `PASSPORT`, `DRIVER_LICENSE`, `OTHER_GOV_ID`, `NOT_SPECIFIED`. Query the spec for the full list rather than hardcoding.
- Optional top-level: `account_type` (`trading`|`custodial`|`donor_advised`|`ira`), `account_sub_type` (IRA: `traditional`|`roth`), `enabled_assets` (`us_equity`|`us_option`|`crypto`|`ipo`, default `us_equity`), `allow_instant_ach` (default `false` — the partner-side switch for Instant ACH).
- **Deprecated:** `investment_objective`/`investment_time_horizon`/`liquidity_needs`/`risk_tolerance` moved from `identity` to **top-level**.

**Responses:** `200` → account object · `409` email already registered · `422` invalid value · `400` malformed body.

## 3. Agreements

Each entry: `agreement` (`customer_agreement`, `account_agreement`, `margin_agreement`, `crypto_agreement`, `options_agreement`), `signed_at` (RFC3339), `ip_address` (IPv4), optional `revision`. **You must present the agreement text to the user and capture the real signing timestamp + IP** — Alpaca treats these as the legal record. `revision` defaults to the currently-active revision if omitted.

## 4. Documents & W-8BEN

`documents[]` items: `document_type` + (`content` base64 **or** `content_data`).

```json
{ "document_type": "identity_verification", "content": "<base64>", "mime_type": "image/jpeg", "document_sub_type": "passport" }
```

- `document_type` enum includes `identity_verification`, `address_verification`, `date_of_birth_verification`, `tax_id_verification`, `w8ben`, `w9`, `cip_result`, and more.
- `mime_type`: `application/pdf`, `image/png`, `image/jpeg` — plus `application/json` **only** for `w8ben`.
- **W-8BEN shortcut (lesson):** instead of generating a PDF, upload `content_data` as a structured `W8benDocument` JSON object (full_name, country_citizen, permanent_address_*, date_of_birth, ip_address, timestamp, signer_full_name, …) and **Alpaca renders the official form for you**. This is the clean way to satisfy the tax-form requirement for non-US persons programmatically.
- **W-8BEN expires.** A new form must be submitted every three years, in addition to the calendar year it was signed — schedule the renewal, don't treat the upload as one-and-done.
- Doc size cap: **10 MB** per file when using Alpaca's KYC-as-a-service; no cap if you run your own KYC.

## 5. Account status lifecycle

`status` (and `crypto_status`) use the `AccountStatus` enum:

| Status | Meaning |
|--------|---------|
| `INACTIVE` | Not enabled for the given asset |
| `PAPER_ONLY` | Limited to paper trading |
| `ONBOARDING` | Created but KYC not yet performed — **only used with Onfido** (the OpenAPI enum text still describes it as "application expected, not yet submitted") |
| `SUBMITTED` | Submitted, being processed |
| `SUBMISSION_FAILED` | Submission error; Alpaca resolves these, no action needed |
| `ACTION_REQUIRED` | Manual action + a document upload from the user (e.g. a `true` disclosure routes here); see `kyc_results` |
| `APPROVAL_PENDING` | The account did not pass the automatic KYC check, so the team reviews manually — usually no document required |
| `APPROVED` | Approved, waiting to go active |
| `ACTIVE` | **Fully usable** — funding & trading allowed |
| `REJECTED` | Application rejected |
| `ACCOUNT_UPDATED` | Personal information under review; transient, returns to `ACTIVE`. Outgoing transfers are restricted meanwhile |
| `ACCOUNT_CLOSED` | Closed |

**Happy path:** `SUBMITTED → APPROVED → ACTIVE`. `APPROVAL_PENDING` and `ACTION_REQUIRED` are the exception branches when the automatic KYC check does not pass; either can rejoin at `APPROVED` or end in `REJECTED`. (The OpenAPI enum still calls `APPROVAL_PENDING` the "initial value"; the statuses guide is the newer source.)

**Lesson — gate every downstream op on `ACTIVE`.** A `200` from `POST /v1/accounts` does *not* mean tradable. Subscribe to account-status SSE events (or poll `GET /v1/accounts/{id}`) and only enable funding/journals/trading once `status == ACTIVE`. Trying to journal or trade into a non-active account fails. Gate crypto on `crypto_status`, which tracks separately from `status`. Treat `ACCOUNT_UPDATED` as transient-restricted rather than failed — the account returns to `ACTIVE` after review.

## 6. KYC results & CIP

- `kyc_results` on the account object carries `reject`/`accept`/`indeterminate` sets plus `additional_information`. `summary` is `pass`/`fail` (internal only).
- **`KYCResultType` is an extensible string set, not a closed enum.** Examples only: `IDENTITY_VERIFICATION`, `WATCHLIST_HIT`, `W8BEN_CORRECTION`. Generated code must tolerate and preserve unrecognized values rather than parsing into a fixed enum. The documented identifiers live under `KYCResults` at `https://docs.alpaca.markets/reference/getaccount`.
- If you run KYC yourself (or via Onfido/Trulioo/Veriff/etc.), submit results via `POST /v1/accounts/{id}/cip` with a `CIPInfo` body (provider_name, kyc, document, photo, identity, watchlist sub-results). Sub-check results are `clear`/`consider`.
- Minimum to open an individual account: verify **name, date of birth, address, and identification number**.
- `WATCHLIST_HIT` needs no action from the account owner unless Alpaca separately requests it.

## 7. Integration guidance & lessons learned

1. **Normalize inputs to canonical formats before sending.** Country fields must be **ISO 3166-1 alpha-3** (`USA`, `PHL`, …) — strip any UI decoration (flags/emoji, display names) and validate against `GET /v1/country-info`. Garbage in `country`/`country_of_tax_residence` is a common 422.
2. **Capture real agreement metadata.** `signed_at` and `ip_address` must reflect the actual user action, not server time / a placeholder.
3. **Treat creation as async.** Persist the returned `account_id` immediately, then drive UI off the **status events**, not the create response.
4. **Keep sandbox and live credentials/config in separate deployments.** There is nothing in an account id to check — ids are plain UUIDs, and the two environments are separate hosts with separate credentials.
5. **Idempotency on submit.** A `409` on duplicate email is your friend — look up the existing account rather than retrying creation. Store your local user↔`account_id` mapping before the network call so a timeout doesn't orphan an account.
6. **Closing is your responsibility to sequence.** Before `POST .../actions/close`, you must liquidate all positions and withdraw all cash. The account record is not deleted — it goes `ACCOUNT_CLOSED`.

**Related skills:** fund the account → `alpaca-broker-funding-transfers`; move cash in via the firm sweep → `alpaca-broker-journals`; trade → `alpaca-broker-trading-orders`; track status in real time → `alpaca-broker-sse-events`.
