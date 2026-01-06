{
    'name': 'Product Compliance Control',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Products',
    'summary': 'Product compliance tracking with automatic approval status based on test reports, labeling, tracking, and date validation rules.',
    'description': """
Product Compliance Control Module
=================================

This module adds a Compliance tab to products with the following features:

- Compliance Fields: Test Reports, Labeling, Tracking on Item
- Date Fields: Test Date, Tracking Date
- Automatic Approval Logic based on field values and date range validation
- Status Color Coding:
    * Green (Approved) - All requirements met
    * Yellow (Warning) - Previously approved but date range exceeded
    * Red (Not Approved) - Requirements not met
- Dynamic re-evaluation when fields or dates change
- Notifications when status changes from Approved to Not Approved

Approval Rules:
- Test Reports must be "Yes"
- Labeling must be "Yes" or "NA"
- Tracking on Item must be "Yes" or "NA"
- Both Test Date and Tracking Date must be filled
- Tracking Date must be within ±12 months of Test Date
    """,
    'author': 'School of Thought',
    'website': 'https://www.qbithabib.com',
    'depends': ['base', 'product', 'mail'],
    'data': [
        'security/compliance_security.xml',
        'security/ir.model.access.csv',
        'data/compliance_data.xml',
        'data/compliance_cron.xml',
        'data/email_template.xml',
        'views/product_compliance_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
