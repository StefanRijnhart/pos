# coding: utf-8
# Copyright (C) 2014 AKRETION (<http://www.akretion.com>).
# Copyright (C) 2016 Opener B.V. (<https://opener.am>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'POS To Sale Order',
    'version': '8.0.1.0.0',
    'category': 'Point Of Sale',
    'author': 'Akretion, Opener B.V., Odoo Community Association (OCA)',
    'website': 'https://github.com/oca/pos',
    'license': 'AGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/point_of_sale_view.xml',
        'views/assets.xml',
        'views/sale_view.xml',
    ],
    'qweb': [
        'static/src/xml/pos_create_sale_order.xml',
    ],
    'installable': True,
}
