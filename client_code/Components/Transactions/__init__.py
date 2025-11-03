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
  def __init__(self,dash=False, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.load_me(dash)
    if dash:
      self.card_3.role = 'fixed-holder'
      self.card_header.visible = False
    else:
      self.card_3.role = 'fixed-holder-page'
    

  def load_me(self,dash,**event_args):
    fd,ld = self.date_me(dash)
    self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by("date",ascending=False),
                                                                  date=q.between(fd,ld,True,True))
    odd,i,o = True,0,0
    for trans in self.repeating_panel_1.get_components():
      if odd:
        trans.set_bg(True)
      else:
        trans.set_bg(False)
      odd = not odd
      if trans.item['amount'] < 0:
        o += trans.item['amount']
      else:
        i += trans.item['amount']
    self.inflow.text = "Inflow: R{a:.2f}".format(a=i/100)
    self.outflow.text = "Outflow: R{a:.2f}".format(a=o/100)
  
  def date_me(self,dash,**event_args):
    m,y = None,None
    if dash:
      m = date.today().month
      y = date.today().year
      days_in_month = calendar.monthrange(y, m)[1]
      return date(y,m,1),date(y,m,days_in_month)
    else:
      p = Global.PERIOD
      if p[0] + p[1] == 0:
        #we have a custom
        return Global.CUSTOM[0],Global.CUSTOM[1]
      else:
        m = p[0]
        y = p[1]
        days_in_month = calendar.monthrange(y, m)[1]
        return date(y,m,1),date(y,m,days_in_month)


