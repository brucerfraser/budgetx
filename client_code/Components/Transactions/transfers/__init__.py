from ._anvil_designer import transfersTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ....Global import Transactions_Form
from .... import Global
from datetime import date, timedelta


class transfers(transfersTemplate):
  def __init__(self,transfer_list, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.transfer_list = transfer_list

  @handle("", "show")
  def form_show(self, **event_args):
    print(self.transfer_list)
    t = "Select or confirm a corresponding account for each of the {n} transactions:".format(n=len(self.transfer_list))
    self.label_2.text = t
    self.repeating_panel_1.items = self.get_pairs()
      

  def get_pairs(self, **event_args):
    # build a transfer pair list based on opposite but equal amounts, same dates ± 2
    pairs = []
    for t_id in self.transfer_list:
      # first check if this id already in pairs
      if not len([p for p in pairs if p[1] == t_id]) > 0:
        # t_id has no match yet
        a,d = self.extract_details(t_id)
        a_opp = -1 * a
        d_bef = d - timedelta(days=2)
        d_aft = d + timedelta(days=2)
        if len([t for t in Transactions_Form.all_transactions if t['amount'] == a_opp and d_bef <= t['date'] and d_aft >= t['date']]) == 1:
          # we have a match
          pairs.append((t_id,[t for t in Transactions_Form.all_transactions if t['amount'] == a_opp and d_bef <= t['date'] and d_aft >= t['date']][0]['transaction_id']))
        else:
          pairs.append((t_id,None))
    return pairs

  def extract_details(self,trans_id,**event_args):
    amount = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == trans_id][0]['amount']
    date = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == trans_id][0]['date']
    return amount,date