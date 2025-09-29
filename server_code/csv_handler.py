import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv

@anvil.server.callable
def read_file(fn):
  mBytes = fn.get_bytes()

  # Convert bytes to a string.
  mString = str(mBytes, "utf-8")
  #   app_tables.flights.get(uid=anvil.users.get_user()['uid'])['log_string'] = mString
  # Create a list of lines split on \n
  line_list = mString.split('\n')
  # we need to identify the account, and the line of the header
  for l in line_list:
    print(l)
  # header = line_list[0]
  # sep, quote = find_sep_quote(line_list)
  
  # the_csv = fn
  # with open(the_csv, newline='', encoding='utf-8') as csvfile:
  #   reader = csv.reader(csvfile)

  #   # Loop through the first 10 rows
  #   for i, row in enumerate(reader):
  #     print(row)
  #     if i >= 9:  # stop after 10 lines (0–9)
  #       break

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
