# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

BATCH_SIZE_PARAM = "l10n_ro_message_spv.migration_batch_size"
DEFAULT_BATCH_SIZE = 500


def migrate(cr, version):
    """Show the partner on the SPV messages received before 19.0.2.16.0,
    when the partner name started to be stored on the message:

    1. a message linked to a real partner takes its name (plain SQL, fast
       on large tables);
    2. a message with no partner, or with a placeholder partner ("Unknown"
       or named after the CIF), re-reads its invoice XML from the stored
       ZIP. It gets the partner name, the due date and the amounts, and the
       placeholder partner takes the real name from the XML.
    """
    if not version:
        return

    # Placeholder partners, created by earlier versions for an unknown CIF,
    # are named "Unknown" or after the CIF (same rule as
    # models.message_spv._is_placeholder_partner_name).
    cr.execute(
        """
        UPDATE l10n_ro_message_spv m
           SET partner_name = p.name
          FROM res_partner p
         WHERE p.id = m.partner_id
           AND m.partner_name IS NULL
           AND p.name IS NOT NULL
           AND p.name != 'Unknown'
           AND p.name !~* '^(RO)?[0-9]+$'
        """
    )
    _logger.info("SPV messages: partner name taken from the partner on %s", cr.rowcount)

    cr.execute(
        """
        SELECT m.id
          FROM l10n_ro_message_spv m
          LEFT JOIN res_partner p ON p.id = m.partner_id
         WHERE m.partner_name IS NULL
           AND m.attachment_id IS NOT NULL
           AND m.message_type IN
               ('in_invoice', 'in_receipt', 'out_invoice', 'out_receipt')
           AND (m.partner_id IS NULL
                OR p.name = 'Unknown'
                OR p.name ~* '^(RO)?[0-9]+$')
         ORDER BY m.id
        """
    )
    message_ids = [row[0] for row in cr.fetchall()]
    if not message_ids:
        return

    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True})
    get_param = env["ir.config_parameter"].sudo().get_param
    batch_size = int(get_param(BATCH_SIZE_PARAM, DEFAULT_BATCH_SIZE))
    done = unread = failed = 0
    for start in range(0, len(message_ids), batch_size):
        messages = env["l10n.ro.message.spv"].browse(
            message_ids[start : start + batch_size]
        )
        for message in messages:
            # One unreadable ZIP must not stop the upgrade.
            try:
                with cr.savepoint():
                    message.get_xml_fom_zip()
                if message.partner_name:
                    done += 1
                else:
                    unread += 1
            except Exception:
                failed += 1
                _logger.warning(
                    "SPV message %s: the XML could not be re-read",
                    message.name,
                    exc_info=True,
                )
        env.flush_all()
        env.invalidate_all()
        _logger.info(
            "SPV messages: XML re-read %s/%s", start + len(messages), len(message_ids)
        )
    _logger.info(
        "SPV messages: partner name read from the XML on %s messages, "
        "%s without a readable XML, %s failed",
        done,
        unread,
        failed,
    )
