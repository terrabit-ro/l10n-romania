# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests import tagged

from ..models.message_spv import _normalize_cif
from .common import TestMessageSPV


@tagged("post_install", "-at_install")
class TestMessageSPVPartner(TestMessageSPV):
    """Legătura dintre mesajul SPV, partener și factură."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner_obj = cls.env["res.partner"]
        cls.supplier_a = partner_obj.create(
            {"name": "Furnizor A", "vat": "RO1001", "is_company": True}
        )
        cls.supplier_b = partner_obj.create(
            {"name": "Furnizor B", "vat": "RO1002", "is_company": True}
        )
        cls.supplier_c = partner_obj.create(
            {"name": "Furnizor C", "vat": "RO1003", "is_company": True}
        )
        cls.customer = partner_obj.create(
            {"name": "Client", "vat": "RO2001", "is_company": True}
        )

    def _create_message(self, name, cif, **extra):
        values = {
            "name": name,
            "request_id": f"REQ_{name}",
            "cif": cif,
            "message_type": "in_invoice",
            "company_id": self.env.company.id,
        }
        values.update(extra)
        return self.env["l10n.ro.message.spv"].create(values)

    def _create_invoice(self, partner, move_type="in_invoice", **extra):
        values = {
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [
                (0, 0, {"name": "test", "quantity": 1, "price_unit": 100})
            ],
        }
        values.update(extra)
        return self.env["account.move"].create(values)

    def test_normalize_cif(self):
        """Aceeași firmă, oricum ar fi scris CIF-ul."""
        for value in ("RO1001", "ro 1001", "1001", " RO-1001 ", "001001"):
            self.assertEqual(_normalize_cif(value), "1001", value)
        self.assertEqual(_normalize_cif(False), "")
        self.assertEqual(_normalize_cif("0000000000000"), "")
        self.assertNotEqual(_normalize_cif("RO1001"), _normalize_cif("RO1002"))

    def test_undownloaded_messages_not_linked_to_draft_bill(self):
        """„Get Invoice" pe un lot: mesajele încă nedescărcate (fără
        referință) nu se leagă de factura ciornă a altui furnizor din lot.

        Înainte, False (referința lipsă) se compara cu False (numărul
        facturii ciornă) și toate mesajele nedescărcate primeau factura,
        partenerul și suma primului furnizor."""
        bill = self._create_invoice(
            self.supplier_a, ref="FAR1", l10n_ro_edi_download="MSG_A"
        )
        self.assertEqual(bill.state, "draft")
        message_a = self._create_message(
            "MSG_A", "1001", ref="FAR1", partner_id=self.supplier_a.id
        )
        message_b = self._create_message("MSG_B", "1002", partner_id=self.supplier_b.id)
        message_c = self._create_message("MSG_C", "1003", partner_id=self.supplier_c.id)

        (message_a | message_b | message_c).get_invoice_from_move()

        self.assertEqual(message_a.invoice_id, bill)
        self.assertEqual(message_a.state, "invoice")
        for message, supplier in (
            (message_b, self.supplier_b),
            (message_c, self.supplier_c),
        ):
            self.assertFalse(message.invoice_id)
            self.assertEqual(message.partner_id, supplier)
            self.assertEqual(message.state, "draft")
            self.assertFalse(message.invoice_amount)
        self.assertEqual(bill.l10n_ro_message_spv_ids, message_a)

    def test_empty_request_id_matches_nothing(self):
        """Un mesaj fără id de încărcare nu se leagă de o factură care nu are
        nici ea id de tranzacție."""
        bill = self._create_invoice(
            self.supplier_a, ref="FAR2", l10n_ro_edi_download="MSG_D"
        )
        message_d = self._create_message(
            "MSG_D", "1001", ref="FAR2", partner_id=self.supplier_a.id
        )
        message_e = self._create_message(
            "MSG_E",
            "1002",
            ref="ALT1",
            request_id=False,
            partner_id=self.supplier_b.id,
        )

        (message_d | message_e).get_invoice_from_move()

        self.assertEqual(message_d.invoice_id, bill)
        self.assertFalse(message_e.invoice_id)

    def test_same_number_other_supplier_not_linked(self):
        """Același număr de document la doi furnizori: fiecare mesaj își ia
        doar factura furnizorului cu CIF-ul lui."""
        bill_b = self._create_invoice(
            self.supplier_b, ref="NR100", l10n_ro_edi_download="MSG_B2"
        )
        message_a = self._create_message(
            "MSG_A2", "1001", ref="NR100", partner_id=self.supplier_a.id
        )
        message_b = self._create_message(
            "MSG_B2", "1002", ref="NR100", partner_id=self.supplier_b.id
        )

        (message_a | message_b).get_invoice_from_move()

        self.assertEqual(message_b.invoice_id, bill_b)
        self.assertFalse(message_a.invoice_id)
        self.assertEqual(message_a.partner_id, self.supplier_a)

    def test_same_number_same_cif_other_partner_record_linked(self):
        """Aceeași firmă cu două fișe de partener (CIF scris diferit):
        potrivirea după număr merge, pentru că se compară CIF-ul."""
        duplicate = self.env["res.partner"].create(
            {"name": "Furnizor A (dublură)", "vat": "1001", "is_company": True}
        )
        bill = self._create_invoice(
            duplicate, ref="DUP1", l10n_ro_edi_download="MSG_DUP_OLD"
        )
        old_message = self._create_message(
            "MSG_DUP_OLD", "1001", ref="DUP1", partner_id=self.supplier_a.id
        )
        new_message = self._create_message(
            "MSG_DUP_NEW", "1001", ref="DUP1", partner_id=self.supplier_a.id
        )

        (old_message | new_message).get_invoice_from_move()

        self.assertEqual(old_message.invoice_id, bill)
        self.assertEqual(new_message.invoice_id, bill)

    def test_received_message_not_linked_to_customer_invoice(self):
        """Numărul unei facturi primite coincide cu numărul unei facturi a
        noastre de client: mesajul primit nu se leagă de ea, cel trimis da."""
        invoice = self._create_invoice(self.customer, move_type="out_invoice")
        invoice.action_post()
        received = self._create_message(
            "MSG_IN", "1001", ref=invoice.name, partner_id=self.supplier_a.id
        )
        sent_other_customer = self._create_message(
            "MSG_OUT_OTHER", "2002", ref=invoice.name, message_type="out_invoice"
        )
        sent = self._create_message(
            "MSG_OUT", "2001", ref=invoice.name, message_type="out_invoice"
        )

        (received | sent_other_customer | sent).get_invoice_from_move()

        self.assertFalse(received.invoice_id)
        self.assertFalse(sent_other_customer.invoice_id)
        self.assertEqual(sent.invoice_id, invoice)
        self.assertEqual(sent.partner_id, self.customer)
        self.assertEqual(sent.state, "done")
