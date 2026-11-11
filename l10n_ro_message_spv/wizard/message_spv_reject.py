# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MessageSPVReject(models.TransientModel):
    _name = "l10n.ro.message.spv.reject"
    _description = "Reject SPV Invoice"

    message_ids = fields.Many2many("l10n.ro.message.spv", string="Messages")
    reason = fields.Text(required=True)

    def action_reject(self):
        self.message_ids._l10n_ro_reject(self.reason)
        return {"type": "ir.actions.act_window_close"}
