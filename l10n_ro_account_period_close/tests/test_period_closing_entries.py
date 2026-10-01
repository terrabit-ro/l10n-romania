# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPeriodClosingEntries(AccountTestInvoicingCommon):
    """Verifică notele contabile (Dr/Cr) generate de închiderea de perioadă."""

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.misc_journal = cls.company_data["default_journal_misc"]
        cls.date_from = fields.Date.from_string("2025-03-01")
        cls.date_to = fields.Date.from_string("2025-03-31")

        def account(code, account_type, **kw):
            return cls.env["account.account"].create(
                dict(
                    name="Test " + code,
                    code=code,
                    account_type=account_type,
                    company_ids=cls.company.ids,
                    **kw,
                )
            )

        cls.acc_601 = account("601900", "expense")
        cls.acc_602 = account("602900", "expense")
        cls.acc_707 = account("707900", "income")
        cls.acc_711 = account("711900", "income", l10n_ro_close_check=True)
        cls.acc_345 = account("345900", "asset_current")
        cls.acc_4111 = account("411900", "asset_receivable", reconcile=True)
        cls.acc_401 = account("401900", "liability_payable", reconcile=True)
        cls.acc_4426 = account("442690", "asset_current")
        cls.acc_4427 = account("442790", "liability_current")
        cls.acc_4423 = account("442390", "liability_current")
        cls.acc_4424 = account("442490", "asset_current")
        cls.acc_1211 = account("121900", "equity")
        cls.acc_1212 = account("121901", "equity")
        cls.acc_512 = account("512900", "asset_cash")

        cls._entry("2025-03-01", [(cls.acc_512, 400, 0), (cls.acc_1212, 0, 400)])
        cls._entry("2025-03-05", [(cls.acc_601, 1000, 0), (cls.acc_401, 0, 1000)])
        cls._entry("2025-03-06", [(cls.acc_401, 200, 0), (cls.acc_601, 0, 200)])
        cls._entry(
            "2025-03-10",
            [(cls.acc_602, 500, 0), (cls.acc_4426, 95, 0), (cls.acc_401, 0, 595)],
        )
        cls._entry(
            "2025-03-12",
            [(cls.acc_4111, 2380, 0), (cls.acc_707, 0, 2000), (cls.acc_4427, 0, 380)],
        )
        cls._entry("2025-03-20", [(cls.acc_711, 300, 0), (cls.acc_345, 0, 300)])
        # în afara perioadei - nu se închide
        cls._entry("2025-02-10", [(cls.acc_601, 50, 0), (cls.acc_401, 0, 50)])
        # nepostat - nu se închide
        cls._entry(
            "2025-03-15", [(cls.acc_601, 70, 0), (cls.acc_401, 0, 70)], post=False
        )

        closing = cls.env["l10n.ro.account.period.closing"]
        cls.exp_closing = closing.create(
            {
                "name": "Exp",
                "type": "expense",
                "journal_id": cls.misc_journal.id,
                "debit_account_id": cls.acc_1211.id,
                "credit_account_id": cls.acc_1212.id,
                "account_ids": [(6, 0, (cls.acc_601 | cls.acc_602).ids)],
            }
        )
        cls.inc_closing = closing.create(
            {
                "name": "Inc",
                "type": "income",
                "journal_id": cls.misc_journal.id,
                "debit_account_id": cls.acc_1211.id,
                "credit_account_id": cls.acc_1212.id,
                "account_ids": [(6, 0, (cls.acc_707 | cls.acc_711).ids)],
            }
        )
        cls.vat_closing = closing.create(
            {
                "name": "VAT",
                "type": "selected",
                "journal_id": cls.misc_journal.id,
                "debit_account_id": cls.acc_4424.id,
                "credit_account_id": cls.acc_4423.id,
                "account_ids": [(6, 0, (cls.acc_4426 | cls.acc_4427).ids)],
            }
        )

    @classmethod
    def _entry(cls, date, lines, post=True):
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": date,
                "journal_id": cls.misc_journal.id,
                "line_ids": [
                    (0, 0, {"name": "x", "account_id": a.id, "debit": d, "credit": c})
                    for a, d, c in lines
                ],
            }
        )
        if post:
            move.action_post()
        return move

    def _close(self, closing):
        wizard = self.env["l10n.ro.account.period.closing.wizard"].create(
            {
                "closing_id": closing.id,
                "date_from": self.date_from,
                "date_to": self.date_to,
            }
        )
        wizard.onchange_closing_id()
        wizard.do_close()
        self.assertEqual(len(closing.move_ids), 1)
        move = closing.move_ids
        self.assertEqual(move.state, "posted")
        self.assertTrue(move.l10n_ro_closing_move)
        self.assertEqual(move.date, self.date_to)
        self.assertEqual(move.journal_id, self.misc_journal)
        return sorted(
            (line.account_id.code, line.debit, line.credit, line.name)
            for line in move.line_ids
        )

    def test_close_expense(self):
        self.assertEqual(
            self._close(self.exp_closing),
            [
                ("121900", 1300.0, 0.0, "Closing Exp"),
                ("601900", 0.0, 800.0, "Closing Exp"),
                ("602900", 0.0, 500.0, "Closing Exp"),
            ],
        )

    def test_close_income_bypass_side(self):
        # 711 are bifat l10n_ro_close_check: sold debitor închis pe credit
        self.assertEqual(
            self._close(self.inc_closing),
            [
                ("121901", 0.0, 1700.0, "Closing Inc"),
                ("707900", 2000.0, 0.0, "Closing Inc"),
                ("711900", 0.0, 300.0, "Closing Inc"),
            ],
        )

    def test_close_income_close_result(self):
        self._close(self.exp_closing)
        self.inc_closing.close_result = True
        self.assertEqual(
            self._close(self.inc_closing),
            [
                ("121900", 400.0, 0.0, "Closing Inc 121900"),
                ("121901", 0.0, 400.0, "Closing Inc 121901"),
                ("121901", 0.0, 1700.0, "Closing Inc"),
                ("707900", 2000.0, 0.0, "Closing Inc"),
                ("711900", 0.0, 300.0, "Closing Inc"),
            ],
        )

    def test_close_vat(self):
        self.assertEqual(
            self._close(self.vat_closing),
            [
                ("442390", 0.0, 285.0, "Closing VAT"),
                ("442690", 0.0, 95.0, "Closing VAT"),
                ("442790", 380.0, 0.0, "Closing VAT"),
            ],
        )
