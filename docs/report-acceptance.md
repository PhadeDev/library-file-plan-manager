# Library report and scan controls, 21 October 2026

Acceptance checklist:
- Use confirmed-pasted Manage Libraries v2.9 as the base; keep current selection, deletion, hierarchy, filters and Limited badges.
- Confirmation warns that a scan normally takes 15 minutes or longer. Return promptly; monitor shared status, not an app timer pretending to measure completion.
- Shared status and optimistic-concurrency lock prevent simultaneous scans/exports. Failed/cancelled scans must not be presented as complete. Export requires a successful completed scan.
- Report contains all tracked libraries, not only filtered/expanded rows: library/link, Team, Sub-Team, flagged/named LTD, actual creation date, file-only count, empty and old-empty review flags.
- User switched to CSV for reliability: built-in CSV table action, UTF-8 BOM, all requested columns and explicit missing stats. No cadet records or document contents.
- Files stay in the tenant's restricted LibraryReports library. Existing SharePoint connector only; no Excel/Office Scripts or template requirement.
- Deliver full-screen YAML, both complete flow packages and one ordered setup section. Validate locally and verify published files; tenant execution and Studio appearance remain unverified.

Existing file-count flow completed successfully in about 15 minutes, confirmed by Allan on 21 October. v2.9 is confirmed pasted, despite the stale Vault snapshot. New status flow and export remain drafts until applied.
