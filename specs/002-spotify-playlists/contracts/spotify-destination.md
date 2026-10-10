# Contract: Spotify Destination Adapter

## Purpose

Define the provider-neutral destination boundary used by playlist reconciliation. Spotify-specific HTTP paths, payloads, pagination, rate limits, snapshots, and error formats remain inside the adapter.

## Required operations

```text
authorize() -> AuthorizationStatus
find_managed_playlist(show_id, expected_name) -> ManagedPlaylist | NotFound
create_playlist(show, name, description, visibility) -> ManagedPlaylist
read_playlist_items(provider_playlist_id) -> OrderedDestinationItem[]
append_items(provider_playlist_id, ordered_track_uris) -> MutationResult
remove_items(provider_playlist_id, items_with_positions_or_snapshot) -> MutationResult
update_details(provider_playlist_id, name, description) -> MutationResult
update_cover(provider_playlist_id, image_bytes) -> MutationResult
```

The concrete adapter may batch calls, but each operation must expose typed success/failure results and preserve enough context to identify the show and provider resource.

## Reconciliation contract

1. Validate configuration and authorization before any playlist mutation.
2. Reuse the locally saved playlist ID for the stable show identity. If no ID is saved, search Spotify for an exact-name match, deduplicate results by provider playlist ID, and choose a stable match. Create a playlist only when discovery finds none, then save its ID locally.
3. Maintain the fixed `KEXP - Latest Tracks` aggregate playlist for non-empty batches using the same lookup order.
4. Read the existing ordered items that the authenticated user can manage.
5. Deduplicate by source/destination track identity while preserving existing positions.
6. Append new eligible items in chronological queue order.
7. Remove the oldest items until the configured limit is satisfied.
8. Update the description after a successful playlist reconciliation.
9. Upload the show cover when available; for the aggregate playlist, upload the supplied KEXP logo as its default cover. Convert supported source artwork to a JPEG within the provider size limit, and preserve existing artwork if upload fails where possible.
10. Make retries idempotent by re-reading the playlist and comparing identities before appending or removing.

## Error contract

The adapter maps authentication failure, missing scope, invalid playlist, unresolved track, rate limit, timeout, provider validation, and cover-upload failure into typed project errors. Errors include operation, show ID, and provider resource where safe; tokens, authorization codes, and secrets are always redacted.
