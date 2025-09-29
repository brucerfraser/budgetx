import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv

@anvil.server.callable
def read_file():
  the_csv = tables.app_tables.test_csv.get(name="discovery")['file']
  with open(the_csv, newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)

    # Loop through the first 10 rows
    for i, row in enumerate(reader):
      print(row)
      if i >= 9:  # stop after 10 lines (0–9)
        break
