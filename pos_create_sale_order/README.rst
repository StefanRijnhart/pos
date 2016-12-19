POS To Sale Order
=================

This module created a sale order in POS.

Installation
============
When installing this module you might want to consider installing account_bank_statement_sale_order as well, to easily match your bank statement lines with the sale orders paid in the POS. This module is currently under review at https://github.com/OCA/bank-statement-reconcile/pull/114

This module is compatible with the support of fiscal positions of the module 'pos_pricelist'.

Configuration
=============
In order to save orders from the backend, you have to check if the stock operation type configured in the POS has a warehouse set. Look up the name of the Picking Type in the POS configuration, and then check it under menu Stock -> Configuration -> Types of Operation.

Credits
=======

Contributors
------------

* Chafique Delli (chafique.delli@akretion.com)
* David Béal (david.beal@akretion.com)
* Sylvain Calador (sylvain.calador@akretion.com)
* Stefan Rijnhart (stefan@opener.amsterdam)

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.
