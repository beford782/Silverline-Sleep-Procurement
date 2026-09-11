# Reject-log audit trail
Auto-ingest tools append relevance-rejected rows here (per-channel _<channel>.csv)
so silent misses become reviewable. Files are created on first reject.

## _permits.csv (tools/ingest_permits.py)
Own header, separate from the relevance-channel logs:

`rejected_date, source, permit_number, issue_date, work_class, reason, description, source_url`

`reason` vocabulary:

- `exclude_term:<term>` - description matched a configured `exclude_terms` entry.
- `work_class_excluded:<wc>` - permit work class is not one the config accepts.
- `non_bp:<type>` - `permittype` is not BP (standalone trade permit).
- `no_keyword` - description matched none of the configured `keywords` under the
  local whole-word check. Live records land here too: the Socrata query is a
  looser substring LIKE over-fetch, and the local filter is the one that counts.
- `duplicate` - already present in the Demand Radar (active or archive) or already
  grouped under another permit in this run.
- `classifier:<reason>` - passed every permit filter, but `demand_signal.py`
  rejected it; `<reason>` is the classifier's own reason string.

Not written under `--dry-run` (unlike the relevance-channel logs), so a dry run
leaves the tree untouched.

No contractor phone numbers or person names are written; the description and
address are the city's published permit text.
