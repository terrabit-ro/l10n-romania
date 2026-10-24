# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re
from datetime import datetime

import pytz

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_download_einvoices_days = fields.Integer(
        string="Maximum number of days to download e-invoices.", default=60
    )
    l10n_ro_refresh_message_days = fields.Integer(
        string="Maximum number of days to refresh e-invoice messages.", default=60
    )
    l10n_ro_spv_last_sync = fields.Datetime(
        string="Last SPV message sync", readonly=True, copy=False
    )
    l10n_ro_spv_last_sync_error = fields.Text(
        string="Last SPV message sync error", readonly=True, copy=False
    )

    def l10n_ro_download_zip_message_spv(self, limit=5):
        # method to be used in cron job to auto download e-invoices from ANAF
        domain = [("l10n_ro_edi_access_token", "!=", False)]
        ro_companies = self or self.env["res.company"].sudo().search(domain)

        need_retrigger = False
        for company in ro_companies:
            # Resetăm la draft mesajele căzute în eroare în zilele trecute, ca să
            # fie reîncercate (cota ANAF de 10 descărcări/zi/mesaj se reînnoiește).
            error_messages_from_past = company.env["l10n.ro.message.spv"].search(
                [
                    ("company_id", "=", company.id),
                    ("attachment_id", "=", False),
                    ("state", "=", "error"),
                    ("last_download_date", "<", fields.Date.today()),
                ]
            )
            if error_messages_from_past:
                error_messages_from_past.write(
                    {"state": "draft", "download_attempts": 0}
                )

            # Procesăm mesajele în starea draft (state="error" rămâne exclus,
            # deci un mesaj epuizat în ziua curentă nu mai e reselectat).
            domain = [
                ("company_id", "=", company.id),
                ("attachment_id", "=", False),
                ("state", "=", "draft"),
            ]
            messages = company.env["l10n.ro.message.spv"].search(
                domain, limit=limit + 1
            )
            if len(messages) > limit:
                need_retrigger = True

            # Procesăm fiecare mesaj individual ca o eroare la unul să nu
            # blocheze descărcarea celorlalte.
            for message in messages[:limit]:
                try:
                    message.download_from_spv()
                except Exception as e:  # pragma: no cover - protecție runtime
                    _logger.exception(
                        "Eroare la descărcarea ZIP pentru mesajul %s (compania %s)",
                        message.name,
                        company.id,
                    )
                    today = fields.Date.today()
                    attempts = message.download_attempts + 1
                    if message.last_download_date != today:
                        attempts = 1
                    message.sudo().write(
                        {
                            "state": "error",
                            "error": str(e),
                            "download_attempts": attempts,
                            "last_download_date": today,
                        }
                    )

        if need_retrigger:
            self.env.ref(
                "l10n_ro_message_spv.ir_cron_download_zip_message_spv"
            )._trigger()

    def l10n_ro_download_message_spv(self):
        # method to be used in cron job to auto download e-invoices from ANAF
        domain = [("l10n_ro_edi_access_token", "!=", False)]
        ro_companies = self or self.env["res.company"].sudo().search(domain)
        return ro_companies._l10n_ro_download_message_spv()

    def _l10n_ro_get_partner_from_cif(self, cif):
        self.ensure_one()
        company_id = self.id

        # ANAF sends the CIF sometimes with and sometimes without the "RO"
        # prefix, while the partner stored in Odoo may hold the other variant.
        # Search both spellings, otherwise the lookup fails and a duplicate
        # "Unknown" partner is created for an already known company.
        cif_clean = re.sub(r"^RO", "", (cif or "").strip().upper())
        cif_variants = [cif_clean, "RO" + cif_clean]
        # Multi-company: only partners of this company (or shared ones) may
        # be matched, so that data does not leak between companies.
        company_domain = [
            "|",
            ("company_id", "=", company_id),
            ("company_id", "=", False),
        ]

        def _search(extra_domain):
            for variant in cif_variants:
                result = self.env["res.partner"].search(
                    [("vat", "=ilike", variant)] + extra_domain, limit=1
                )
                if result:
                    return result
            return self.env["res.partner"]

        partner = _search([("is_company", "=", True), ("company_id", "=", company_id)])
        if not partner:
            partner = _search([("is_company", "=", True)] + company_domain)
        if not partner:
            partner = _search(company_domain)
        if not partner:
            partner = self.env["res.partner"].create(
                {
                    "name": "Unknown",
                    "company_id": company_id,
                    "country_id": self.env.ref("base.ro").id,
                    "is_company": True,
                }
            )
            partner.write({"vat": cif_clean})
        return partner

    def _l10n_ro_download_message_spv(self, no_days=0, raise_error=False):
        # Fiecare companie rulează într-un savepoint: o eroare la una (token
        # expirat, limită ANAF) nu oprește celelalte și nu lasă în urmă
        # ștergeri sau creări parțiale. O eroare nouă ajunge ca notificare la
        # contabilii-șefi și administratorii companiei; aceeași eroare nu se
        # renotifică la fiecare rulare. Din butonul manual (raise_error=True) eroarea
        # ajunge direct la utilizator.
        for company in self:
            if not raise_error and company.partner_id.lang:
                company = company.with_context(lang=company.partner_id.lang)
            try:
                with self.env.cr.savepoint():
                    company._l10n_ro_download_company_message_spv(no_days)
            except Exception as e:
                if raise_error:
                    raise
                if isinstance(e, UserError):
                    _logger.warning(
                        "SPV message sync failed for company %s: %s",
                        company.id,
                        e,
                    )
                else:
                    _logger.exception(
                        "SPV message sync failed for company %s", company.id
                    )
                error = str(e)
                if company.l10n_ro_spv_last_sync_error != error:
                    company._l10n_ro_notify_spv_sync_error(error)
                company.sudo().write({"l10n_ro_spv_last_sync_error": error})
            else:
                company.sudo().write(
                    {
                        "l10n_ro_spv_last_sync": fields.Datetime.now(),
                        "l10n_ro_spv_last_sync_error": False,
                    }
                )
        return True

    def _l10n_ro_notify_spv_sync_error(self, error):
        """Trimite eroarea de sincronizare SPV (în Discuss sau pe email, după
        preferința fiecăruia) contabililor-șefi ai companiei și administratorilor
        de setări, care pot regenera tokenul ANAF. Notificarea nu e legată de
        o înregistrare: în Discuss se deschide într-un dialog cu textul complet,
        nu pe fișa partenerului companiei, unde nu apare."""
        self.ensure_one()
        groups = self.env.ref("account.group_account_manager") | self.env.ref(
            "base.group_system"
        )
        users = (
            self.env["res.users"]
            .sudo()
            .search(
                [
                    ("group_ids", "in", groups.ids),
                    ("company_ids", "in", self.id),
                    ("share", "=", False),
                ]
            )
        )
        if not users:
            return
        self.env["mail.thread"].sudo().message_notify(
            partner_ids=users.partner_id.ids,
            subject=self.env._(
                "SPV message sync failed: %(company)s", company=self.name
            ),
            body=self.env._(
                "%(error)s Messages older than 60 days can no longer be listed"
                " from ANAF, so check the ANAF token in the e-Factura settings.",
                error=error,
            ),
            author_id=self.env.ref("base.partner_root").id,
        )

    def _l10n_ro_download_company_message_spv(self, no_days=0):
        self.ensure_one()
        pattern_in = r"cif_emitent=(\d+)"
        pattern_out = r"cif_beneficiar=(\d+)"

        romania_tz = pytz.timezone("Europe/Bucharest")
        obj_message_spv = self.env["l10n.ro.message.spv"]
        obj_edi_document = self.env["l10n_ro_edi.document"]

        for company in self:
            # stergere erorile vechi
            domain = [("company_id", "=", company.id), ("message_type", "=", "error")]
            error_messages = obj_message_spv.with_company(company).search(domain)
            error_messages.unlink()
            days = no_days or int(company.l10n_ro_download_einvoices_days or 1)
            # company_messages = company._l10n_ro_get_anaf_efactura_messages()
            company_messages = obj_edi_document._request_ciusro_download_messages_spv(
                company, no_days=days
            )
            message_spv_obj = obj_message_spv.with_company(company).sudo()

            for message in company_messages:
                domain = [("name", "=", message["id"])]
                if not message_spv_obj.search(domain, limit=1):
                    date = datetime.strptime(message.get("data_creare"), "%Y%m%d%H%M")
                    localized_date = romania_tz.localize(date)
                    # Convertim data și ora la GMT
                    gmt_tz = pytz.timezone("GMT")
                    gmt_date = localized_date.astimezone(gmt_tz)
                    partner = self.env["res.partner"]
                    cif = message["cif"]
                    message_type = False
                    if message["tip"] == "FACTURA PRIMITA":
                        message_type = "in_invoice"
                        match = re.search(pattern_in, message["detalii"])
                        if match:
                            cif = match.group(1)
                            partner = company._l10n_ro_get_partner_from_cif(cif)

                    elif message["tip"] == "FACTURA TRIMISA":
                        message_type = "out_invoice"
                        match = re.search(pattern_out, message["detalii"])
                        if match:
                            cif = match.group(1)
                            partner = company._l10n_ro_get_partner_from_cif(cif)
                    elif message["tip"] == "ERORI FACTURA":
                        message_type = "error"
                    elif "MESAJ" in message["tip"]:
                        message_type = "message"
                    else:
                        _logger.error("Unknown message type: %s", message["tip"])

                    message_spv_obj.create(
                        {
                            "name": message["id"],
                            "cif": cif,
                            "message_type": message_type,
                            "date": gmt_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "details": message["detalii"],
                            "request_id": message["id_solicitare"],
                            "company_id": company.id,
                            "partner_id": partner.id,
                            "state": "draft",
                        }
                    )

        return True
