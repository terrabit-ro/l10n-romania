**19.0.2.15.1 (2026-10-30)**

- Indexed the SPV message attachment. Every deleted attachment checks this
  column, and without an index each check scanned the whole message table:
  on a database with ~90,000 SPV messages, a batch deletion of attachments
  ran past odoo.sh's 66 s statement limit.

**19.0.2.15.0 (2026-10-22)**

- The SPV sync error notification is no longer linked to the company
  partner: clicking it in Discuss opened that partner's form, which does
  not show the notification. It now opens in a dialog with the full text,
  as on 20.0.
- The Refresh, Download, Get Invoice and Create Invoice buttons are shown
  only to accounting users. A read-only user saw them, and Refresh failed
  with an access error, because the synchronization deletes and creates
  messages.
- "No XML found in the downloaded ZIP." in the message's Error field is
  now translated.

**19.0.2.14.0 (2026-10-20)**

- The SPV message list download no longer fails silently. When ANAF
  answered with HTTP 200 and `status: 401` in the body (expired token),
  the listing returned `False` and the daily cron crashed with a
  `TypeError`, stopping the download for all companies. Any other error
  (HTTP 401/403/500, request limit, an `eroare` from ANAF) was treated
  as an empty list, with nothing logged. Now every such response is
  reported as an error; only ANAF's "Nu exista mesaje" answer means an
  empty list.
- Each company is synchronized in its own savepoint: an error at one
  company does not stop the others and leaves nothing half-done behind
  (the old error messages are no longer deleted when the listing fails).
- A new synchronization error is sent as a notification (in Discuss or
  by email, according to each user's notification preference) to the
  company's accounting managers and settings administrators, who can
  regenerate the ANAF token. The same error is not sent again on every run,
  only when it changes. The time of the last successful synchronization
  is shown in the e-Factura settings. The manual refresh button shows the
  error to the user.
- SPV message views: the `Currency` and `Invoice Amount` columns are no
  longer shown empty in the list, the `Error` state has a red badge, the
  empty `Errors and Info` group is hidden, and the form has no `New`
  button (messages come only from ANAF).

**19.0.2.11.0 (2026-08-19)**

- The partner lookup by tax ID now accepts both spellings of the Romanian
  CIF. ANAF sends the code sometimes with and sometimes without the `RO`
  prefix, while the partner in Odoo may hold the other variant; the
  lookup used to fail in that case and a duplicate `Unknown` partner was
  created for a company already in the database. Both variants are now
  searched, and the tax ID written on a newly created partner is
  normalized without the prefix.
- Multi-company isolation on SPV messages: `Invoice`, `Partner` and
  `Attachment` are company-checked, the downloaded ZIP is stored in the
  message's company, the invoice is created explicitly in that company,
  and the partner lookup/creation is restricted to the message's company
  (or to partners shared between companies). The `Company` field is shown
  in the list, form and search views, together with a `Company` grouping,
  only for users with multi-company rights.

**19.0.2.9.1 (2026-08-13)**

- Matching an SPV message to an invoice no longer leaves the invoice in
  the `invoice_sent` E-Factura state. The EDI document created at match
  time is now `invoice_validated`, a terminal state: the document is
  already in the SPV (the message proves it) and this instance never
  uploaded it, so there is nothing to fetch a status for. With
  `invoice_sent`, the fetch-status cron queried ANAF with an empty
  `l10n_ro_edi_index`, failed on every run, logged the failure in the
  chatter and re-triggered itself every 2 minutes for as long as such an
  invoice existed — an endless loop. This shows up on self-billed
  invoices a customer issues in the supplier's name, which can only be
  matched by hand. Re-sending to the SPV stays blocked, as before.
- Invoices this instance did upload are unaffected: they already carry an
  EDI document with the upload index, so their normal
  `invoice_sent` -> `invoice_validated` flow and signature retrieval are
  untouched.

**19.0.2.7.0 (2026-07-28)**

- The product can now be corrected on a bill line imported from SPV
  without losing the data received from the supplier: the description
  and the unit price read from the XML are kept when a different product
  is selected. Previously the description was overwritten with the
  product name as soon as the product changed on bills fetched by the
  standard `l10n_ro_edi` SPV import (those bills carry
  `l10n_ro_edi_index`, not `l10n_ro_edi_download`, so the former guard
  did not apply to them).
- The guard is now evaluated per line instead of per bill: lines added
  by hand on an SPV bill are filled in from the product as usual, while
  the imported lines keep their SPV values.
- The vendor item code received from SPV is available as an optional
  column on the bill lines, so the user can see what the supplier
  invoiced while correcting the product.

**19.0.2.1.2 (2026-07-09)**

- Fixed duplicate vendor bills when a bill already exists in Odoo (e.g.
  created from a purchase order) and is still in draft when the matching
  invoice is later downloaded from SPV: the deduplication search used to
  only match `posted` invoices, so a draft bill with the same reference
  and vendor was never found, and a second draft bill was created for the
  same document. The search now matches any non-cancelled invoice.

**19.0.2.1.1 (2026-07-05)**

- Clicking "Download embedded PDF" when the invoice XML has no embedded
  PDF now raises a user-friendly error instead of navigating to a raw
  404 page.
- The form view no longer shows the derived attachment fields (ZIP, XML,
  ANAF PDF, embedded PDF) with their file names, since those are only
  materialized on demand and often have no name to display. The four
  download actions are now buttons with suggestive icons in the form
  header instead.

**19.0.2.0.0 (2026-07-02)**

Storage optimization: the signed ANAF ZIP is now the only file stored per
SPV message.

- The XML extracted from the ZIP is no longer stored as a separate
  attachment at download time; the message metadata (reference, amount,
  invoice date, currency) is parsed in memory.
- `attachment_xml_id`, `attachment_anaf_pdf_id` and
  `attachment_embedded_pdf_id` became non-stored computed fields that
  expose the files materialized on the linked invoice.
- The XML is created once, directly on the vendor bill, when the invoice
  is created from the message; the PDF embedded in the XML is attached
  once on the bill as its preview (main attachment).
- The ANAF PDF and the embedded PDF are no longer persisted per message:
  the download buttons stream them on the fly, derived from the ZIP, via
  the new `/l10n_ro/message_spv/<id>/{xml,anaf_pdf,embedded_pdf}` routes.
- Migration: derived attachments of messages linked to an invoice are
  relinked to the invoice; those of messages without an invoice are
  deleted (they can be re-extracted from the ZIP), reclaiming the
  duplicated filestore space.
