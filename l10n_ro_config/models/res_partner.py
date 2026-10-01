# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "l10n.ro.mixin"]

    l10n_ro_vat_subjected = fields.Boolean(string="Romania - VAT Subjected")
    l10n_ro_vat_number = fields.Char(
        string="Romania - VAT number digits",
        compute="_compute_l10n_ro_vat_number",
        store=True,
        help="VAT number without country code.",
    )
    l10n_ro_caen_code = fields.Char(string="Romania - CAEN Code", default="0000")
    l10n_ro_e_invoice = fields.Boolean(string="Romania - E-Invoicing", copy=False)

    @api.depends("vat")
    def _compute_l10n_ro_vat_number(self):
        for partner in self:
            l10n_ro_vat_number = ""
            if partner.vat:
                l10n_ro_vat_number = self._split_vat(partner.vat)[1]
            partner.l10n_ro_vat_number = l10n_ro_vat_number

    def _l10n_ro_map_vat_country_code(self, country_code):
        country_code_map = {
            "RE": "FR",
            "GP": "FR",
            "MQ": "FR",
            "GF": "FR",
            "EL": "GR",
        }
        return country_code_map.get(country_code, country_code)

    def _split_vat(self, vat):
        """Allow the Romanian CUI to be written without the "RO" prefix.

        The country code is taken from the current record, never from a database
        lookup. A previous implementation searched for a partner having the same
        ``vat`` and borrowed its country code: during create/write the record is
        already in the database when ``_check_vat`` runs, so it found itself and
        ``_run_vat_checks`` re-attached the prefix. That made it impossible to
        store a tax ID without its country prefix - for instance a Hungarian
        11-digit adoszam, which VIES only accepts in its 8-digit EU form.

        Odoo 20 merged ``base_vat`` into ``base`` and dropped the
        ``res.partner._split_vat`` hook (``_run_vat_checks`` now calls
        ``odoo.tools.business_data.split_vat``), so there is no ``super()``:
        the Odoo 19 ``base_vat`` splitting is reproduced here for the callers
        in the Romanian localization.
        """
        vat_country, l10n_ro_vat_number = "", vat
        if vat and vat[:2].isalpha():
            vat_country = vat[:2].upper()
            l10n_ro_vat_number = vat[2:].replace(" ", "")
        if vat_country or not vat or not vat.isdigit():
            return vat_country, l10n_ro_vat_number
        country_code = self.country_id.code if len(self) == 1 else False
        if (
            country_code
            and self._l10n_ro_map_vat_country_code(country_code.upper()) == "RO"
        ):
            vat_country = "RO"
        return vat_country, l10n_ro_vat_number

    def _get_ro_vat(self):
        self.ensure_one()
        returned_vat = self.vat
        if (
            self.is_l10n_ro_record
            and self.vat
            and self.country_id
            and self.country_id.code == "RO"
        ):
            if self.l10n_ro_vat_subjected and self.vat.isdigit():
                returned_vat = "RO" + self.vat
            elif not self.l10n_ro_vat_subjected and not self.vat.isdigit():
                _vat_country, l10n_ro_vat_number = self._split_vat(self.vat)
                returned_vat = l10n_ro_vat_number

        return returned_vat

    def _check_vat(self, validation="error"):
        res = super()._check_vat(validation=validation)
        for partner in self:
            ro_vat = partner._get_ro_vat()
            if partner.vat != ro_vat:
                partner.vat = ro_vat
        return res

    def _compute_is_company(self):
        """Only a commercial entity can be a company.

        ``base`` computes ``is_company`` as "own commercial entity and has a VAT",
        but ``l10n_ro_edi`` replaces it for Romanian partners with a check of the
        CUI alone, without calling ``super()``. Contacts inherit the CUI of their
        company, so every contact of a Romanian company became a company too.
        Restore the commercial-entity condition on top of both computations.
        """
        res = super()._compute_is_company()
        for partner in self:
            if partner.commercial_partner_id != partner:
                partner.is_company = False
        return res

    @api.onchange("l10n_ro_vat_subjected")
    def onchange_l10n_ro_vat_subjected(self):
        if (
            not self.env.context.get("skip_ro_vat_change")
            and self.country_id.code == "RO"
        ):
            self.vat = self._get_ro_vat()

    # Odoo 20: ``res.partner.company_registry`` and its compute no longer exist,
    # so the Odoo 19 override ``_compute_company_registry`` (which mirrored the
    # NRC into ``company_registry``) was dropped. The NRC stays on ``nrc``.
