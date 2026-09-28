from odoo import models


class MergePartnerAutomatic(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        ctx = {"partner_merge": True}
        partners = self.env["res.partner"].browse(partner_ids).with_context(**ctx)
        if dst_partner:
            dst_partner = dst_partner.with_context(**ctx)
        # the wizard browses the partners with its own environment (e.g. when no
        # destination partner is given), so the flag is set on the wizard too
        return super(MergePartnerAutomatic, self.with_context(**ctx))._merge(
            partners.ids, dst_partner=dst_partner, extra_checks=extra_checks
        )
