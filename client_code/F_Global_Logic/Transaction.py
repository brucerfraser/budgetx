import anvil.server
from anvil import *
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import Global
import calendar
from datetime import date, datetime, timedelta

def work_transaction_data(mode,transaction):
  """
    CENTRAL LOGIC
    transaction is multi-purpose:is now a list of transactions, either from self.delete_list (Transactions form),
    mode_______________transaction_______________________
    add                one dict of new transaction
    delete_immediate   list of transaction ids to delete (use from a transfer double confirm)
    delete_confirm     list of transaction ids to delete (use from tranactions page, mulitple selected)
    reload             list of new transaction dictionaries
    update             one dict of transaction to be updated
    """
  if mode == 'add':
    Global.TRANSACTIONS.insert(0,transaction)
    app_tables.transactions.add_row(**transaction)
    Global.Transactions_Form.load_me(Global.Transactions_Form.dash)
  elif mode == 'delete_immediate':
    note = Notification("Deleting corresponding transfer",
                        timeout=None)
    note.show()
    anvil.server.call('delete_transactions',transaction)
    for id in transaction:
      for trans in Global.TRANSACTIONS:
        if trans['transaction_id'] == id:
          Global.TRANSACTIONS.remove(trans)
          break
    Global.Transactions_Form.load_me(Global.Transactions_Form.dash)
    note.hide()
  elif mode == 'delete_confirm':
    num = str(len(transaction)) + ' ' if len(transaction) > 1 else ''
    tra = 'transactions' if len(transaction) > 1 else 'transaction'
    m = "Are you sure you wish to delete the {n}highlighted {t}?".format(n=num,t=tra)
    if confirm(m,"Delete?",
                buttons=[("Delete",True),("Cancel",False)]):
      note = Notification("Deleting {n}{t}".format(n=num,t=tra),
                          timeout=None)
      note.show()
      anvil.server.call('delete_transactions',transaction)
      for id in transaction:
        for trans in Global.TRANSACTIONS:
          if trans['transaction_id'] == id:
            Global.TRANSACTIONS.remove(trans)
            break
      Global.Transactions_Form.load_me(Global.Transactions_Form.dash)
      note.hide()
  elif mode == 'reload':
    for new in transaction:
      if len([t for t in Global.TRANSACTIONS if t['hash'] == new['hash']]) == 0:
        #we have a new transaction
        new['notes'] = None
        new['category'] = None
        Global.TRANSACTIONS.append(new)
  elif mode == "update":
    acc = 'none_yet' if not transaction['account'] else transaction['account']
    transaction['hash'] = str(transaction['date'].day) + str(transaction['date'].month) + str(transaction['date'].year) + str(transaction['amount']) + acc
    app_tables.transactions.get(transaction_id=transaction['transaction_id']).update(**transaction)
    # force a local data update here
    for trans in Global.TRANSACTIONS:
      if trans['transaction_id'] == transaction['transaction_id']:
        trans.update(transaction)
        break
    
    
def date_me(dashboard_mode):
  m,y = None,None
  if dashboard_mode:
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