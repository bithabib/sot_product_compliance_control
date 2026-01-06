# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    compliance_notification_email = fields.Char(
        string='Compliance Notification Email',
        config_parameter='product_compliance.notification_email',
        help='Email address to receive compliance status change notifications. '
             'Multiple emails can be separated by commas.'
    )


class ProductComplianceType(models.Model):
    _name = 'product.compliance.type'
    _description = 'Product Compliance Type'
    _order = 'name'

    name = fields.Char(
        string='Compliance Name',
        required=True
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Compliance type name must be unique!')
    ]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    test_date = fields.Date(
        string='Test Date'
    )

    tracking_date = fields.Date(
        string='Tracking Date'
    )

    compliance_note = fields.Text(
        string='Compliance Notes'
    )

    compliance_line_ids = fields.One2many(
        'product.compliance.line',
        'product_id',
        string='Compliance Checklist'
    )

    compliance_status = fields.Selection(
        [
            ('approved', 'Approved'),
            ('warning', 'Warning'),
            ('not_approved', 'Not Approved'),
            ('no_compliance', 'No Compliance'),
        ],
        string='Compliance Status',
        compute='_compute_compliance_status',
        store=True,
        tracking=True
    )

    previous_compliance_status = fields.Selection(
        [
            ('approved', 'Approved'),
            ('warning', 'Warning'),
            ('not_approved', 'Not Approved'),
            ('no_compliance', 'No Compliance'),
        ],
        string='Previous Compliance Status',
        copy=False
    )

    @api.depends('compliance_line_ids', 'compliance_line_ids.status', 'test_date', 'tracking_date')
    def _compute_compliance_status(self):
        for product in self:
            if not product.compliance_line_ids:
                product.compliance_status = 'no_compliance'
                continue

            # Get compliance line statuses by type name (case-insensitive)
            compliance_dict = {}
            for line in product.compliance_line_ids:
                type_name = line.compliance_type_id.name.lower() if line.compliance_type_id.name else ''
                compliance_dict[type_name] = line.status

            # Get individual compliance values
            test_reports = compliance_dict.get('test reports', 'no')
            labeling = compliance_dict.get('labeling', 'no')
            tracking_on_item = compliance_dict.get('tracking on item', 'no')

            # Check if tracking conditions are met (for warning status)
            tracking_ok = tracking_on_item in ('yes', 'na')
            tracking_date_filled = bool(product.tracking_date)

            # Check if all field conditions are met
            all_fields_ok = (
                test_reports == 'yes' and
                labeling in ('yes', 'na') and
                tracking_on_item in ('yes', 'na')
            )

            # Check if both dates are filled
            both_dates_filled = bool(product.test_date and product.tracking_date)

            # Check date range (±12 months)
            date_range_valid = False
            if both_dates_filled:
                min_date = product.test_date - relativedelta(months=12)
                max_date = product.test_date + relativedelta(months=12)
                date_range_valid = min_date <= product.tracking_date <= max_date

            # Determine new status
            if all_fields_ok and both_dates_filled and date_range_valid:
                new_status = 'approved'
            elif tracking_ok and tracking_date_filled:
                # Warning: Tracking is OK but missing other requirements
                new_status = 'warning'
            else:
                new_status = 'not_approved'

            # Check for status change from approved to not_approved
            old_status = product.previous_compliance_status or product.compliance_status
            if old_status == 'approved' and new_status == 'not_approved':
                product._send_compliance_status_notification()

            # Update status fields
            product.compliance_status = new_status
            product.previous_compliance_status = new_status

    def _send_compliance_status_notification(self):
        """Send notification when compliance status changes from Approved to Not Approved."""
        self.ensure_one()

        # Collect all email addresses to notify
        emails_to_notify = []

        # 1. Get configured email address from settings
        notification_email = self.env['ir.config_parameter'].sudo().get_param(
            'product_compliance.notification_email'
        )
        if notification_email:
            emails_to_notify.extend([e.strip() for e in notification_email.split(',') if e.strip()])

        # 2. Get emails from users in the Compliance Notifications group
        compliance_group = self.env.ref(
            'sot_product_compliance_control.group_compliance_notification',
            raise_if_not_found=False
        )
        if compliance_group:
            for user in compliance_group.users:
                if user.email and user.email not in emails_to_notify:
                    emails_to_notify.append(user.email)

        # Send email to all collected addresses
        if emails_to_notify:
            self._send_compliance_email(','.join(emails_to_notify))

        # Post message in chatter
        self.message_post(
            body=_('Compliance status changed from <b>Approved</b> to <b>Not Approved</b>.'),
            subject=_('Compliance Status Alert'),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def _send_compliance_email(self, email_to):
        """Send direct email notification for compliance status change."""
        self.ensure_one()
        template = self.env.ref(
            'sot_product_compliance_control.email_template_compliance_status_change',
            raise_if_not_found=False
        )
        if template:
            # Send using email template
            template.send_mail(self.id, force_send=True, email_values={'email_to': email_to})
        else:
            # Fallback: send email directly without template
            mail_values = {
                'subject': _('Compliance Alert: %s - Status Changed to Not Approved') % self.name,
                'body_html': _('''
                    <p>Hello,</p>
                    <p>The compliance status for the following product has changed from <b>Approved</b> to <b>Not Approved</b>:</p>
                    <ul>
                        <li><b>Product:</b> %s</li>
                        <li><b>Internal Reference:</b> %s</li>
                        <li><b>Test Date:</b> %s</li>
                        <li><b>Tracking Date:</b> %s</li>
                    </ul>
                    <p>Please review the product compliance information.</p>
                    <p>Best regards,<br/>Odoo Compliance System</p>
                ''') % (
                    self.name,
                    self.default_code or 'N/A',
                    self.test_date or 'N/A',
                    self.tracking_date or 'N/A',
                ),
                'email_to': email_to,
                'email_from': self.env.company.email or self.env.user.email,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()

    @api.model
    def _cron_recompute_compliance_status(self):
        """Cron job to re-evaluate compliance status for all products.

        This is needed because the date range validation (±12 months)
        can expire over time without any field changes.
        """
        products = self.search([
            ('compliance_line_ids', '!=', False),
            ('test_date', '!=', False),
            ('tracking_date', '!=', False),
        ])
        products._compute_compliance_status()
        return True


class ProductComplianceLine(models.Model):
    _name = 'product.compliance.line'
    _description = 'Product Compliance Line'
    _order = 'id'

    product_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='cascade'
    )

    compliance_type_id = fields.Many2one(
        'product.compliance.type',
        string='Compliance Name',
        required=True
    )

    status = fields.Selection(
        [
            ('yes', 'Yes'),
            ('no', 'No'),
            ('na', 'N/A'),
        ],
        string='Status',
        default='no',
        required=True
    )

    notes = fields.Text(
        string='Notes'
    )
