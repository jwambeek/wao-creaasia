{
    'name' : 'Tax Reports',
    'version': '1.8',
    'Summary': 'Tax Report Prints',
    'description': 'To print the new report',
    'license': 'LGPL-3',
    'depends': [
        'sale_management','website','account_accountant'
    ],    
    'data': [
        'reports/report_tax_invoice_copy.xml',
        'reports/report_tax_invoice.xml',
        'reports/reports.xml',
        'views/app_report_view.xml',
        #'reports/custom_header.xml',
        #'reports/custom_footer.xml',
        'reports/main_template.xml',
        'reports/example.xml'
    
    ],
    'installable': True,
    'application':True,
    'auto_install':False
}