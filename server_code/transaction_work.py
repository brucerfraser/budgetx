import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from dateutil.parser import parse
from datetime import date, datetime

@anvil.server.callable
def get_hash_date(date):
  return str(parse(date).day) + str(parse(date).month) + str(parse(date).year)

@anvil.server.callable
def clear_cats():
  for row in app_tables.transactions.search():
    row['category'] = None