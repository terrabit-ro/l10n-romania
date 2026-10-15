## 19.0.1.1.1

- Hide the accounting date in the backorder confirmation wizard when the
  pickings to validate belong to a non-Romanian company (the wizard now takes
  the company from the pickings, not from the current company), and never
  write it on non-Romanian pickings.
- The accounting date no longer defaults to the current date: it is written on
  the pickings only when the user sets it, so validating without touching it
  keeps the standard dates and clearing it no longer erases a date already set
  on the picking.
- The date proposed by the wizard is the accounting date shared by all the
  pickings; when they have different dates, the field is left empty.
- *Validate* and *No Backorder* now write the date on the same pickings, the
  ones validated by the stock core (`button_validate_picking_ids`), including
  the pickings that need no backorder.
