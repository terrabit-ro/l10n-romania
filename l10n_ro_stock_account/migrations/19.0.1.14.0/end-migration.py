import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _get_transfer_account(env, company):
    # In 18.0, when the company had no stock transfer account, the moves through
    # a transit location fell back on the valuation account of that location.
    # In 19.0 the transfer account is read only from the company.
    transit_locations = (
        env["stock.location"]
        .with_company(company)
        .search(
            [("usage", "=", "transit"), ("company_id", "in", [company.id, False])],
            order="company_id",
        )
    )
    for location in transit_locations:
        if location.l10n_ro_property_stock_valuation_account_id:
            return location.l10n_ro_property_stock_valuation_account_id
    account = (
        env["account.chart.template"]
        .with_company(company)
        .ref("pcg_482", raise_if_not_found=False)
    )
    if not account:
        account = (
            env["account.account"]
            .with_company(company)
            .search(
                [
                    ("company_ids", "parent_of", company.id),
                    ("code", "=like", "482%"),
                ],
                limit=1,
            )
        )
    return account


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].search(
        [
            ("l10n_ro_accounting", "=", True),
            ("l10n_ro_property_stock_transfer_account_id", "=", False),
        ]
    )
    for company in companies:
        account = _get_transfer_account(env, company)
        if not account:
            _logger.warning(
                "l10n_ro_stock_account: no stock transfer account (482) found "
                "for company %s, set it in the Romanian accounting settings",
                company.name,
            )
            continue
        company.l10n_ro_property_stock_transfer_account_id = account
        _logger.info(
            "l10n_ro_stock_account: stock transfer account %s set on company %s",
            account.code,
            company.name,
        )
