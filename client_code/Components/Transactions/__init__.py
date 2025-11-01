from ._anvil_designer import TransactionsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global
import calendar
from datetime import date

class Transactions(TransactionsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    p = Global.PERIOD
    days_in_month = calendar.monthrange(p[1], p[0])[1]
    last_day = date(p[1], p[0], days_in_month)
    first_day = date(p[1], p[0], 1)
    print(days_in_month,last_day, first_day)
    self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by("date",ascending=False),
                                                                 date=q.between(first_day,last_day,True,True))
    odd = True
    for trans in self.repeating_panel_1.get_components():
      if odd:
        trans.set_bg(True)
      else:
        trans.set_bg(False)
      odd = not odd
    # Any code you write here will run before the form opens.


