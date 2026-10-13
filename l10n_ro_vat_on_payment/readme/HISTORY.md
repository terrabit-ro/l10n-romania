## 19.0.0.7.1

- Fix the VAT on payment flag staying set on partners whose tax ID has no `RO`
  prefix. When a company loses its VAT registration, its tax ID is stored as
  the bare CUI and ANAF publishes, at the same time, its removal from the VAT
  on payment register. The daily update only loaded the ANAF history for tax
  IDs starting with `RO`, so the removal was never recorded and the partner
  kept the VAT on payment fiscal position. The history is now loaded for every
  numeric CUI; affected partners are corrected on the next run of the cron.
