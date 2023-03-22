from arcpy import AddError, AddFieldDelimiters, AddMessage, Describe, Exists, GetParameterAsText, SetProgressorLabel
from arcpy.da import SearchCursor
from arcpy.management import GetCount
from arcpy.mp import ArcGISProject
from datetime import date
from math import ceil
from os import path as os_path, remove, startfile
from sys import exit, path as sys_path

# Hack to allow imports of local libraries from python_packages folder
base_dir = os_path.abspath(os_path.dirname(__file__)) #\SUPPORT
sys_path.append(os_path.join(base_dir, 'python_packages'))

from python_packages.docx.api import Document
from python_packages.docxcompose.composer import Composer
from python_packages.docxtpl import DocxTemplate


def add_blank_rows(table_data, max_rows):
    '''Given a list of table data, adds empty rows (dict) up to a specified max'''
    if len(table_data) < max_rows:
        for index in range(max_rows - len(table_data)):
            table_data.append({})
    return table_data


### Initial Tool Validation ###
try:
    aprx = ArcGISProject('CURRENT')
    aprx.listMaps('Determinations')[0]
except Exception:
    AddError('This tool must be run from an ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...')
    exit()

AddMessage('Collecting inputs...')
SetProgressorLabel('Collecting inputs...')

### Input Parameters ###
site_cwd_lyr = GetParameterAsText(0)
include_pjw_statement = GetParameterAsText(1)
create_028_form = GetParameterAsText(2)
nrcs_office = GetParameterAsText(3)
fsa_office = GetParameterAsText(4)
consolidate_by_wetland = GetParameterAsText(5)

AddMessage('Assigning local variables...')
SetProgressorLabel('Assigning local variables...')

### Paths to Word Templates ###
templates_dir = os_path.join(base_dir, 'Templates')
customer_letter_template_path = os_path.join(templates_dir, 'WC_Letter_Template.docx')
cpa_026_wc_template_path = os_path.join(templates_dir, 'CPA_026_WC_Template.docx')
cpa_026_wc_supplemental_template_path = os_path.join(templates_dir, 'SupplementalWorksheet_026.docx')
cpa_026_wc_supplemental_template_output = os_path.join(templates_dir, 'SupplementalWorksheet_026_TEMP.docx')
cpa_026_wc_definitions_template_path = os_path.join(templates_dir, 'DefinitionsNDS_026.docx')
cpa_028_wc_template_path = os_path.join(templates_dir, 'CPA_028_WC_Template.docx')
cpa_028_wc_supplemental_template_path = os_path.join(templates_dir, 'SupplementalWorksheet_028.docx')
cpa_028_wc_supplemental_template_output = os_path.join(templates_dir, 'SupplementalWorksheet_028_TEMP.docx')
cpa_028_wc_definitions_template_path = os_path.join(templates_dir, 'DefinitionsNDS_028.docx')

### Paths to SUPPORT GDB ###
support_gdb = os_path.join(base_dir, 'SUPPORT.gdb')
nrcs_addresses_table = os_path.join(support_gdb, 'nrcs_addresses')
fsa_addresses_table = os_path.join(support_gdb, 'fsa_addresses')
nad_addresses_table = os_path.join(support_gdb, 'nad_addresses')

### Paths to Site GDB ###
site_cwd_lyr_path = Describe(site_cwd_lyr).CatalogPath
site_gdb = site_cwd_lyr_path[:site_cwd_lyr_path.find('.gdb')+4]
admin_table = os_path.join(site_gdb, 'Admin_Table')
clu_cwd_026_table = os_path.join(site_gdb, 'CLU_CWD_026')
clu_cwd_026_alt_table = os_path.join(site_gdb, 'CLU_CWD_026_alt')
clu_cwd_028_table = os_path.join(site_gdb, 'CLU_CWD_028')

### Paths to Site Wetlands Folder for Outputs ###
wetlands_dir = os_path.dirname(site_gdb)
customer_letter_output = os_path.join(wetlands_dir, 'WC_Letter.docx')
cpa_026_wc_output = os_path.join(wetlands_dir, 'NRCS-CPA-026-WC-Form.docx')
cpa_028_wc_output = os_path.join(wetlands_dir, 'NRCS-CPA-028-WC-Form.docx')


### Ensure Word Doc Templates Exist ###
#NOTE: Front end validation checks the existance of most geodatabase tables
for path in [customer_letter_template_path, cpa_026_wc_template_path, cpa_026_wc_supplemental_template_path, cpa_026_wc_definitions_template_path,
    cpa_028_wc_template_path, cpa_028_wc_supplemental_template_path, cpa_028_wc_definitions_template_path]:
    if not os_path.exists(path):
        AddError(f'Error: Failed to locate required Word template: {path}. Exiting...')
        exit()
AddMessage('Located required Word templates...')


### Read and assign values from Admin Table ###
SetProgressorLabel('Reading table data...')
if int(GetCount(admin_table)[0]) != 1:
    AddError('Error: Admin Table has more than one entry. Exiting...')
    exit()

try:
    admin_data = {}
    fields = ['admin_state', 'admin_state_name', 'admin_county', 'admin_county_name', 'state_code', 'state_name', 'county_code', 'county_name', 
        'farm_number', 'tract_number', 'client', 'deter_staff', 'dig_staff', 'request_date', 'request_type', 'comments', 'street', 'street_2', 
        'city', 'state', 'zip']
    with SearchCursor(admin_table, fields) as cursor:
        row = cursor.next()
        admin_data['admin_state'] = row[0] if row[0] else ''
        admin_data['admin_state_name'] = row[1] if row[1] else ''
        admin_data['admin_county'] = row[2] if row[2] else ''
        admin_data['admin_county_name'] = row[3] if row[3] else ''
        admin_data['state_code'] = row[4] if row[4] else ''
        admin_data['state_name'] = row[5] if row[5] else ''
        admin_data['county_code'] = row[6] if row[6] else ''
        admin_data['county_name'] = row[7] if row[7] else ''
        admin_data['farm_number'] = row[8] if row[8] else ''
        admin_data['tract_number'] = row[9] if row[9] else ''
        admin_data['client'] = row[10] if row[10] else ''
        admin_data['deter_staff'] = row[11] if row[11] else ''
        admin_data['dig_staff'] = row[12] if row[12] else ''
        admin_data['request_date'] = row[13].strftime('%m/%d/%Y') if row[13] else ''
        admin_data['request_type'] = row[14] if row[14] else ''
        admin_data['comments'] = row[15] if row[15] else ''
        admin_data['street'] = f'{row[16]}, {row[17]}' if row[17] else row[16]
        admin_data['city'] = row[18] if row[18] else ''
        admin_data['state'] = row[19] if row[19] else ''
        admin_data['zip'] = row[20] if row[20] else ''
except Exception as e:
    AddError('Error: failed while retrieving Admin Table data. Exiting...')
    AddError(e)
    exit()

AddMessage('Retrieved data from Admin Table...')


### Read and assign values from NRCS Addresses Table - select row by NRCS Office input ###
try:
    nrcs_address = {}
    fields = ['NRCSOffice', 'NRCSAddress', 'NRCSCITY', 'NRCSSTATE', 'NRCSZIP', 'NRCSPHONE', 'NRCSFAX']
    where_clause = """{0}='{1}'""".format(AddFieldDelimiters(support_gdb, 'NRCSOffice'), nrcs_office)
    with SearchCursor(nrcs_addresses_table, fields, where_clause) as cursor:
        row = cursor.next()
        nrcs_address['office'] = row[0] if row[0] else ''
        nrcs_address['street'] = row[1] if row[1] else ''
        nrcs_address['city'] = row[2] if row[2] else ''
        nrcs_address['state'] = row[3] if row[3] else ''
        nrcs_address['zip'] = row[4] if row[4] else ''
        nrcs_address['phone'] = row[5] if row[5] else ''
        nrcs_address['fax'] = row[6] if row[6] else ''
except Exception as e:
    AddError('Error: failed while retrieving NRCS Address Table data. Exiting...')
    AddError(e)
    AddError('You may need to run tool F.Import Office Addresses and then try this tool again.')
    exit()

AddMessage('Retrieved data from NRCS Addresses Table...')

### Read and assign values from FSA Addresses Table - select row by FSA Office input ###
try:
    fsa_address = {}
    fields = ['FSAOffice', 'FSAAddress', 'FSACITY', 'FSASTATE', 'FSAZIP', 'FSAPHONE', 'FSAFAX', 'FSACounty']
    where_clause = """{0} = '{1}'""".format(AddFieldDelimiters(support_gdb, 'FSAOffice'), fsa_office)
    with SearchCursor(fsa_addresses_table, fields, where_clause) as cursor:
        row = cursor.next()
        fsa_address['office'] = row[0] if row[0] else ''
        fsa_address['street'] = row[1] if row[1] else ''
        fsa_address['city'] = row[2] if row[2] else ''
        fsa_address['state'] = row[3] if row[3] else ''
        fsa_address['zip'] = row[4] if row[4] else ''
        fsa_address['phone'] = row[5] if row[5] else ''
        fsa_address['fax'] = row[6] if row[6] else ''
        fsa_address['county'] = row[7] if row[7] else ''
except Exception as e:
    AddError('Error: failed while retrieving FSA Address Table data. Exiting...')
    AddError(e)
    AddError('You may need to run tool F.Import Office Addresses and then try this tool again.')
    exit()

AddMessage('Retrieved data from FSA Addresses Table...')


### Read and assign values from NAD Addresses Table - select row by State Code from Admin Table ###
if not Exists(nad_addresses_table):
    AddError('NAD Addresses table not found in SUPPORT.gdb. Exiting...')
    exit()

try:
    nad_address = {}
    fields = ['STATECD', 'STATE', 'NADADDRESS', 'NADCITY', 'NADSTATE', 'NADZIP', 'TOLLFREE', 'PHONE', 'TTY', 'FAX']
    where_clause = """{0} = '{1}'""".format(AddFieldDelimiters(support_gdb, 'STATECD'), admin_data['state_code'])
    with SearchCursor(nad_addresses_table, fields, where_clause) as cursor:
        row = cursor.next()
        nad_address['state'] = row[1] if row[1] else ''
        nad_address['street'] = row[2] if row[2] else ''
        nad_address['city'] = row[3] if row[3] else ''
        nad_address['state'] = row[4] if row[4] else ''
        nad_address['zip'] = row[5] if row[5] else ''
        nad_address['toll_free'] = row[6] if row[6] else ''
        nad_address['phone'] = row[7] if row[7] else ''
        nad_address['tty'] = row[8] if row[8] else ''
        nad_address['fax'] = row[9] if row[9] else ''
except Exception as e:
    AddError('Error: failed while retrieving NAD Address Table data. Exiting...')
    AddError(e)
    AddError('You may need to run tool F.Import Office Addresses and then try this tool again.')
    exit()

AddMessage('Retrieved data from NAD Addresses Table...')


### Generate Customer Letter ###
SetProgressorLabel('Generating WC_Letter.docx...')
try:
    customer_letter_template = DocxTemplate(customer_letter_template_path)
    context = {
        'today_date': date.today().strftime('%A, %B %d, %Y'),
        'admin_data': admin_data,
        'nrcs_address': nrcs_address,
        'fsa_address': fsa_address,
        'nad_address': nad_address
    }
    customer_letter_template.render(context)
    customer_letter_template.save(customer_letter_output)
    AddMessage('Created WC_Letter.docx...')
except PermissionError:
    AddError('Error: Please close any open Word documents and try again. Exiting...')
    exit()
except Exception as e:
    AddError('Error: Failed to create WC_Letter.docx. Exiting...')
    AddError(e)
    exit()


### Read and assign values from CLU CWD 026 Table ###
SetProgressorLabel('Generating NRCS-CPA-026-WC-Form.docx...')
try:
    table_026 = clu_cwd_026_alt_table if consolidate_by_wetland == 'true' else clu_cwd_026_table
    data_026_pg1 = [] #11 rows
    data_026_pg2 = [] #15 rows
    data_026_extra = []
    fields = ['clu_number', 'wetland_label', 'occur_year', 'SUM_acres']
    with SearchCursor(table_026, fields) as cursor:
        row_count = 0
        for row in cursor:
            row_count += 1
            row_data = {}
            row_data['clu'] = row[0] if row[0] else ''
            row_data['label'] = row[1] if row[1] else ''
            row_data['year'] = row[2] if row[2] else ''
            row_data['acres'] = f'{row[3]:.2f}' if row[3] else ''
            if row_count < 12:
                data_026_pg1.append(row_data)
            elif row_count > 11 and row_count < 27:
                data_026_pg2.append(row_data)
            else:
                data_026_extra.append(row_data)
except Exception as e:
    AddError('Error: failed while retrieving CLU CWD 026 Table data. Exiting...')
    AddError(e)
    exit()


### Generate Pages 1 and 2 of 026 Form ###
pjw_statement = 'Areas identified as Potential Jurisdictional Waters (PJW) are not subject to the Food Security Act but are potentially subject to the Clean Water Act. You should contact the U.S. Army Corps of Engineers local district office prior to performing work in areas which may be subject to the Clean Water Act. Areas identified as PJW are for informational purposes only and are not appealable to USDA. Additional areas, not identified by NRCS, might also be subject to the Clean Water Act.'
try:
    cpa_026_wc_template = DocxTemplate(cpa_026_wc_template_path)
    context = {
        'admin_data': admin_data,
        'pjw_statement': pjw_statement if include_pjw_statement == 'Yes' else '',
        'data_026_pg1': add_blank_rows(data_026_pg1, 11),
        'data_026_pg2': add_blank_rows(data_026_pg2, 15) 
    }
    cpa_026_wc_template.render(context)
    cpa_026_wc_template.save(cpa_026_wc_output)
    cpa_026_wc_doc = Document(cpa_026_wc_output)
    cpa_026_wc_composer = Composer(cpa_026_wc_doc)
    AddMessage('Created pages 1 and 2 of NRCS-CPA-026-WC-Form.docx...')
except PermissionError:
    AddError('Error: Please close any open Word documents and try again. Exiting...')
    exit()
except Exception as e:
    AddError('Error: Failed to create pages 1 and 2 of NRCS-CPA-026-WC-Form.docx. Exiting...')
    AddError(e)
    exit()


### Generate 026 Supplemental Pages if Needed ###
if data_026_extra:
    number_pages = ceil(len(data_026_extra)/15)
    for page_number in range(number_pages):
        # Fill pages with sets of 15, removing from original list
        page_data = []
        page_data.extend(data_026_extra[:15])
        del data_026_extra[:15]
        try:
            page_data = add_blank_rows(page_data, 15)
            cpa_026_wc_supplemental_template = DocxTemplate(cpa_026_wc_supplemental_template_path)
            context = {'data_026_extra': page_data}
            cpa_026_wc_supplemental_template.render(context)
            cpa_026_wc_supplemental_template.save(cpa_026_wc_supplemental_template_output)
            supplemental_026_doc = Document(cpa_026_wc_supplemental_template_output)
            cpa_026_wc_composer.append(supplemental_026_doc)
            remove(cpa_026_wc_supplemental_template_output)
            AddMessage(f'Created 026 Supplemental Worksheet page {page_number+3}...')
        except Exception as e:
            AddError(f'Error: Failed to create 026 Supplemental Worksheet page {page_number+3}. Exiting...')
            AddError(e)
            exit()


### Combine Pages and Save Final 026 Form ###
try:
    definitions_026_doc = Document(cpa_026_wc_definitions_template_path)
    cpa_026_wc_composer.append(definitions_026_doc)
    cpa_026_wc_composer.save(cpa_026_wc_output)
    AddMessage('Appended Wetland Definitions template and finalized NRCS-CPA-026-WC-Form.docx...')
except PermissionError:
    AddError('Error: Please close any open Word documents and try again. Exiting...')
    exit()
except Exception as e:
    AddError('Error: Failed to append Wetland Definitions template and finalize 026 Form. Exiting...')
    AddError(e)
    exit()


### Read and assign values from CLU CWD 028 Table ###
if create_028_form == 'Yes':
    try:
        SetProgressorLabel('Generating NRCS-CPA-028-WC-Form.docx...')
        data_028_pg1 = [] #12 rows
        data_028_pg2 = [] #20 rows
        data_028_extra = []
        fields = ['clu_number', 'wetland_label', 'occur_year', 'cert_date', 'SUM_acres']
        with SearchCursor(clu_cwd_028_table, fields) as cursor:
            row_count = 0
            for row in cursor:
                row_count += 1
                row_data = {}
                row_data['clu'] = row[0] if row[0] else ''
                row_data['label'] = row[1] if row[1] else ''
                row_data['year'] = row[2] if row[2] else ''
                row_data['date'] = row[3].strftime('%m/%d/%Y') if row[3] else ''
                row_data['acres'] = f'{row[4]:.2f}' if row[4] else ''
                if row_count < 13:
                    data_028_pg1.append(row_data)
                elif row_count > 12 and row_count < 33:
                    data_028_pg2.append(row_data)
                else:
                    data_028_extra.append(row_data)
    except Exception as e:
        AddError('Error: failed while retrieving CLU CWD 028 Table data. Exiting...')
        AddError(e)
        exit()


    ### Generate Pages 1 and 2 of 028 Form ###
    try:
        cpa_028_wc_template = DocxTemplate(cpa_028_wc_template_path)
        context = {
            'today_date': date.today().strftime('%m/%d/%Y'),
            'admin_data': admin_data,
            'data_028_pg1': add_blank_rows(data_028_pg1, 12),
            'data_028_pg2': add_blank_rows(data_028_pg2, 20) 
        }
        cpa_028_wc_template.render(context)
        cpa_028_wc_template.save(cpa_028_wc_output)
        cpa_028_wc_doc = Document(cpa_028_wc_output)
        cpa_028_wc_composer = Composer(cpa_028_wc_doc)
        AddMessage('Created pages 1 and 2 of NRCS-CPA-028-WC-Form.docx...')
    except PermissionError:
        AddError('Error: Please close any open Word documents and try again. Exiting...')
        exit()
    except Exception as e:
        AddError('Error: Failed to create pages 1 and 2 of NRCS-CPA-028-WC-Form.docx. Exiting...')
        AddError(e)
        exit()


    ### Generate 028 Supplemental Pages if Needed ###
    if data_028_extra:
        number_pages = ceil(len(data_028_extra)/20)
        for page_number in range(number_pages):
            # Fill pages with sets of 20, removing from original list
            page_data = []
            page_data.extend(data_028_extra[:20])
            del data_028_extra[:20]
            try:
                page_data = add_blank_rows(page_data, 20)
                cpa_028_wc_supplemental_template = DocxTemplate(cpa_028_wc_supplemental_template_path)
                context = {'data_028_extra': page_data}
                cpa_028_wc_supplemental_template.render(context)
                cpa_028_wc_supplemental_template.save(cpa_028_wc_supplemental_template_output)
                supplemental_028_doc = Document(cpa_028_wc_supplemental_template_output)
                cpa_028_wc_composer.append(supplemental_028_doc)
                remove(cpa_028_wc_supplemental_template_output)
                AddMessage(f'Created 028 Supplemental Worksheet page {page_number+3}...')
            except Exception as e:
                AddError(f'Error: Failed to create 028 Supplemental Worksheet page {page_number+3}. Exiting...')
                AddError(e)
                exit()

    
    ### Combine Pages and Save Final 028 Form ###
    try:
        definitions_028_doc = Document(cpa_028_wc_definitions_template_path)
        cpa_028_wc_composer.append(definitions_028_doc)
        cpa_028_wc_composer.save(cpa_028_wc_output)
        AddMessage('Combined pages and created NRCS-CPA-028-WC-Form.docx...')
    except PermissionError:
        AddError('Error: Please close any open Word documents and try again. Exiting...')
        exit()
    except Exception as e:
        AddError('Error: Failed to append Wetland Definitions template and finalize 028 Form. Exiting...')
        AddError(e)
        exit()


### Open Customer Letter, 026 Form, and 028 Form (Optional) ###
AddMessage('Finished generating forms, opening in Microsoft Word...')
SetProgressorLabel('Finished generating forms, opening in Microsoft Word...')
try:
    startfile(customer_letter_output)
    startfile(cpa_026_wc_output)
    if create_028_form == 'Yes':
        startfile(cpa_028_wc_output)
except Exception as e:
    AddError('Error: Failed to open finished forms in Microsoft Word. End of script.')
    AddError(e)
