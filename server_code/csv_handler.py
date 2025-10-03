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

@anvil.server.callable
def read_file(fn):
  mBytes = fn.get_bytes()

  # Convert bytes to a string.
  mString = str(mBytes, "utf-8")
  #   app_tables.flights.get(uid=anvil.users.get_user()['uid'])['log_string'] = mString
  # Create a list of lines split on \n
  line_list = mString.split('\n')
  # we need to identify the account, and the line of the header
  header_triggers = ["date","amount","description","details","debits","credits","balance"]
  r = 0
  for l in line_list:
    r += 1
    triggers = 0
    for t in header_triggers:
      if t in l.lower():
        triggers += 1
    # print(l)
    if triggers > 2:
      break
  print(r,line_list[r-1])
  key_words = header_words(line_list,r-1)
  found, acc_id = account_finder(key_words)
  print(found,acc_id)
  
  print(line_list[6])
  sep, quote = find_sep_quote(line_list)
  # print(sep,quote)
  
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