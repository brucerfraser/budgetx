from ._anvil_designer import one_transactionTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .... import Global
from datetime import date, datetime



class one_transaction(one_transactionTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.dd_list = Global.ACCOUNTS
    self.init_components(**properties)
    self.date.tag = 'date'
    self.account_name = '
    for f in self.dd_list:
      if self.item['account'] == f[1]:
        self.account_name = f[0]
        break
    self.account.text = self.account_name
    
  def set_bg(self,odd,**event_args):
    objs = [self.account,self.date,self.amount,self.category,self.description,self.card_1,
           self.card_2,self.card_3,self.card_4,self.card_5,self.card_6]
    for obj in objs:
      if odd:
        obj.background = "#2B383E"
      else:
        obj.background = "#595A3B"

  def click_date(self, **event_args):
    self.date_picker_1.visible = True
    self.date_picker_1.focus()
    self.date.visible = False

  def date_picker_1_change(self, **event_args):
    self.parent.items = app_tables.transactions.search()
    self.date_picker_1.visible = False
    self.date.visible = True

  def click_account(self, **event_args):
    self.drop_down_1.visible = True
    self.drop_down_1.focus()
    self.account.visible = False

  def drop_down_1_change(self, **event_args):
    for f in self.dd_list:
      if self.item['account'] == f[1]:
        self.account_name = f[0]
        break
    self.account.text = self.account_name
    self.account.visible = True
    self.drop_down_1.visible = False
    # have to change the hash here
    self.item['hash'] = str(self.item['date'].day) + str(self.item['date'].month) + str(self.item['date'].year)+ str(self.item['amount']) + self.item['account']

  
