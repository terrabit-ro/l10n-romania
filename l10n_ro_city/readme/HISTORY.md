## 19.0.1.10.2

- Add the towns Breaza (Prahova), Băile Govora, Băile Olănești, Ocnele Mari (Vâlcea)
  and Eforie (Constanța). None of them has a component locality with the town's name,
  so they were missing from the list, while the post office and the partners' addresses
  use the town's name. They carry the SIRUTA code of the town itself. On update, a town
  of the same name created by hand in that county is kept and completed, not duplicated.
- Fix the names of Sfântu Gheorghe (two spaces) and Popești-Leordeni (hyphen).

## 19.0.1.10.1

- Fix the postal code prefix of Giurgiu county, which was `87` instead of `08`. No
  Giurgiu postal code starts with `87`, so the county was never filled in from the
  postal code, neither on partners nor on the rows of `l10n_ro_zip`. Existing
  databases get the new prefix on update.
