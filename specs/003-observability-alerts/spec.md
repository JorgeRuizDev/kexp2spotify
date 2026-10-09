# Feature Specification: Run Observability and Alerts

**Feature Branch**: `003-observability-alerts`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Add observability to this project. I want the first run of a day to send me a message summarizing the previous day. I also want a message with the error traceback if a run fails after 3 retries."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive the daily summary (Priority: P1)

As the scheduled-process operator, I want to receive a summary of the previous day's runs on the first run of each day so that I can quickly understand the operational state without manually reviewing logs.

**Why this priority**: It provides proactive visibility into normal operation and makes missing runs or unexpected results detectable.

**Independent Test**: Record runs from a previous day, run the process for the first time on a new day, and verify that the operator receives one summary with the correct totals.

**Acceptance Scenarios**:

1. **Given** runs exist for the previous day and its summary has not yet been sent, **When** the first run of the current day begins, **Then** the operator receives a message with successful and failed run counts, received and new songs, and changes made at the destination.
2. **Given** the previous day's summary has already been sent, **When** one or more runs execute again during the same day, **Then** no additional daily summary is sent.
3. **Given** there were no runs on the previous day, **When** the first run of the current day begins, **Then** the operator receives a summary showing zero runs and zero results.

---

### User Story 2 - Receive permanent-failure alerts (Priority: P1)

As the scheduled-process operator, I want to receive an alert when a run cannot complete after its retries so that I can diagnose it and act without continuously monitoring the scheduler.

**Why this priority**: Silent failures can leave the collection or playlists outdated; an actionable alert reduces time to recovery.

**Independent Test**: Force a repeatable failure, verify that three retries occur after the initial attempt, and verify that one message is sent with the command, attempt count, and error traceback.

**Acceptance Scenarios**:

1. **Given** a run fails transiently, **When** the failure occurs before retries are exhausted, **Then** the process tries again and does not send a permanent-failure alert.
2. **Given** a run fails on the initial attempt and all three retries, **When** the fourth attempt ends, **Then** the operator receives a message with run context and the error traceback, and the process ends in a failed state.
3. **Given** a run succeeds after a retry, **When** the process ends, **Then** no failure alert is sent and the history shows that the run completed successfully.

---

### User Story 3 - Keep diagnostics safe and resilient (Priority: P2)

As an operator, I want observability not to expose credentials or turn a notification-channel problem into an additional process failure.

**Why this priority**: Diagnostic information must be useful without increasing security risk or preventing the process from completing its work.

**Independent Test**: Simulate a messaging-channel error and verify that the run retains its original result, the error is recorded safely, and no tokens or credentials appear in messages or logs.

**Acceptance Scenarios**:

1. **Given** the notification channel is not configured or unavailable, **When** a run completes or fails, **Then** the process retains its exit code and records that the notification could not be sent without revealing secrets.
2. **Given** the traceback contains sensitive information or is too long for the channel, **When** the alert is built, **Then** credentials are masked and the traceback is limited to a safe size while preserving the main context.

### Edge Cases

- The first run of the day occurs after one or more days without runs; the summary covers only the immediately preceding calendar day.
- The process runs several times near the day boundary; only one run should claim summary delivery for each day.
- Summary delivery fails; a later run must be able to retry it without duplicating a confirmed delivery.
- A run fails after partially completing an operation; retries must not create duplicates or alter the confirmed state of previous runs.
- Local time and UTC cross different dates; the summary date must follow the configured operational timezone.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST retain a queryable history of every run, including operational date, command, status, attempt count, duration, and relevant processing counters.
- **FR-002**: The system MUST identify the first run of each day using the configured operational timezone.
- **FR-003**: On the first run of a day, the system MUST send a summary of runs from the previous calendar day.
- **FR-004**: The daily summary MUST include at least total runs, successful runs, failed runs, received songs, new songs, and changes made at the destination.
- **FR-005**: The system MUST send at most one confirmed daily summary for each summarized day.
- **FR-006**: If a run fails, the system MUST make an initial attempt and up to three retries before declaring it permanently failed.
- **FR-007**: If a run continues to fail after three retries, the system MUST send an alert with the command, total attempt count, and a diagnostic error traceback.
- **FR-008**: If a run succeeds after a retry, the system MUST record the successful result and MUST NOT send a permanent-failure alert.
- **FR-009**: The system MUST allow the notification destination and delivery timeout to be configured securely.
- **FR-010**: The system MUST hide credentials, tokens, and other secrets from messages, tracebacks, and logs emitted by the feature.
- **FR-011**: A notification-channel failure MUST NOT change the exit code or result of the run that triggered the notification.
- **FR-012**: The system MUST allow retrying delivery of a summary not confirmed as delivered without duplicating already confirmed summaries.

### Key Entities

- **Run record**: Result of a scheduled run, with its operational date, command, status, attempts, counters, and possible error diagnostic.
- **Daily summary**: Aggregation of run records for an operational day and the message associated with that day.
- **Notification status**: Marker indicating whether a daily summary was sent and confirmed, guaranteeing idempotency.
- **Failure alert**: Message addressed to the operator when a run exhausts its retries, including context and a safe diagnostic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of first runs on a day with a configured channel generate a summary of the previous day, with no more than one confirmed summary per summarized day.
- **SC-002**: 100% of persistent failures generate an alert after exactly four total attempts: one initial attempt and three retries.
- **SC-003**: At least 99% of failure messages contain the command, attempt count, and a usable traceback, with no detectable credentials.
- **SC-004**: A notification-channel failure does not change the exit code or prevent completion of the run record in 100% of verifiable cases.
- **SC-005**: A run that recovers during retries generates no permanent-failure alert.

## Assumptions

- The operator has a configured messaging channel and the credentials required to send messages.
- Telegram is the initial notification channel supported by the product; the requirement design does not prevent adding other channels later.
- The project's existing operational timezone is used to determine calendar days for summaries.
- History and notification-status data are retained alongside existing operational data; long-term retention policies are outside this feature.
- Retries apply to scheduled collection and update runs, not to the interactive authorization flow.
