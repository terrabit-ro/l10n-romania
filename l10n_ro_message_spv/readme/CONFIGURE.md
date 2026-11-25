In **Accounting → Configuration → Settings → e-Factura**:

- *Review received invoices*: received invoices arrive in SPV messages as
  To Review and a bill can be created only from an accepted invoice.
- *Download only received invoices*: the cron downloads the archives of the
  received invoices only, not those of the issued invoices.

The cron *Download ZIP SPV Message* downloads the archives of the messages of
the last 60 days, the time ANAF keeps them; an older message is no longer asked
for. Its archive can still be downloaded from the message, while ANAF has it.
