# Notification Coverage Audit - are alerts actually reaching us?

- **For:** Blake / Continental Silverline Products, L.P.
- **Date:** 2026-06-27
- **Question:** of every portal/co-op/agency we registered with, which ones actually
  deliver opportunity notifications to us, and how do we verify it?

> Generated from `sources/procurement_sources.json` + ingest history. The 'ingest
> evidence' column is a ROUGH indicator (has this source ever produced a row in
> Lead Radar / pipeline / archive?). It is NOT proof a channel works now - the
> **mailbox check below is the definitive test.**

## How notifications reach us (4 channel types)

1. **api** - we pull directly (SAM.gov). Self-verifying: rows appear in the pipeline.
2. **email_notification** - the portal emails `beford@silverlinesleep.com` when a
   matching opportunity posts. The live pipeline (Power Automate -> Gmail -> ingest)
   now captures these. Verify by mailbox search.
3. **saved_search** - alerts fire only if a saved search is set to email. Verify the
   saved search emails + mailbox search.
4. **manual_review / portal_registration** - NO automatic alerts. Co-ops (TIPS,
   Choice Partners, Sourcewell, OMNIA, BuyBoard, HGACBuy), Texas CMBL, and some
   universities require periodic MANUAL portal visits. Nothing to 'receive' - these
   are blind spots by design.

## The definitive check (run this in Outlook)

Buckets 2 and 3 land in `beford@silverlinesleep.com` (Microsoft 365). At
<https://outlook.office.com> search the mailbox over the **last 90 days** for each
sender domain in the tables below. A domain WITH mail = confirmed receiving. A domain
with ZERO mail in 90 days = open that portal and check the notification email +
commodity codes are set and alerts are ON.

Fast version - one combined search (paste, then set date filter to last 90 days):

```
bonfirehub.com OR ionwave.net OR bidnetdirect.com OR beaconbid.com OR eandi.org OR nola.gov OR brla.gov OR arbuy.arkansas.gov OR generalservices.state.nm.us OR infor.com OR txsmartbuy.gov
```

Then eyeball which domains appear and cross-check the tables. (Claude can drive
Outlook to run this for you on request.)

## Email-notification sources (should email you)

| Source | Sender domain | Ingest evidence | Verify |
|---|---|---|---|
| Arkansas ARBuy | `arbuy.arkansas.gov` | seen | search `beford@` for `arbuy.arkansas.gov` (90d) |
| Bernalillo County NM Bonfire | `bernco.bonfirehub.com` | **none yet** | search `beford@` for `bernco.bonfirehub.com` (90d) |
| Bexar County TX Infor | `bexarprod-lm01.cloud.infor.com` | seen | search `beford@` for `bexarprod-lm01.cloud.infor.com` (90d) |
| BidNet Direct - Arkansas Purchasing Group | `bidnetdirect.com` | seen | search `beford@` for `bidnetdirect.com` (90d) |
| BidNet Direct - Louisiana Purchasing Group | `bidnetdirect.com` | seen | search `beford@` for `bidnetdirect.com` (90d) |
| BidNet Direct - Mississippi Purchasing Group | `bidnetdirect.com` | seen | search `beford@` for `bidnetdirect.com` (90d) |
| BidNet Direct - New Mexico Purchasing Group | `bidnetdirect.com` | seen | search `beford@` for `bidnetdirect.com` (90d) |
| BidNet Direct - Oklahoma Purchasing Group | `bidnetdirect.com` | seen | search `beford@` for `bidnetdirect.com` (90d) |
| BidNet Direct - Texas Purchasing Group | `bidnetdirect.com` | seen | search `beford@` for `bidnetdirect.com` (90d) |
| City of Houston Beacon Bid | `beaconbid.com` | seen | search `beford@` for `beaconbid.com` (90d) |
| City of New Orleans BRASS | `nola.gov` | seen | search `beford@` for `nola.gov` (90d) |
| Dallas County TX BidNet | `bidnetdirect.com` | **none yet** | search `beford@` for `bidnetdirect.com` (90d) |
| E&I Cooperative Services | `eandi.org` | seen | search `beford@` for `eandi.org` (90d) |
| East Baton Rouge Parish Purchasing | `brla.gov` | seen | search `beford@` for `brla.gov` (90d) |
| El Paso County TX IonWave | `epcountypurchasing.ionwave.net` | seen | search `beford@` for `epcountypurchasing.ionwave.net` (90d) |
| Harris County Bonfire | `harriscountytx.bonfirehub.com` | **none yet** | search `beford@` for `harriscountytx.bonfirehub.com` (90d) |
| Houston ISD IonWave | `houstonisd.ionwave.net` | **none yet** | search `beford@` for `houstonisd.ionwave.net` (90d) |
| New Mexico State Purchasing Division | `generalservices.state.nm.us` | seen | search `beford@` for `generalservices.state.nm.us` (90d) |
| Oklahoma County OK BidNet | `bidnetdirect.com` | seen | search `beford@` for `bidnetdirect.com` (90d) |
| Pulaski County AR IonWave | `arkansas.ionwave.net` | seen | search `beford@` for `arkansas.ionwave.net` (90d) |
| Tarrant County TX IonWave | `tarrantcountytx.ionwave.net` | **none yet** | search `beford@` for `tarrantcountytx.ionwave.net` (90d) |
| Walker County TX Bonfire | `co-walker-tx.bonfirehub.com` | **none yet** | search `beford@` for `co-walker-tx.bonfirehub.com` (90d) |

## Saved-search sources (alert only if the saved search emails)

| Source | Sender domain | Ingest evidence | Verify |
|---|---|---|---|
| Louisiana LaPAC | `wwwcfprd.doa.louisiana.gov` | seen | search `beford@` for `wwwcfprd.doa.louisiana.gov` (90d) |
| Louisiana State University Procurement / LaPAC | `lsu.edu` | seen | search `beford@` for `lsu.edu` (90d) |
| Mississippi MAGIC Supplier Portal | `dfa.ms.gov` | seen | search `beford@` for `dfa.ms.gov` (90d) |
| Oklahoma OMES Central Purchasing | `oklahoma.gov` | seen | search `beford@` for `oklahoma.gov` (90d) |
| Texas ESBD / Texas SmartBuy | `txsmartbuy.gov` | seen | search `beford@` for `txsmartbuy.gov` (90d) |

## Portal-registration sources (verify registration + any alert option)

| Source | Sender domain | Ingest evidence | Verify |
|---|---|---|---|
| Oklahoma State University Procurement / Jaggaer | `bids.sciquest.com` | seen | check portal periodically (no email) |
| Texas CMBL | `comptroller.texas.gov` | seen | check portal periodically (no email) |
| The Texas A&M University System | `tamus.edu` | **none yet** | check portal periodically (no email) |
| The University of Texas System | `utsystem.edu` | **none yet** | check portal periodically (no email) |
| University of Houston | `uh.edu` | seen | check portal periodically (no email) |
| University of Oklahoma Procurement / Jaggaer | `ou.edu` | seen | check portal periodically (no email) |

## Manual-only sources (NO auto-alerts - schedule periodic portal checks)

| Source | Sender domain | Ingest evidence | Verify |
|---|---|---|---|
| BuyBoard | `buyboard.com` | seen | check portal periodically (no email) |
| Choice Partners | `choicepartners.org` | seen | check portal periodically (no email) |
| HGACBuy | `hgacbuy.org` | seen | check portal periodically (no email) |
| Hinds County MS Purchasing | `hindscountyms.com` | seen | check portal periodically (no email) |
| OMNIA Partners | `omniapartners.com` | seen | check portal periodically (no email) |
| Sourcewell | `sourcewell-mn.gov` | seen | check portal periodically (no email) |
| TIPS | `tips-usa.com` | seen | check portal periodically (no email) |
| Travis County TX Purchasing Transparency Portal | `purchasingtransparency.traviscountytx.gov` | seen | check portal periodically (no email) |

## SAM.gov (api)

Working - 16 ingested rows, pulled directly via the federal API. No action.

## Priority to verify (registered but no ingest evidence yet)

- **Bernalillo County NM Bonfire** (`bernco.bonfirehub.com`) - confirm the notification email/contact + commodity codes on the portal.
- **Dallas County TX BidNet** (`bidnetdirect.com`) - confirm the notification email/contact + commodity codes on the portal.
- **Harris County Bonfire** (`harriscountytx.bonfirehub.com`) - confirm the notification email/contact + commodity codes on the portal.
- **Houston ISD IonWave** (`houstonisd.ionwave.net`) - confirm the notification email/contact + commodity codes on the portal.
- **Tarrant County TX IonWave** (`tarrantcountytx.ionwave.net`) - confirm the notification email/contact + commodity codes on the portal.
- **Walker County TX Bonfire** (`co-walker-tx.bonfirehub.com`) - confirm the notification email/contact + commodity codes on the portal.

*(No evidence can simply mean a quiet period or that the dead email channel never ingested it - the mailbox search settles it.)*

### Scope note
Docs only. Domains/methods from `sources/procurement_sources.json`; evidence from ingest CSVs. PII out of version control.
