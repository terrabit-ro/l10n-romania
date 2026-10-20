# © 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
#
# Capturi de ecran pentru fișa „Mesaje SPV și facturi primite prin e-Factura" —
# generate în timpul testelor, în limba RO, pe planul de conturi RO.
#
# Seedează registrul de mesaje SPV fără apeluri la ANAF: o factură primită descărcată,
# una din care s-a creat factura de furnizor, una cu sumă diferită de factura legată,
# plus mesaje de vânzare, eroare și informare. La final simulează o listare refuzată de
# ANAF (token neautorizat) și pozează notificarea primită în Inbox.
#
# Rulare:
#   ./odoo/odoo-bin -c odoo.conf -d <db> \
#       -i l10n_ro_message_spv,l10n_ro_doc_screenshots \
#       --test-tags=fise_screenshots --stop-after-init
import io
import unittest
import zipfile
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tools.misc import file_path

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

try:
    from odoo.addons.l10n_ro_doc_screenshots.tests.screenshot_case import (
        ScreenshotCase,
    )
except ImportError:
    ScreenshotCase = None


MSG_ACTION = "l10n_ro_message_spv.action_l10n_ro_message_spv"
REQUEST = "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request"
SCROLL_TO = (
    "(() => {"
    "  const el = document.querySelector(\"div[name='%s']\");"
    "  if (el) el.scrollIntoView({behavior:'instant', block:'center'});"
    "})()"
)


@tagged("-at_install", "post_install", "fise_screenshots")
class TestMessageSpvScreenshots(AccountTestInvoicingCommon, ScreenshotCase or object):
    screenshots_module = "l10n_ro_message_spv"

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        if ScreenshotCase is None:
            raise unittest.SkipTest("l10n_ro_doc_screenshots indisponibil")
        super().setUpClass()
        cls.prepare_ro_company(name="Demo SPV SRL")
        env = cls.env
        company = env.company
        env.ref("base.user_admin").write(
            {
                "company_ids": [(4, company.id)],
                "company_id": company.id,
                # notificările ajung în Inbox, nu doar pe email
                "notification_type": "inbox",
            }
        )
        company.write(
            {
                "l10n_ro_edi_client_id": "client-id-demo",
                "l10n_ro_edi_client_secret": "client-secret-demo",
                "l10n_ro_edi_access_token": "token-demo",
                "l10n_ro_edi_test_env": False,
                "l10n_ro_spv_last_sync": fields.Datetime.now() - relativedelta(hours=2),
                "l10n_ro_spv_last_sync_error": False,
            }
        )
        # notificarea se scrie în limba companiei
        company.partner_id.lang = "ro_RO"
        # o singură companie pe ecran: fără coloana Companie în liste
        admin = env.ref("base.user_admin")
        admin.write({"company_ids": [(6, 0, company.ids)]})
        admin.group_ids = [(3, env.ref("base.group_multi_company").id)]

        partner_obj = env["res.partner"]
        ro = env.ref("base.ro").id
        supplier = partner_obj.create(
            {
                "name": "Romchim Protect SRL",
                "vat": "RO10167619",
                "is_company": True,
                "country_id": ro,
            }
        )
        supplier_2 = partner_obj.create(
            {
                "name": "Birotica Expert SRL",
                "vat": "RO18547290",
                "is_company": True,
                "country_id": ro,
            }
        )
        customer = partner_obj.create(
            {
                "name": "Client Retail SRL",
                "vat": "RO24398818",
                "is_company": True,
                "country_id": ro,
            }
        )

        now = fields.Datetime.now()
        today = now.date()
        company_cif = company.vat.replace("RO", "")
        msg_obj = env["l10n.ro.message.spv"]

        def message(name, request_id, message_type, partner, hours, **extra):
            cif = (partner.vat or "").replace("RO", "") if partner else False
            if message_type == "out_invoice":
                details = (
                    f"Factura cu id_incarcare={request_id} emisa de "
                    f"cif_emitent={company_cif} pentru cif_beneficiar={cif}"
                )
            elif partner:
                details = (
                    f"Factura cu id_incarcare={request_id} emisa de "
                    f"cif_emitent={cif} pentru cif_beneficiar={company_cif}"
                )
            else:
                details = "Mesaj de informare ANAF"
            values = {
                "name": name,
                "request_id": request_id,
                "message_type": message_type,
                "partner_id": partner.id if partner else False,
                "cif": cif,
                "date": now - relativedelta(hours=hours),
                "company_id": company.id,
                "details": details,
            }
            values.update(extra)
            return msg_obj.create(values)

        def attach_zip(msg, zip_raw):
            attachment = (
                env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": f"{msg.request_id}.zip",
                        "raw": zip_raw,
                        "mimetype": "application/zip",
                        "company_id": company.id,
                    }
                )
            )
            msg.write(
                {
                    "attachment_id": attachment.id,
                    "file_name": attachment.name,
                    "state": "downloaded",
                }
            )
            msg.get_xml_fom_zip()

        # Factura primită din care se creează factura de furnizor (Pasul 4)
        msg_invoice = message("3006372781", "5004111924", "in_invoice", supplier, 30)
        attach_zip(
            msg_invoice,
            cls._demo_invoice_zip(today - relativedelta(days=2), "RCHIM/055087"),
        )
        msg_invoice.create_invoice()
        cls.bill = msg_invoice.invoice_id

        # Factura primită descărcată, încă fără factură (Pasul 3)
        cls.msg_downloaded = message(
            "3006372790", "5004111937", "in_invoice", supplier, 5
        )
        attach_zip(
            cls.msg_downloaded,
            cls._demo_invoice_zip(today, "RCHIM/055102", qty=12.0, price=150.0),
        )

        # Factură primită legată de o factură cu alt total (sumă cu roșu, Pasul 5)
        bill_manual = env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": supplier_2.id,
                "ref": "BEX 4471",
                "invoice_date": today - relativedelta(days=3),
                "invoice_line_ids": [
                    (0, 0, {"name": "Consumabile birou", "price_unit": 400.0})
                ],
            }
        )
        message(
            "3006372755",
            "5004111890",
            "in_invoice",
            supplier_2,
            70,
            ref="BEX 4471",
            invoice_date=today - relativedelta(days=3),
            amount=496.0,
            invoice_amount=bill_manual.amount_total,
            invoice_id=bill_manual.id,
            state="invoice",
        )
        # Factură primită, listată azi, nedescărcată încă
        message("3006372801", "5004111950", "in_invoice", supplier_2, 1)

        # Factură trimisă și confirmată, eroare ANAF, mesaj de informare
        sale_tax = env["account.tax"].search(
            [
                ("type_tax_use", "=", "sale"),
                ("company_id", "=", company.id),
                ("amount", "=", 21.0),
            ],
            limit=1,
        )
        out_invoice = env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": customer.id,
                "invoice_date": today - relativedelta(days=2),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Servicii mentenanță",
                            "price_unit": 1475.21,
                            "tax_ids": [(6, 0, sale_tax.ids)],
                        },
                    )
                ],
            }
        )
        out_invoice.action_post()
        message(
            "3006372744",
            "5004111872",
            "out_invoice",
            customer,
            50,
            ref=out_invoice.name,
            invoice_date=out_invoice.invoice_date,
            amount=out_invoice.amount_total,
            invoice_amount=out_invoice.amount_total,
            invoice_id=out_invoice.id,
            state="done",
        )
        message(
            "3006372768",
            "5004111905",
            "error",
            False,
            26,
            ref="FV 2026/0421",
            error="E: validarea XML a eșuat: lipsește codul fiscal al cumpărătorului",
            state="error",
        )
        message("3006372779", "5004111919", "message", False, 40, state="downloaded")

        cls.action_grouped = env["ir.actions.act_window"].create(
            {
                "name": "Mesaje SPV",
                "res_model": "l10n.ro.message.spv",
                "view_mode": "list,form",
                "context": "{'search_default_invoices': 1, "
                "'search_default_group_state': 1}",
            }
        )
        env.flush_all()

    @classmethod
    def _demo_invoice_zip(cls, issue_date, ref, qty=4.0, price=25.0):
        """Arhiva de test, cu o factură plauzibilă pentru capturi: TVA 21%,
        scadență la 30 de zile (fixture-ul original are o linie „Test” la 19%,
        din 2023)."""
        base = round(qty * price, 2)
        vat = round(base * 0.21, 2)
        with zipfile.ZipFile(
            file_path("l10n_ro_message_spv/tests/invoice.zip")
        ) as source:
            files = {name: source.read(name) for name in source.namelist()}
        xml = files["5004111924.xml"].decode("utf-8")
        for old, new in (
            ("RCHIM/054914", ref),
            ("2023-11-06", issue_date.isoformat()),
            ("2023-12-06", (issue_date + relativedelta(days=30)).isoformat()),
            ("<cbc:Percent>19.0</cbc:Percent>", "<cbc:Percent>21.0</cbc:Percent>"),
            ('currencyID="RON">3.80<', f'currencyID="RON">{vat:.2f}<'),
            ('currencyID="RON">20.00<', f'currencyID="RON">{base:.2f}<'),
            ('currencyID="RON">23.80<', f'currencyID="RON">{base + vat:.2f}<'),
            (
                'unitCode="C62">2.0</cbc:InvoicedQuantity>',
                f'unitCode="C62">{qty}</cbc:InvoicedQuantity>',
            ),
            ('currencyID="RON">10.000<', f'currencyID="RON">{price:.3f}<'),
            (
                'unitCode="C62">2.0</cbc:BaseQuantity>',
                'unitCode="C62">1.0</cbc:BaseQuantity>',
            ),
            (
                "<cbc:Description>Test</cbc:Description>",
                "<cbc:Description>Bidon 5 l, concentrat</cbc:Description>",
            ),
            (
                "<cbc:Name>Test</cbc:Name>",
                "<cbc:Name>Soluție dezinfectantă 5 l</cbc:Name>",
            ),
        ):
            assert old in xml, old
            xml = xml.replace(old, new)
        files["5004111924.xml"] = xml.encode("utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as target:
            for name, content in files.items():
                target.writestr(name, content)
        return buffer.getvalue()

    def _settings_shot(self, name, field):
        return {
            "url": "action=account.action_account_config",
            "name": name,
            "wait": ".o_form_view",
            "timeout": 40000,
            "eval": SCROLL_TO % field,
            "eval_wait": 1500,
            "highlight": [f"div[name='{field}']"],
            "settle": 2000,
            "full": False,
        }

    def test_capture_fise(self):
        # Pasul 6: ANAF refuză listarea (token neautorizat); contabilul-șef
        # (admin, cu drept de administrator contabil) primește notificarea.
        # textul pe care îl dă make_efactura_request cu interfața în română
        error = "Token de acces neautorizat."
        with patch(REQUEST, return_value={"error": error}):
            self.env.company._l10n_ro_download_message_spv()
        self.env.flush_all()
        admin_partner = self.env.ref("base.user_admin").partner_id
        self.assertTrue(
            self.env["mail.notification"].search(
                [
                    ("res_partner_id", "=", admin_partner.id),
                    ("notification_type", "=", "inbox"),
                    ("mail_message_id.model", "=", False),
                ]
            ),
            "Notificarea de eroare SPV nu a ajuns în Inbox-ul administratorului.",
        )

        msg_action = self.env.ref(MSG_ACTION).id
        bill_action = self.env.ref("account.action_move_in_invoice_type").id
        self.capture_screenshots(
            [
                # 1. Setări E-Factura: zilele de descărcare și ultima sincronizare
                self._settings_shot("01_setari_spv.png", "l10n_ro_spv_last_sync"),
                # 2. Lista Mesaje SPV
                {
                    "url": f"action={msg_action}",
                    "name": "02_lista_mesaje_spv.png",
                    "wait": ".o_list_view",
                    "highlight": ["button[name='refresh']"],
                    "settle": 2000,
                },
                # 3. Mesajul unei facturi primite, descărcat
                {
                    "url": (
                        f"action={msg_action}&id={self.msg_downloaded.id}"
                        "&model=l10n.ro.message.spv&view_type=form"
                    ),
                    "name": "03_mesaj_factura_primita.png",
                    "wait": ".o_form_view",
                    "highlight": [
                        "button[name='create_invoice']",
                        "button[name='action_download_xml']",
                        "button[name='action_download_anaf_pdf']",
                    ],
                    "settle": 2000,
                },
                # 4. Factura de furnizor creată în Ciornă din XML
                {
                    "url": (
                        f"action={bill_action}&id={self.bill.id}"
                        "&model=account.move&view_type=form"
                    ),
                    "name": "04_factura_furnizor_creata.png",
                    "wait": ".o_form_view",
                    "highlight": [
                        "div[name='partner_id']",
                        "div[name='ref']",
                    ],
                    "settle": 2500,
                    "full": True,
                },
                # 5. Facturile primite, grupate pe stare
                {
                    "url": f"action={self.action_grouped.id}",
                    "name": "05_mesaje_grupate_stare.png",
                    "wait": ".o_list_view",
                    "eval": (
                        "document.querySelectorAll('.o_group_header')"
                        ".forEach(h => h.click())"
                    ),
                    "eval_wait": 2000,
                    "settle": 2000,
                },
                # 6. Notificarea de eroare din Inbox
                {
                    "url": "action=mail.action_discuss&active_id=mail.box_inbox",
                    "name": "06_notificare_eroare_sincronizare.png",
                    # în 20.0 Discuss arată lista notificărilor; click pe ea
                    # deschide mesajul fără înregistrare legată într-un dialog
                    "wait": ".o-mail-NotificationItem",
                    "click_btn": ".o-mail-NotificationItem",
                    "wait_after": ".modal .o-mail-Message",
                    "highlight": [".modal .o-mail-Message"],
                    # avertismentul de websocket al serverului de test și canalele
                    # demo din bara laterală Discuss nu țin de flux
                    "eval": (
                        "(() => {"
                        "  const st = document.createElement('style');"
                        "  st.textContent = 'body, .o_web_client"
                        " { border: 0 !important; outline: 0 !important; }"
                        " .o-mail-DiscussSidebar { display: none !important; }';"
                        "  document.head.appendChild(st);"
                        "  document.querySelectorAll('body *').forEach(e => {"
                        "    if (!e.children.length &&"
                        "        e.textContent.includes('Conexiunea în timp real'))"
                        "      (e.closest('.o_notification, .position-fixed,"
                        " .position-absolute') || e).remove();"
                        "  });"
                        "})()"
                    ),
                    "eval_wait": 500,
                    "settle": 2500,
                },
            ],
            viewport=(1920, 950),
            hide_systray=True,
        )
