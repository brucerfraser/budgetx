from ._anvil_designer import remove_transferTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .... import Global



class remove_transfer(remove_transferTemplate):
  def __init__(self,t_id, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    self.lbl = """
    You are changing a transfer transaction with a corresponding transaction for {R:.2f} on {D} from {A}.
    Would you like to delete this corresponding transaction or change its category to None?
    """
    the_one = [t for t in Global.Transactions_Form.all_transactions if t['transaction_id'] == t_id][0]
    r = the_one['amount'] / 100
    a = ''
    for g in Global.ACCOUNTS:
      if g[1] == the_one['account']:
        a = g[0]
        break
    d = the_one['date']
    self.label_2.text = self.lbl.format(R=r,A=a,D=d)

  @handle('btn_none','click')
  @handle('btn_delete','click')
  def answer(self,**event_args):
    if event_args['sender'].text == "none":
      self.raise_event('x-close-alert',value=False)
    else:
      self.raise_event('x-close-alert',value=True)
    
