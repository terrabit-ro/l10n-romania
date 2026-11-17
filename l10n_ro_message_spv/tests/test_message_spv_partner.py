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

    # ------------------------------------------------------------------
    # Conflict de CIF între mesaj, partener și factură
    # ------------------------------------------------------------------

    def test_cif_conflict_shown_on_linked_invoice(self):
        """Factura găsită după identificatorul ANAF aparține altui partener:
        legătura rămâne, conflictul este afișat, mesajul nu preia partenerul
        străin, iar factura nu este modificată."""
        bill = self._create_invoice(
            self.supplier_b, ref="X1", l10n_ro_edi_download="MSG_K"
        )
        message = self._create_message(
            "MSG_K", "1001", ref="X1", partner_id=self.supplier_a.id
        )
        self.assertFalse(message.cif_conflict)

        message.get_invoice_from_move()

        self.assertEqual(message.invoice_id, bill)
        self.assertTrue(message.cif_conflict)
        self.assertEqual(message.partner_id, self.supplier_a)
        self.assertEqual(bill.partner_id, self.supplier_b)

    def test_partner_follows_invoice_with_same_cif(self):
        """Factura este pe altă fișă a aceleiași firme: mesajul preia fișa
        de pe factură, fără conflict."""
        duplicate = self.env["res.partner"].create(
            {"name": "Furnizor A (dublură)", "vat": "1001", "is_company": True}
        )
        bill = self._create_invoice(duplicate, ref="X2", l10n_ro_edi_download="MSG_L")
        message = self._create_message(
            "MSG_L", "1001", ref="X2", partner_id=self.supplier_a.id
        )

        message.get_invoice_from_move()

        self.assertEqual(message.invoice_id, bill)
        self.assertEqual(message.partner_id, duplicate)
        self.assertFalse(message.cif_conflict)

    def test_stale_partner_replaced_by_cif(self):
        """Mesaj fără factură, rămas cu partenerul altui CIF: partenerul se
        reface după CIF-ul primit de la ANAF."""
        message = self._create_message("MSG_S", "1002", partner_id=self.supplier_a.id)
        self.assertTrue(message.cif_conflict)

        message.get_partner()

        self.assertEqual(message.partner_id, self.supplier_b)
        self.assertFalse(message.cif_conflict)

        # CIF necunoscut în Odoo: partenerul străin se scoate și nu se
        # creează altul în loc.
        unknown = self._create_message("MSG_S2", "9999", partner_id=self.supplier_a.id)
        partner_count = self.env["res.partner"].search_count([])
        unknown.get_partner()
        self.assertFalse(unknown.partner_id)
        self.assertFalse(unknown.cif_conflict)
        self.assertEqual(self.env["res.partner"].search_count([]), partner_count)

    def test_no_conflict_without_comparable_cif(self):
        """Fără două CIF-uri de comparat nu există conflict și nu se schimbă
        nimic: partener fără CIF, mesaj fără CIF, mesaj de alt tip."""
        no_vat = self.env["res.partner"].create(
            {"name": "Fără CIF", "is_company": True}
        )
        messages = (
            self._create_message("MSG_N1", "1001", partner_id=no_vat.id)
            | self._create_message("MSG_N2", False, partner_id=self.supplier_a.id)
            | self._create_message(
                "MSG_N3",
                "1002",
                partner_id=self.supplier_a.id,
                message_type="message",
            )
        )
        partners = messages.mapped("partner_id")

        messages.get_partner()

        self.assertFalse(any(messages.mapped("cif_conflict")))
        self.assertEqual(messages.mapped("partner_id"), partners)
        self.assertEqual(messages[0].partner_id, no_vat)

    def test_onchange_invoice_warns_on_cif_conflict(self):
        """Legarea manuală a unei facturi cu alt CIF: avertizare, iar mesajul
        nu preia partenerul facturii."""
        bill_b = self._create_invoice(self.supplier_b)
        bill_a = self._create_invoice(self.supplier_a)
        message = self._create_message("MSG_O", "1001", partner_id=self.supplier_a.id)

        message.invoice_id = bill_b
        result = message._onchange_invoice_id()

        self.assertIn("1002", result["warning"]["message"])
        self.assertEqual(message.partner_id, self.supplier_a)
        self.assertEqual(message.invoice_amount, bill_b.amount_total)
        self.assertTrue(message.cif_conflict)

        message.invoice_id = bill_a
        self.assertFalse(message._onchange_invoice_id())
        self.assertEqual(message.partner_id, self.supplier_a)
        self.assertFalse(message.cif_conflict)
