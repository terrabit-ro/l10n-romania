## 19.0.1.10.1

- Fix the postal code prefix of Giurgiu county, which was `87` instead of `08`. No
  Giurgiu postal code starts with `87`, so the county was never filled in from the
  postal code, neither on partners nor on the rows of `l10n_ro_zip`. Existing
  databases get the new prefix on update.
