Romanian cash register (*Registru de casă*, form 14-4-7A of OMFP 2634/2015) as a numbered
document, one per cash journal and day.

- the register is numbered with its own sequence, unique per journal and date;
- the opening balance is carried over automatically from the previous day and the closing
  balance is computed from the posted entries on the cash account of the journal
  (`default_account_id`, e.g. 5311);
- the day's movements are listed with receipts, payments, the explanation and the partner;
- the register prints in the layout of the form;
- **daily closing**: closing a day freezes its balance, and no entry on the cash account dated on
  that day or earlier can be posted, reset to draft or deleted until the register is reopened.
  Reopening a day also reopens the later closed days of the same cash journal, because the
  balance is carried forward from day to day. A day in the future or with a negative balance
  cannot be closed. Corrections for a closed day are made with a reversal or a correction entry
  dated today.
