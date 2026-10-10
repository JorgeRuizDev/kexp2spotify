# Feature Specification: BBC Radio Support

**Feature Branch**: `004-bbc-radio-support`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Add BBC Radio support. Instead of playlists per show, include playlist per radio. Only include music radios."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Follow BBC music radio stations (Priority: P1)

As a listener, I want BBC music plays grouped into one playlist for each radio station, so I can follow a station without its playlist being split by the shows airing on it.

**Why this priority**: Station-level playlists are the central requested change; grouping by show would not meet the feature's purpose.

**Independent Test**: Provide music plays from multiple shows on two supported stations, synchronize them, and verify that each station has one playlist containing its plays and neither station has playlists split by show.

**Acceptance Scenarios**:

1. **Given** eligible music plays from several shows on BBC Radio 1, **When** synchronization runs, **Then** all resolved plays are added to the single playlist named `BBC Radio 1`.
2. **Given** eligible music plays from two supported stations, **When** synchronization runs, **Then** each station's plays appear in its own station playlist and are not mixed into the other station's playlist.
3. **Given** a supported station has no eligible plays yet, **When** synchronization runs, **Then** no empty playlist is created solely for that run.
4. **Given** the supplied service list is evaluated, **When** BBC music support is synchronized, **Then** the nine music services in FR-001 are supported and spoken-word or sports focused services are excluded.

---

### User Story 2 - Keep station playlists current (Priority: P1)

As a listener, I want each station playlist to contain recent music without duplicates, so I can use it as an up-to-date listening queue.

**Why this priority**: Station grouping is useful only if repeated updates preserve a reliable, bounded queue.

**Independent Test**: Synchronize overlapping timestamped plays for one station over multiple runs and verify that the playlist contains unique resolved songs in play order, respects the configured limit, and removes the oldest songs first when full.

**Acceptance Scenarios**:

1. **Given** a station playlist does not exist, **When** the station has eligible resolved tracks, **Then** one playlist is created using the station's listed name.
2. **Given** the station playlist already exists, **When** another synchronization runs, **Then** the existing playlist is updated rather than duplicated.
3. **Given** a song is encountered again in a later run, **When** the station playlist is updated, **Then** a duplicate is not added and the existing song's queue position is preserved.
4. **Given** new songs exceed the configured playlist limit, **When** synchronization completes, **Then** the playlist contains no more than the limit and the oldest songs have been removed first.
5. **Given** the existing Spotify authorization and playlist limit configuration are valid, **When** BBC synchronization runs, **Then** it reuses them without requiring separate BBC credentials or per-show playlist settings.

---

### User Story 3 - Recognize and check station playlists (Priority: P2)

As a listener, I want a station playlist to show its radio identity and latest update time, so I can recognize it and know whether it is current.

**Why this priority**: Station artwork and update information help listeners distinguish playlists and understand their freshness.

**Independent Test**: Synchronize an eligible track for a station with available identity artwork, then inspect the resulting playlist name, cover, and update description.

**Acceptance Scenarios**:

1. **Given** a supported station has an available logo, **When** its playlist is created or updated, **Then** that logo is used as the playlist cover.
2. **Given** a station playlist update completes, **When** a listener inspects its description, **Then** it shows the time and date of the latest successful update in the configured execution timezone.
3. **Given** a station logo is unavailable, **When** its playlist is updated, **Then** track synchronization still completes and existing artwork is preserved when possible.
4. **Given** an operator follows the BBC setup documentation, **When** they check which services are supported and how playlists are grouped, **Then** the documentation lists the nine supported music services and explains station-level grouping.

### Edge Cases

- A BBC play cannot be attributed to one of the supported radio identities; it is skipped and reported rather than assigned to a guessed station.
- A radio play is associated with a show that changes during the synchronization window; plays remain grouped by radio identity.
- A service is present in the supplied station list but has no eligible or resolvable music plays; no blank playlist is created.
- An unsupported BBC service appears in source data; its plays do not create a managed playlist.
- Multiple existing playlists have the same expected station name; selection is deterministic and the duplicate condition is reported for review.
- A station name or identity is missing or invalid; synchronization skips that station's records and reports the issue.
- A song cannot be resolved at the destination; it is skipped and reported while other valid songs continue.
- The source or destination fails partway through an update; the run reports the affected station and can be retried without duplicate playlists or songs.
- The configured playlist limit is missing, invalid, zero, or negative; configuration is rejected before playlists are changed.
- The station logo is missing, unreadable, or rejected; track synchronization continues without inventing replacement artwork.
- No new eligible plays are available; existing playlists are not cleared or reordered unnecessarily.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support music playlists for exactly these BBC services and formats: BBC Radio 1 (youth-orientated music), BBC Radio 1 Anthems (nostalgic and classic popular music), BBC Radio 1 Dance (electronic dance music), BBC Radio 1Xtra (black contemporary music), BBC Radio 2 (adult-orientated music), BBC Radio 3 (classical, jazz, world music and culture), BBC Radio 3 Unwind (classical and meditation music), BBC Radio 6 Music (alternative music), and BBC Radio 6 Indie Forever (indie music).
- **FR-002**: The system MUST classify BBC Radio 1, Radio 1 Anthems, Radio 1 Dance, Radio 1Xtra, Radio 2, Radio 3, Radio 3 Unwind, Radio 6 Music, and Radio 6 Indie Forever as music services, using the formats in the supplied station list as their descriptions.
- **FR-003**: The system MUST exclude BBC Radio 4, BBC Radio 4 Extra, BBC Radio 5 Live, BBC Radio 5 Sports Extra, and BBC local or national services not named in FR-001 from BBC music playlists.
- **FR-004**: The system MUST associate each eligible BBC music play with its radio service identity independently of the show or programme that aired it.
- **FR-005**: For each supported service with at least one eligible resolved track, the system MUST create or update exactly one managed Spotify playlist named exactly as the service is listed in FR-001.
- **FR-006**: The system MUST place eligible tracks from every show on a service into that service's single playlist and MUST NOT create BBC playlists per show.
- **FR-007**: The system MUST keep tracks from different BBC services in separate playlists.
- **FR-008**: The system MUST avoid adding a duplicate destination track to a station playlist and MUST preserve the existing occurrence's queue position when the same track is encountered again.
- **FR-009**: The system MUST add new station tracks in chronological play order and MUST enforce the existing configurable playlist limit independently for each BBC station playlist.
- **FR-010**: When a station playlist exceeds its configured limit, the system MUST remove the oldest tracks first until the playlist is within the limit.
- **FR-011**: When a station logo is available, the system MUST use it as the playlist cover during creation or update; unavailable artwork MUST NOT prevent track synchronization or require invented artwork.
- **FR-012**: After each successful station playlist update, the system MUST set its description to the existing project format `Last updated at HH:MM on DD-MM-YYYY (Timezone) ·  github.com/JorgeRuizDev/kexp2spotify`, using the execution time and configured timezone.
- **FR-013**: The system MUST report source, station attribution, track resolution, playlist, artwork, authorization, and configuration failures with enough context to identify the affected station and operation.
- **FR-014**: The system MUST make station playlist updates safe to retry after an interrupted or partially failed run without creating duplicate playlists or tracks.
- **FR-015**: The system MUST use the existing Spotify authorization and playlist limit configuration rather than requiring a separate authorization or per-show playlist configuration for BBC support.
- **FR-016**: The system MUST document the supported BBC music services and explain that BBC playlists are organized by radio service, not by show.

### Key Entities *(include if data involved)*

- **BBC radio service**: A supported station identity, display name, music format, and optional logo; it is the grouping identity for BBC playlists.
- **BBC music play**: A track aired by a BBC radio service, including the service identity, track details, and play time; it may also carry show or programme metadata that does not determine playlist grouping.
- **Station playlist**: The managed Spotify playlist for one supported BBC radio service, with its station name, artwork, update description, and ordered unique tracks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 9 supported BBC music services can be represented by their exact listed station identity and playlist name.
- **SC-002**: For every supported station with eligible resolved tracks, one successful synchronization produces exactly 1 managed playlist for that station and 0 BBC playlists per show.
- **SC-003**: After every successful update, 100% of managed station playlists contain no duplicate destination tracks and contain no more than the configured playlist limit.
- **SC-004**: 100% of successfully updated station playlists show the latest successful update date and time in the configured timezone.
- **SC-005**: In a repeat run with unchanged source plays, the number of duplicate tracks and duplicate station playlists created is 0.
- **SC-006**: In a review of every managed BBC playlist, listeners can identify its radio service from the playlist title without consulting the show or programme schedule.

## Assumptions

- BBC support is additive to the current KEXP-to-Spotify pipeline; existing KEXP show playlists and its cross-show latest-tracks playlist remain unchanged.
- The supported BBC service list is fixed to the nine music services explicitly named by the user; BBC Radio 4, Radio 4 Extra, Radio 5 Live, Radio 5 Sports Extra, BBC local radio, Radio Scotland, Radio Wales, and Radio Ulster are excluded.
- The service's station identity is available with each eligible play or can be determined from the source data without inferring it from show or programme names.
- A playlist is created when a supported station has at least one eligible track that can be resolved at Spotify; an empty playlist is not created for a station with no eligible tracks.
- The configured Spotify playlist limit, timezone, authorization, and existing track resolution behavior are reused for BBC playlists.
- The station's official logo is used when available through the source data or existing project assets; lack of a logo does not block synchronization.
- Existing playlists are managed only when they can be matched to the supported service identity and expected station name.
- BBC source availability and Spotify availability are dependencies of successful synchronization; details of provider access are decided during planning.
