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
    # Any code you write here will run before the form opens.

  @handle("", "show")
  def form_show(self, **event_args):
    if self.item[1]:
      self.btn_lock.enabled = True 
    else:
      self.btn_lock.enabled = False
    d_a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[0]][0]['date']
    ac_a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[0]][0]['account']
    ac_a = [a for a in Global.ACCOUNTS if a[1] == ac_a][0][0]
    am_a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[0]][0]['amount']
    am_a = am_a/100
    dir = ("From","to") if am_a < 0 else ("To","from")
    t = "{da} {aca} on {ada} for R {ama:.2f}, {db}:".format(da=dir[0],
                                                      aca=ac_a,
                                                      ada=d_a,
                                                      ama=am_a,
                                                      db=dir[1])
    self.label_1.text = t
    if self.item[1]:
      self.date_picker_1.date = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[1]][0]['date']
      self.drop_down_1.selected_value = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[1]][0]['account']
      a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == self.item[1]][0]['amount']
      a = a/100
