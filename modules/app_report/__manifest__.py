{
    'name' : 'Tax Reports',
    'version': '3.5',
    'Summary': 'Tax Report Prints',
    'description': 'To print the new report',
    'license': 'LGPL-3',
    'depends': [
        'sale_management','website','account_accountant','hr'
    ],    
    'data': [
        'reports/custom_header1.xml',
        'reports/report_tax_invoice.xml',
        'reports/custom_header_copy.xml',
        'reports/report_tax_invoice_copy.xml',
        'reports/custom_header_creditnote.xml',
        'reports/report_credit_note.xml',
        'reports/reports.xml',
        'views/app_report_testview.xml'
    ],
    'installable': True,
    'application':True,
    'auto_install':False
}