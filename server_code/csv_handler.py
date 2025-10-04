import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv
import re
import uuid

transaction_keys = {'date':'Value Date','description':'Description','amount':'Amount'}
all_trans_keys = ['date','description','amount','account','notes','hash']
# Hash will be a unique id to detect duplicates: daymonthyearamountaccount

@anvil.server.callable
def read_file(fn):
  mBytes = fn.get_bytes()

  # Convert bytes to a string.
  mString = str(mBytes, "utf-8")
  #   app_tables.flights.get(uid=anvil.users.get_user()['uid'])['log_string'] = mString
  # Create a list of lines split on \n
  line_list = mString.split('\n')
  # which line is the header?
  head_line = header_line(line_list)
  # find alphanumeric words in the account header
  key_words = header_words(line_list,head_line)
  # do we know the account name?
  found, acc_id = account_finder(key_words)
  # comvert text file transaction body to list of lists and load transactions. 
  load_transactions(line_list,acc_id,head_line)
  # If there's no account, we cannot hash. 
  # Confirm with popup, popup must be able to change hash anyway and re-check.
  
  
  

def header_line(file):
  header_triggers = ["date","amount","description","details","debits","credits","balance"]
  r = 0
  for l in file:
    r += 1
    triggers = 0
    for t in header_triggers:
      if t in l.lower():
        triggers += 1
    # print(l)
    if triggers > 2:
      break
  return r-1

def header_words(csv_output, header):
  # find all alphanum string-parts in the csv rows before the ehader row
  word_list = []
  for l in csv_output[0:header]:
    for word in re.findall(r'[a-zA-Z0-9]+', l):
      word_list.append(word)
  return word_list

@anvil.server.callable
def need_an_id():
  return str(uuid.uuid4())

def account_finder(keys):
  # get all the accounts
  accounts = []
  for row in app_tables.accounts.search():
    row_dict = dict(row)
    accounts.append(row_dict)
  found = False
  match = True
  acc_id = ''
  for acc in accounts:
    match = True
    if len(acc['acc_keywords']) > 0:
      for key in acc['acc_keywords']:
        if not key in keys:
          match = False
      if match:
        acc_id = acc['acc_id']
        found = True
        break
  return found, acc_id

def load_transactions(file,account,head_line):
  # first we get a list of lists
  sep,quote = find_sep_quote(file)
  new = file[head_line].replace("\r","")
  new = new.replace(" ","")
  if quote:
    new=new.replace(quote,"")
  header_list = new.split(sep)
  print(header_list)
  raw_list = []
  for line in file[head_line+1:]:
    new = line.replace("\r","")
    new = new.replace(" ","")
    try:
      if new[-1] == ',':
        new = new[0:-1]
    except:
      pass
    if new:
      raw_list.append(new.split(sep))
  # first we check head_line for debits/credits or amount
  if not 'Amount' in header_list:
    dbt = header_list.index("Debits")
    crt = header_list.index("Credits")
    header_list.append("Amount")
    for t in raw_list:
      c = float(t[crt]) if t[crt] else 0.0
      d = float(t[dbt]) if t[dbt] else 0.0
      t.append(str(c-d))
  # Now we make a transaction dictionary
  trans_list = []
  for t in raw_list:
    d = dict(zip(header_list,t))
    trans_list.append(d)
  # this dictionary is still based on the CSV file. We have to get it into BudgetX language keys
  

def convert_CSV_LIST(csv_object):
  # Get the data as bytes.
  mBytes = csv_object.get_bytes()

  # Convert bytes to a string.
  mString = str(mBytes, "utf-8")
  #   app_tables.flights.get(uid=anvil.users.get_user()['uid'])['log_string'] = mString
  # Create a list of lines split on \n
  line_list = mString.split('\n')
  header = line_list[0]
  sep, quote = find_sep_quote(line_list)

  # Bring the generic keys and user defined names
  concrete_keys = app_tables.generic.get(rid='generic')['concrete_keys']
  # turn user defined list of dicts into a dict with key: user's name for field; value: generic key list
  user_key_names = build_user_keys(app_tables.settings.get(uid=anvil.users.get_user()['uid'])['key_display_names'])

  key_list = header.split(sep)
  if '\ufeff' in key_list[0]:
    t = key_list[0][1:]
    key_list.pop(0)
    key_list.insert(0,t)
  add_list = []
  for con_key in concrete_keys:
    if con_key not in key_list:
      add_list.append(con_key)
  new_logbook = []
  non_included = []
  for line in line_list[1:]:
    flight_list = None
    if quote != "":
      if line.count(quote) != 0:
        flight_list = parse_quote(line,sep,quote)
      else:
        flight_list = line.split(sep)
    else:
      flight_list = line.split(sep)
    flight = {}
    idx = 0
    if len(flight_list) > 1:
      for key in key_list:
        if key in concrete_keys:
          flight[key] = flight_list[idx]
        elif key in user_key_names.keys():
          flight[user_key_names[key]] = flight_list[idx]
        else:
          if not key in non_included:
            non_included.append(key)
        idx += 1
      for add_key in add_list:
        flight[add_key] = ''

    new_logbook.append(flight)

  return new_logbook,non_included

def parse_quote(line, sep, quote):
  line = line.split(sep)
  idx = 0
  for item in line:
    if item.count(quote) > 0:
      sub_line = line[idx + 1:]
      brk = 0
      for sub in sub_line:
        if sub.count(quote) > 0:
          break
        else:
          brk += 1
      n_item = ''
      for i in range(idx, idx + brk + 2):
        n_item += line[i] + sep
      line[idx] = n_item[0:-1]
      for i in range(idx + 1,idx + brk + 2):
        line.pop(idx + 1)
    idx += 1
  return line

def find_sep_quote(list_obj):
  s_c = 0
  l_c = 0
  d_q = 0
  s_q = 0
  for line in list_obj:
    s_c += line.count(',')
    l_c += line.count(';')
    d_q += line.count('"')
    s_q += line.count("'")
  if s_c > l_c:
    sep = ','
  else:
    sep = ';'
  if d_q > s_q:
    quo = '"'
  elif s_q > d_q:
    quo = "'"
  else:
    quo = ''
  return sep, quo

def build_user_keys(user_key_list):
  user_key_dict = {}
  for row in user_key_list:
    user_key_dict[row['name']] = row['key']
  return user_key_dict