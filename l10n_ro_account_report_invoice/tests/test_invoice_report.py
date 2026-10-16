# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestInvoiceReport(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.partner_a.write({"nrc": "J40/1234/2020"})
        cls.bank = cls.env["res.partner.bank"].create(
            {
                "account_number": "RO49AAAA1B31007593840000",
                "bank_name": "Banca Test",
                "partner_id": cls.partner_a.id,
                "l10n_ro_print_report": True,
            }
        )

    def _render_invoice(self, invoice):
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", invoice.ids
        )
        return html.decode() if isinstance(html, bytes) else str(html)

    def test_invoice_report_partner_nrc_and_bank(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        self.assertTrue(invoice.is_l10n_ro_record)
        html = self._render_invoice(invoice)
        self.assertIn("J40/1234/2020", html)
        self.assertIn("Banca Test", html)
        # the IBAN is printed formatted, in groups of four
        self.assertIn("RO49 AAAA 1B31 0075 9384 0000", html)

    def test_invoice_report_bank_not_printed(self):
        self.bank.l10n_ro_print_report = False
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        html = self._render_invoice(invoice)
        self.assertIn("J40/1234/2020", html)
        self.assertNotIn("Banca Test", html)

    def test_invoice_report_no_signature_text(self):
        self.env.company.l10n_ro_no_signature_text = "Factura valabila fara semnatura"
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        html = self._render_invoice(invoice)
        self.assertIn("Factura valabila fara semnatura", html)

    def test_invoice_report_non_romanian(self):
        self.env.company.l10n_ro_accounting = False
        self.env.company.l10n_ro_no_signature_text = "Factura valabila fara semnatura"
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        self.assertFalse(invoice.is_l10n_ro_record)
        html = self._render_invoice(invoice)
        self.assertNotIn("J40/1234/2020", html)
        self.assertNotIn("Factura valabila fara semnatura", html)
