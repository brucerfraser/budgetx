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
    t = "Select or confirm a corresponding account for each of the {n} transactions:".format(n=len(self.transfer_list))
    self.label_2.text = t
    for pair in self.get_pairs():
      d_a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == pair[0]][0]['date']
      ac_a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == pair[0]][0]['account']
      ac_a = [a for a in Global.ACCOUNTS if a[1] == ac_a][0]
      am_a = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == pair[0]][0]['amount']
      if pair[1]:
        d_b = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == pair[0]][0]['date']
        ac_b = [t for t in Transactions_Form.all_transactions if t['transaction_id'] == pair[0]][0]['account']
        ac_b = [a for a in Global.ACCOUNTS if a[1] == ac_b][0]
      else:
        d_b = None
      dir = ("From","to") if am_a < 0 else ("To","from")
      if d_b:
        t = "{da} {aca} on {ada} for {ama}, {db} {acb} on {adb} for {amb}".format(da=dir[0],
                                                                                aca=ac_a,
                                                                                ada=d_a,
                                                                                ama=am_a,
                                                                                db=dir[1],
                                                                                acb=ac_b,
                                                                                adb=d_b,
                                                                                amb=-1*am_a)
      else:
        t = "{da} {aca} on {ada} for {ama}, {db} ...No pair found".format(da=dir[0],
                                                                          aca=ac_a,
                                                                          ada=d_a,
                                                                          ama=am_a,
                                                                          db=dir[1])
      self.column_panel_1.add_component(Label(text=t))

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