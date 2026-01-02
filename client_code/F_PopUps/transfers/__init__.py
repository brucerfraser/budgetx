from ._anvil_designer import transfersTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic.Global import Transactions_Form
from ...F_Global_Logic import Global
from datetime import date, timedelta


class transfers(transfersTemplate):
  def __init__(self,transfer_list, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.transfer_list = transfer_list
    self.return_list = []
    

  @handle("", "show")
  def form_show(self, **event_args):
    self.label_2.text = self.intro_write()
    self.repeating_panel_1.items = self.get_pairs()

  def intro_write(self,**event_args):
    t = "Select or confirm a corresponding account for each of the {n} transactions.\n".format(n=len(self.transfer_list))
    t += """
    Use the green lock button 🔒 to confirm the transfer details. Green background = locked and ready.\n
    Use the red unlock button 🔓 to ignore the transaction for transfer. Red background = ignored.
    """
    self.return_list = []
    return t

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
        if len([t for t in Global.TRANSACTIONS if t['amount'] == a_opp and d_bef <= t['date'] and d_aft >= t['date']]) == 1:
          # we have a match
          pairs.append((t_id,[t for t in Global.TRANSACTIONS if t['amount'] == a_opp and d_bef <= t['date'] and d_aft >= t['date']][0]['transaction_id']))
        else:
          pairs.append((t_id,None))
    return pairs

  def extract_details(self,trans_id,**event_args):
    try:
      amount = [t for t in Global.TRANSACTIONS if t['transaction_id'] == trans_id][0]['amount']
      date = [t for t in Global.TRANSACTIONS if t['transaction_id'] == trans_id][0]['date']
      return amount,date
    except Exception as e:
      print(self.transfer_list)

  @handle('btn_cancel','click')
  @handle('btn_ok','click')
  def tally_up(self,**event_args):
    if event_args['sender'].text == 'cancel':
      if self.btn_ok.text == 'ok':
        self.raise_event('x-close-alert',value=False)
      else:
        self.btn_ok.text = 'ok'
        self.label_2.background = ''
        self.label_2.foreground = ''
        self.label_2.text = self.intro_write()
    elif event_args['sender'].text == 'ok':
      #tally
      for transfer in self.repeating_panel_1.get_components():
        if transfer.locked:
          partner = {'exists':transfer.item[1] != None,
                    'trans_one':transfer.item[0],'trans_two':None,
                    'amount_two':transfer.amount_zero * -1,
                    'date_two':transfer.date_picker_1.date,
                    'account_two':transfer.drop_down_1.selected_value,
                    'account_one':transfer.account_zero}
          if partner['exists']:
            partner['trans_two'] = transfer.item[1]
          self.return_list.append(partner)
      t,c = 0,0
      for l in self.return_list:
        t += 1
        c += 0 if l['exists'] else 1
      msg = "You have {t} transfers ready to save".format(t=t)
      if c > 0:
        msg += ", of which {c} will create new corresponding transactions. Confirm?".format(c=c)
      else:
        msg += ", Confirm?"
      self.label_2.text = msg
      self.label_2.background = '#F7B980'
      self.label_2.foreground = 'black'
      self.btn_ok.text = 'confirm'
    elif event_args['sender'].text == 'confirm':
      self.raise_event('x-close-alert',value=self.return_list)