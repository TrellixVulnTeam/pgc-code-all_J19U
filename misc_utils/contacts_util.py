# -*- coding: utf-8 -*-
"""
Created on Wed Jan  9 10:03:43 2019

@author: disbr007
"""

import calendar
import datetime
import pandas as pd
import numpy as np
import os
import shutil

def emailByRegion(contacts_xl, region):
    '''Generate list of contact emails only for selected region, writes to txt file'''
    df = pd.read_excel(contacts_xl, header=0)
    emails = df[df['Region']==region]['Email'].tolist()
    emails = ', '.join(emails)
    out_dir = os.path.dirname(contacts_xl)
    outpath = os.path.join(out_dir, '{}_emails.txt'.format(region))
    with open(outpath, 'w') as email_txt:
        email_txt.write(r'{}'.format(emails))
    return emails
   
def contacts_update(contacts_xl, new_contacts_xl):
    # For naming outputs
    date = str(datetime.date.today())
    year, month, day = date.split('-')
    date_words = r'{}{}{}'.format(year, str.lower(calendar.month_abbr[int(month)]), day)
    new_contacts = pd.read_csv(new_contacts_xl, sep=',', encoding = "ISO-8859-1")
#    new_contacts['First Name'], new_contacts['Last Name'] = new_contacts['Name'].str.split(' ', 1).str
    new_contacts['Region'] = np.NaN
    new_contacts['Old/New'] = 'New'
    
    copy_contacts_xl = os.path.join(os.path.dirname(contacts_xl), r'{}_{}.xls'.format(os.path.splitext(os.path.basename(contacts_xl))[0], date_words))
    shutil.copyfile(contacts_xl, copy_contacts_xl)
    
    contacts = pd.read_excel(copy_contacts_xl)
    contacts['Old/New'] = 'Old'
    contacts = contacts.append(new_contacts)
    contacts.drop_duplicates(subset='Name', keep='first', inplace=True)
    writer = pd.ExcelWriter(copy_contacts_xl, engine='xlsxwriter')
    contacts.to_excel(writer, header=True, index=False, sheet_name='Sheet1')
    writer.save()
    return contacts

working_dir = r'E:\disbr007\UserServicesRequests\contacts'
contacts_path = os.path.join(working_dir, 'contacts_2019jan17.xls')
new_contacts_path = os.path.join(working_dir, 'new_contacts.csv')

    
#updated_contacts2 = contacts_update(contacts_path, new_contacts_path)

arctic_emails = emailByRegion(contacts_path, 'Arctic')

#new_contacts = pd.read_csv(new_contacts_path, sep=',', encoding = "ISO-8859-1")
#new_contacts['First Name'], new_contacts['Last Name'] = new_contacts['Name'].str.split(' ', 1).str
