from ._anvil_designer import edit_transactionTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date, timedelta
import time
from ...F_Global_Logic.Global import Transactions_Form
from ...F_Global_Logic import Global, Transaction


class edit_transaction(edit_transactionTemplate):
  def __init__(self, new_trans, **properties):
    # Set Form properties and Data Bindings.
    self.item = new_trans
    self.holder = ""
    self.init_components(**properties)

  @handle("", "show")
  def form_show(self, **event_args):
    self.drop_down_1.items = Global.ACCOUNTS
    self.dd_transfer.items = Global.ACCOUNTS
    self.categorise()

  @handle("btn_cancel", "click")
  @handle("btn_save", "click")
  def tally_up(self, **event_args):
    if event_args["sender"].text == "cancel":
      self.raise_event("x-close-alert", value=None)
    elif event_args["sender"].text == "save":
      if self.cp_transfer.visible and self.cp_transfer.background == "#b2d8b2":
        # we can save
        self.save_and_send()
        self.raise_event("x-close-alert", value=None)
      elif not self.cp_transfer.visible:
        # we can save
        self.save_and_send()
        self.raise_event("x-close-alert", value=None)
      else:
        # flash a bit
        on = False
        for i in range(0, 5):
          self.cp_transfer.background = "#FFCDC9" if on else ""
          on = not on
          time.sleep(0.2)
        self.cp_transfer.background = "#FFCDC9"
    elif event_args["sender"].text == "save and add":
      # save, clear, and wait
      if self.cp_transfer.visible and self.cp_transfer.background == "#b2d8b2":
        # we can save
        self.save_and_send()
        self.refresh_form()
      elif not self.cp_transfer.visible:
        # we can save
        self.save_and_send()
        self.refresh_form()
      else:
        # flash a bit
        on = False
        for i in range(0, 5):
          self.cp_transfer.background = "#FFCDC9" if on else ""
          on = not on
          time.sleep(0.2)
        self.cp_transfer.background = "#FFCDC9"

  def save_and_send(self, **event_args):
    self.item["amount"] = self.item["amount"] * 100
    self.item["hash"] = (
      str(self.item["date"].day)
      + str(self.item["date"].month)
      + str(self.item["date"].year)
      + str(self.item["amount"])
      + str(self.item["account"])
    )
    Transaction.work_transaction_data("add", self.item)
    # was this a transfer? Need to make a new transaction if so.
    if self.item["category"] == "ec8e0085-8408-43a2-953f-ebba24549d96":
      hash_new = (
        str(self.item["date"].day)
        + str(self.item["date"].month)
        + str(self.item["date"].year)
        + str(-1 * self.item["amount"])
        + self.dd_transfer.selected_value
      )
      for g in Global.ACCOUNTS:
        # print(g[0],g[1],g[1]==transfer['account_one'])
        if g[1] == self.item["account"]:
          acc_name = g[0]
          break
      f_t = "From" if self.item["amount"] < 0 else "To"
      new_trans = {
        "date": self.item["date"],
        "amount": -1 * self.item["amount"],
        "description": "{f} {a}".format(f=f_t, a=acc_name),
        "category": "ec8e0085-8408-43a2-953f-ebba24549d96",
        "account": self.dd_transfer.selected_value,
        "notes": "",
        "hash": hash_new,
        "transaction_id": Global.new_id_needed(),
        "transfer_account": self.item["account"],
      }
      Transaction.work_transaction_data("add", new_trans)

  def refresh_form(self, **event_args):
    date_new = date.today()
    hash_new = (
      str(date_new.day) + str(date_new.month) + str(date_new.year) + "0" + "none_yet"
    )
    id_new = Global.new_id_needed()
    self.item = {
      "date": date_new,
      "amount": 0,
      "description": "",
      "category": None,
      "account": None,
      "notes": "",
      "hash": hash_new,
      "transaction_id": id_new,
      "transfer_account": None,
    }
    self.refresh_data_bindings()
    self.categorise()

  def categorise(self, **event_args):
    names_list = sorted(list(map(lambda x: x["display"], Global.CATEGORIES.values())))
    names_list.insert(0, "None")
    self.autocomplete_1.suggestions = names_list
    self.autocomplete_1.text = ""
    self.autocomplete_1.background = ""
    self.autocomplete_1.foreground = ""

  @handle("autocomplete_1", "pressed_enter")
  @handle("autocomplete_1", "suggestion_clicked")
  @handle("autocomplete_1", "lost_focus")
  def category_choose(self, **event_args):
    self.item["category"] = next(
      (
        k
        for k, v in Global.CATEGORIES.items()
        if v.get("display") == self.autocomplete_1.text
      ),
      None,
    )
    if self.item["category"]:
      Global.smarter(
        first=False, update=(self.item["category"], self.item["description"])
      )
      self.autocomplete_1.background = Global.CATEGORIES[self.item["category"]][
        "colour"
      ]
      self.autocomplete_1.foreground = "theme:Surface"
    else:
      self.categorise()
    self.update_transfer()

  @handle("drop_down_1", "change")
  @handle("text_box_1", "lost_focus")
  @handle("date_picker_1", "change")
  def update_transfer(self, **event_args):
    if self.item["category"] == "ec8e0085-8408-43a2-953f-ebba24549d96":
      # we have a transfer
      self.holder = self.txt_description.text
      acc_name = "<No Account>"
      acc_name_two = "<No Account>"
      for g in Global.ACCOUNTS:
        if g[1] == self.item["account"]:
          acc_name = g[0]
        if g[1] == self.dd_transfer.selected_value:
          acc_name_two = g[0]
      f_t = "From" if self.item["amount"] < 0 else "To"
      t_f = "From" if f_t == "To" else "To"
      dte = self.item["date"] if self.item["date"] else "<No Date>"
      self.lbl_tfer_detail.text = "{f} {a} on {d} {t}:".format(
        f=f_t, a=acc_name, d=dte, t=t_f
      )
      self.lbl_tfer_amount.text = "R {ama:.2f}".format(ama=-1 * self.item["amount"])
      self.txt_description.text = "{f} {a}".format(f=t_f, a=acc_name_two)
      self.item["description"] = self.txt_description.text
      self.lbl_tfer_amount.foreground = (
        "theme:Amount Negative" if self.item["amount"] > 0 else "theme:Primary"
      )
      self.lbl_tfer_detail.foreground = (
        "theme:Amount Negative" if self.item["amount"] < 0 else "theme:Primary"
      )
      self.cp_transfer.visible = True
    else:
      self.item["description"] = self.txt_description.text = self.holder
      self.lbl_tfer_detail.text = ""
      self.lbl_tfer_amount.text = ""
      self.dd_transfer.selected_value = None
      self.cp_transfer.visible = False

  @handle("dd_transfer", "change")
  def tfer_account(self, **event_args):
    if self.dd_transfer.selected_value:
      self.cp_transfer.background = "#b2d8b2"
      acc_name = ""
      for g in Global.ACCOUNTS:
        if g[1] == self.dd_transfer.selected_value:
          acc_name = g[0]
          break
      f_t = "From" if self.item["amount"] > 0 else "To"
      self.item["description"] = self.txt_description.text = "{f} {a}".format(
        f=f_t, a=acc_name
      )
    else:
      self.cp_transfer.background = "#FFCDC9"
