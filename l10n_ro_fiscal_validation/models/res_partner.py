# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import time

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

CEDILLATRANS = bytes.maketrans(
    "\u015f\u0163\u015e\u0162".encode(),
    "\u0219\u021b\u0218\u021a".encode(),
)

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MSIE 7.01; Windows NT 5.0)",
    "Content-Type": "application/json;",
}

ANAF_BULK_URL = "https://webservicesp.anaf.ro/AsynchWebService/api/v/ws/tva"
ANAF_CORR = "https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva?id=%s"


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def update_l10n_ro_vat_subjected(self):  # noqa C901
        ir_config = self.env["ir.config_parameter"].sudo()
        get_str = ir_config.get_str
        anaf_url = get_str("l10n_ro_fiscal_validation.anaf_bulk_url", ANAF_BULK_URL)
        anaf_api_key_header_tag = get_str(
            "l10n_ro_partner_create_by_vat.anaf_api_key_header_tag", "x-api-key"
        )
        anaf_api_key = get_str("l10n_ro_partner_create_by_vat.anaf_api_key", "")
        if anaf_api_key:
            headers.update({anaf_api_key_header_tag: anaf_api_key})
        anaf_corr = get_str("l10n_ro_fiscal_validation.anaf_corr", ANAF_CORR)
        anaf_dict = []
        check_date = fields.Date.to_string(fields.Date.today())
        # Build list of vat numbers to be checked on ANAF
        for partner in self:
            anaf_dict.append(partner.l10n_ro_vat_number)
        chunk = []
        chunks = []
        # Process 500 vat numbers once
        max_no = ir_config.get_int("l10n_ro_fiscal_validation.anaf_bulk_number", 499)
        for position in range(0, len(anaf_dict), max_no):
            chunk = anaf_dict[position : position + max_no]
            chunks.append(chunk)
        for chunk in chunks:
            anaf_ask = []
            for item in chunk:
                if item:
                    anaf_ask.append({"cui": int(item), "data": check_date})
            try:
                res = requests.post(
                    anaf_url, json=anaf_ask, headers=headers, timeout=30
                )
                if res.status_code == 200:
                    result = {}
                    try:
                        result = res.json()
                    except Exception:
                        _logger.warning(f"ANAF sync not working: {res.content}")

                    if result.get("correlationId"):
                        time.sleep(3)
                        resp = False
                        try:
                            resp = requests.get(
                                anaf_corr % result["correlationId"],
                                headers=headers,
                                timeout=30,
                            )
                        except Exception as e:
                            _logger.warning(f"ANAF sync not working: {e}")
                        if resp and resp.status_code == 200:
                            result = resp.json()

                    for result_partner in result.get("found", []) + result.get(
                        "notFound", []
                    ):
                        vat = result_partner.get("date_generale").get("cui")
                        if vat:
                            partners = self.search(
                                [
                                    ("l10n_ro_vat_number", "=", vat),
                                    ("is_company", "=", True),
                                ]
                            )._l10n_ro_filter_commercial_entities()
                            for partner in partners:
                                data = partner._Anaf_to_Odoo(result_partner)
                                partner.update(data)
            except Exception as e:
                _logger.warning(f"ANAF sync not working: {e}")

    def _l10n_ro_filter_commercial_entities(self):
        """Keep only the commercial entities (not their contacts).

        Odoo 20: ``is_company`` is computed. In ``base`` it means "own commercial
        entity with a VAT number", but ``l10n_ro_edi`` overrides it for Romanian
        partners to "valid company CUI" only, so the contacts of a company, which
        receive the company VAT number, are flagged as companies too. Without this
        filter the ANAF data (name, address...) would overwrite the contacts.
        """
        return self.filtered(lambda p: p.commercial_partner_id == p)

    @api.model
    def update_l10n_ro_vat_subjected_all(self):
        domain = [
            ("l10n_ro_vat_number", "!=", False),
            ("l10n_ro_vat_number", "!=", ""),
            ("country_id", "=", self.env.ref("base.ro").id),
            ("is_company", "=", True),
        ]
        partners = self.search(domain)._l10n_ro_filter_commercial_entities()
        partners.update_l10n_ro_vat_subjected()

    @api.model
    def _update_l10n_ro_vat_subjected_all(self):
        self.update_l10n_ro_vat_subjected_all()
