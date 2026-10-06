Separate numbering of the documents of Romanian cash journals.

- Each cash payment gets a cash document type, and each type has its own sequence on the cash
  journal: customer receipts (`CH`), supplier payments (`PL`), payment orders (`DP`), collection
  orders (`DI`) and internal transfers (`IT`), instead of the journal's single payment sequence.
- On cash journals, the payment methods post directly on the cash account of the journal (no
  outstanding receipts/payments account), so a cash payment moves the cash account as soon as it
  is posted. When a cash journal is created or its account or payment methods change, the payment
  methods are aligned and the journal's existing lines on the old outstanding account are moved to
  the cash account.
