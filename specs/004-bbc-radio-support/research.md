# Research: BBC Radio Support

**Date**: 2026-10-10

## Decision: Fetch recent segments from the BBC RMS service endpoint

**Decision**: Use the BBC Sounds RMS request shape
`GET https://rms.api.bbc.co.uk/v2/services/{service_id}/segments/latest` with
`experience=domestic`, `offset=0`, and `limit=min(fetch_limit, 10)`. A live request with
`limit=50` returned HTTP 400 and the message `Page limit must be between 1 and 10`; a small-limit
request succeeded. The station is explicit in the URL, so attribution does not depend on
programme or show metadata. Keep this request in `BbcClient`; normalize only music segments for
the fixed nine-service catalog.

**Authentication finding**: This read request was observed to return recent segment metadata
without an API key or BBC login. It is therefore publicly callable in observed behavior, but
BBC does not document RMS as a supported public developer API. Do not describe it as a
guaranteed or officially supported API, and do not add API-key settings. Spotify
authentication remains required for destination playlist changes.

**Evidence**:

- Observed BBC Sounds RMS endpoint: [Radio 1 latest segments](https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest?experience=domestic&offset=0&limit=4). This URL is a direct, unauthenticated read example; availability and schema may change.
- BBC's [Developer Portal](https://developer.bbc.com/) is the published API entry point and does not offer RMS as a documented external developer contract.
- BBC Sounds service identifiers and presentation can be cross-checked through [BBC Sounds](https://www.bbc.co.uk/sounds).

**Alternatives considered**:

- BBC Developer APIs: rejected for this feature because the required station-level recent music segment feed was not found as a documented external API.
- Scraping BBC Sounds pages: rejected because the RMS JSON endpoint supplies structured segment metadata and is less brittle than HTML parsing.
- A BBC API key or account: rejected because the observed RMS read endpoint does not request one; users should not need unneeded credentials.

**Risk treatment**: Isolate the endpoint, catalog IDs, field mapping, status handling, and JSON
validation inside the adapter. Record a sanitized response fixture and test known station IDs.
Do not retry permanent 4xx responses; retry 408, 425, 429, 5xx, and transport failures under
the bounded per-station policy. On HTTP errors, JSON/schema drift, or missing service attribution,
report that station as failed/skipped and continue. A contract test protects against unannounced
changes but cannot provide an upstream compatibility guarantee.

## Decision: Catalog exactly nine music services

The implementation uses an immutable allowlist and never creates a station from arbitrary response content. The candidate service IDs below match the BBC Sounds identifiers used by RMS; verify each using a live contract smoke check during implementation before enabling it.

| Playlist name | RMS service ID | Music format |
|---|---|---|
| BBC Radio 1 | `bbc_radio_one` | Youth-orientated music |
| BBC Radio 1 Anthems | `bbc_radio_one_anthems` | Nostalgic and classic popular music |
| BBC Radio 1 Dance | `bbc_radio_one_dance` | Electronic dance music |
| BBC Radio 1Xtra | `bbc_1xtra` | Black contemporary music |
| BBC Radio 2 | `bbc_radio_two` | Adult-orientated music |
| BBC Radio 3 | `bbc_radio_three` | Classical, jazz, world music and culture |
| BBC Radio 3 Unwind | `bbc_radio_three_unwind` | Classical and meditation music |
| BBC Radio 6 Music | `bbc_6music` | Alternative music |
| BBC Radio 6 Indie Forever | `bbc_radio_six_indie_forever` | Indie music |

**Alternatives considered**: Discover every RMS service dynamically, or accept any `bbc_*` ID.
Rejected because the specification requires exactly nine music services and expressly excludes
spoken-word/sports and local/national services.

## Decision: Use the station endpoint as authoritative attribution

Each catalog entry is fetched independently and assigns its own service identity to normalized
records. No station identity is inferred from a show title, track image, or programme field.
Unexpected service IDs are excluded. RMS item artwork represents segment/track artwork in the
observed response, so it must not be used as the station logo. Station logos belong in the
catalog as optional service-level image URLs from BBC service branding; if an image is absent,
unavailable, invalid, or rejected by Spotify, queue synchronization continues and current artwork
is preserved.

## Decision: Respect the returned segment order without inventing airtimes

The observed latest-segments response is newest-first and includes relative offset/label fields,
not a reliable per-track wall-clock airtime. Preserve the returned order as the source ordering
for queue placement and retain any supplied offset verbatim in `raw_json`. Do not convert an
offset label into a fabricated timestamp. The execution capture time may be stored for ingestion
and playlist metadata; stable source ordering resolves items within a single fetch.

## Decision: Keep provider event deduplication source-qualified

The existing SQLite unique key is `songs.track_id`. Build BBC event identity from the station
ID plus the RMS segment `id` (or `urn` fallback), e.g.
`bbc:bbc_radio_one:<segment-id>`. Retain the full payload and normalized station ID in
`raw_json`. Spotify queue reconciliation separately de-duplicates resolved track URIs, so the
same recording remains unique within a station while a play on another station stays eligible
for that station's playlist.

## Decision: Continue the combined update after individual failures

Authenticate Spotify and validate shared configuration once before changing playlists. Then
process KEXP and each of the nine BBC stations as independent units, applying bounded retries
inside each unit. A terminal station failure is logged and aggregated; it does not stop later
stations or KEXP. Continue track-resolution, playlist, and artwork steps for unaffected units.
At completion, persist the aggregate run outcome and return nonzero if any unit failed. Global
configuration, Spotify authentication, or shared database failures remain fatal because no
unit can safely proceed without them.

**Rationale**: The user specifically requires a service failure not to stop the whole process.
Retrying a whole combined operation could re-run successful units and obscure the failed
station; unit-level retries keep failures attributable and make completed playlist updates
idempotent.

