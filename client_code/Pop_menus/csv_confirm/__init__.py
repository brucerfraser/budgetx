from ._anvil_designer import csv_confirmTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
# from dateutil.parser import parse
from datetime import date, datetime

class csv_confirm(csv_confirmTemplate):
  def __init__(self,accounts,acc_id,ready,trans, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.changed = False
    self.trans = trans
    self.ready = ready
    dd_list = []
    for acc in accounts:
      dd_list.append((acc['acc_name'],acc['acc_id']))
    self.account_dd.items = dd_list
    if acc_id:
      self.account_dd.selected_value = acc_id
    else:
      self.changed = True
    if ready:
      i_list = [{'amount':'Amount','date':'Transaction Date',
                 'description':'Description'}]
      for i in range(0,3):
        try:
          i_list.append(ready[i])
        except:
          pass
      self.sample_trans.items = i_list
      hashes = []
      for re in ready:
        hashes.append(re['hash'])
      self.duplicate.text = "Of the {l} transactions loaded,\
 {d} are duplicates\
 and will be ignored""".format(l=len(ready),
            d=anvil.server.call('duplicate_check',hashes))
    else:
      self.sample_trans.items = [{'amount':'Amount','date':'Transaction Date',
                 'description':'Description'}]
      self.duplicate.text = "No transactions loaded yet"

  def confirm_click(self, **event_args):
    if self.account_dd.selected_value and len(self.ready) > 0:
      self.raise_event("x-close-alert", value=self.ready)
    else:
      self.raise_event("x-close-alert", value=None)

  def account_dd_change(self, **event_args):
    # will have to change ready etc here.
    if self.account_dd.selected_value:
      r,t = anvil.server.call('make_ready',account=self.account_dd.selected_value,
                       trans_list=self.trans)
      self.ready = r
      i_list = [{'amount':'Amount','date':'Transaction Date',
                 'description':'Description'}]
      for i in range(0,3):
        try:
          i_list.append(r[i])
        except:
          pass
      self.sample_trans.items = i_list
      hashes = []
      for re in r:
        hashes.append(re['hash'])
      self.duplicate.text = "Of the {l} transactions loaded,\
 {d} are duplicates\
 and will be ignored".format(l=len(r),
              d=anvil.server.call('duplicate_check',hashes))

  def cancel_click(self, **event_args):
    self.raise_event("x-close-alert",value=None)
