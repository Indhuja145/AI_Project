# Phase 0 Bug Changelog

## Fixed before dashboard redesign

- Sentiment scoring counted overlapping substrings such as `fade` and `faded` twice, producing incorrect sentiment for mixed reviews.
- Dashboard filters changed headline metrics but not product priorities or seasonal totals.
- Imported `Casual/General` seasons were omitted from seasonal data and filter choices.
- Missing complaint categories rendered as `null` in Marketing analytics.
- Marketing, Design, and QA startup routing could be overwritten by a later generic `overview` load.
- The frontend contained duplicate implementations of core functions, causing dead controls and unpredictable startup behavior.
- Visible filter, reset, Ask AI, and export controls were not consistently bound to handlers.
- Review export could omit the visible search query and sorting context.
- Nullable imported timestamps rendered as literal `null` and produced unstable sorting.
- Authenticated endpoints lacked consistent role restrictions, including review writes and management dashboard access.
- Empty product catalogs could make natural-language comparison queries raise `max()`/`min()` errors.
- The application had no health-check endpoint or structured request logging.
- Existing mixed-aspect test exposed the substring-scoring defect.

## Remaining implementation phases

Phase 1 introduces distinct Owner, Design, Marketing, and QA workflows. Phase 2 adds shared responsive polish and interaction states. Phase 3 documents and hardens deployment. Phase 4 validates each role end to end.
