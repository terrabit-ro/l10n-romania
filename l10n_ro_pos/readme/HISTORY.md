## 19.0.1.9.1

- Fix: the cash limit warnings no longer break the core `t-if`/`t-else` chain of the
  payment status, so the remaining/change amount stays visible above 10,000 lei in cash;
  the Sales Details report no longer raises a TypeError when only `date_stop` is given;
  the stock cost columns are shown on the Refunds rows too.
