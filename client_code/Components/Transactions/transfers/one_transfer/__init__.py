from ._anvil_designer import one_transferTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .....Global import Transactions_Form
from ..... import Global


class one_transfer(one_transferTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.drop_down_1.items = Global.ACCOUNTS
    self.locked = False
    self.amount_zero = 0
    self.account_zero = ''
    # Any code you write here will run before the form opens.

  @handle("", "show")
  def form_show(self, **event_args):
    if self.item[1]:
      self.btn_lock.enabled = True 
    else:
      self.btn_lock.enabled = False
    self.fill_details()

  def fill_details(self,**event_args):
    d_a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[0]][0]['date']
    ac_a = self.account_zero = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[0]][0]['account']
    ac_a = [a for a in Global.ACCOUNTS if a[1] == ac_a][0][0]
    am_a = self.amount_zero = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[0]][0]['amount']
    am_a = am_a/100
    dir = ("From","to") if am_a < 0 else ("To","from")
    t = "{da} {aca} on {ada} for R {ama:.2f}, {db}:".format(da=dir[0],
                                                      aca=ac_a,
                                                      ada=d_a,
                                                      ama=am_a,
                                                      db=dir[1])
    self.label_1.text = t
    if am_a < 0:
      self.label_1.foreground = 'theme:Amount Negative'
    if self.item[1]:
      self.date_picker_1.date = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[1]][0]['date']
      self.drop_down_1.selected_value = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[1]][0]['account']
      a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[1]][0]['amount']
      a = a/100
      self.label_2.text = "R {amount:.2f}".format(amount=a)
      if a < 0:
        self.label_2.foreground = 'theme:Amount Negative'

  @handle('date_picker_1','change')
  @handle('drop_down_1','change')
  def change_item_one(self,**event_args):
    if self.date_picker_1.date and self.drop_down_1.selected_value:
      self.btn_lock.enabled = True
      amount = self.amount_zero * -1 / 100
      self.label_2.text = "R {a:.2f}".format(a=amount)
      if amount < 0:
        self.label_2.foreground = 'theme:Amount Negative'
      else:
        self.label_2.foreground = ''
    else:
      self.btn_lock.enabled = False
      self.label_2.text = ''
    
  @handle('btn_lock','click')
  @handle('btn_unlock','click')
  def status_update(self,**event_args):
    if self.btn_lock.visible:
      # we lock this down after checking it's ready to be locked down
      if self.label_2.text:
        # we are ready to lock
        self.locked = True
        self.column_panel_1.background = "#b2d8b2"
        self.btn_lock.visible = False
        self.btn_unlock.visible = True
    else:
      self.locked = False
      self.btn_lock.visible = True
      self.column_panel_1.background = '#FFCDC9'
      self.btn_unlock.visible = False
