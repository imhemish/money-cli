# Constant definitions --------------
INCOME_TYPE=0
EXPENSE_TYPE=1
REPEAT_NEVER=0
REPEAT_DAILY=1
REPEAT_WEEKLY=2
REPEAT_MONTHLY=3
REPEAT_QUARTERLY=4
REPEAT_YEARLY=5
REPEAT_BIYEARLY=6
script_name = 'savepenses'
# -----------------------------------

# Imports ----------------------------------
import pathlib
import datetime
import sqlite3
from typing import Optional, Union
# -------------------------------------------

# Exceptions --------------------------------
class NmoneyFileNotFound(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
# --------------------------------------------
 
# Today in ISO format ------------------------
today = str(datetime.date.today())
# ---------------------------------------------

# ---------------------------------------------
# Argument Parsing
import sys
from argparse import ArgumentParser

ap = ArgumentParser(description="A CLI program for NickvisionMoney")

ap.add_argument("--file", '-f', required=True, nargs=1, metavar='/path/to/file', help="Account file to use")

ap.add_argument("--income", '-i', required=False, action='store_true', help="Income Transaction.")

ap.add_argument("--expense", '-e', required=False, action='store_true', help="Expense Transaction.")

ap.add_argument("--amount", '-a', required=False, nargs=1, metavar='<amount>', help="Amount")

ap.add_argument("--comment", '-c', required=False, nargs=1, metavar='<description>', help="Include a description while making the transaction.")

ap.add_argument("--group", '-g', action='store_true', help="Group")

ap.add_argument("--transaction", '-t', action='store_true', help="Transaction")

ap.add_argument("--date", '-d', required=False, nargs=1, metavar='1970-01-01', help="Use this specified date instead of default today.")

ap.add_argument("--balance", '-b', required=False, action='store_true', help="Show current balance.")

ap.add_argument("--list", '-l', required=False, action='store_true', help='List all transactions')

ap.add_argument("--delete", required=False, metavar='<id>')

ap.add_argument("--new", '-n', action='store_true', help="New transaction/group")

ap.add_argument("--update", '-u', action='store_true', help="Update transaction/group")

#args = ap.parse_args()
#----------------------------------------------

# ----------------------------------------------
# Implementing warn with STDERR
def warn(message) -> None:
    sys.stderr.write("{}: {} \n".format(script_name, message))
# -------------------------------------------------
print(today)
class Transaction:
    def __init__(self, id:int, trans_type:int, repeat:int, amount:int, date: str=today, description: Union[str, None]=None, gid: Optional[int]=None) -> None:
        self.id = id
        self.date = date
        self.description = description
        self.trans_type = trans_type
        self.repeat = repeat
        self.amount = amount
        self.gid = gid
    
    def __dict__(self):
        return {"id": self.id, "date": self.date, "description": self.description, "type": self.trans_type, "repeat": self.repeat, "amount": self.amount, "gid": self.gid}
    
    def __str__(self):
        return str(self.__dict__())

class Group:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description
    
    def get_total(self, account):
        cursor: sqlite3.Cursor = account.conn.execute("SELECT COALESCE(SUM(IIF(t.type=1, -t.amount, t.amount)), 0) FROM groups g LEFT JOIN transactions t ON t.gid = g.id WHERE g.id=1 GROUP BY g.id;")
        return cursor.fetchone()[0]
    
    def __dict__(self):
        return {"id": self.id, "name": self.name, "description": self.description}

    def __str__(self):
        return str(self.__dict__())


class Account:
    def __init__(self, file) -> None:
        path = pathlib.Path(file)
        if not (path.exists() and path.is_file() and (path.suffix == ".nmoney")):
            return NmoneyFileNotFound("File does not exist or is not a Nmoney file: {}".format(file))
        
        self.conn = sqlite3.connect(file)

        self.conn.execute("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, name TEXT, description TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, date TEXT, description TEXT, type INTEGER, repeat INTEGER, amount TEXT, gid INTEGER)")

        # To support older versions
        try:
            self.conn.execute("ALTER TABLE transactions ADD COLUMN gid INTEGER")
        except:
            pass


        self.conn.commit()
    
    @property
    def groups(self) -> list[Group]:
        cursor = self.conn.execute("SELECT * FROM groups")
        groups_list = cursor.fetchall()
        groups = []
        for i in groups_list:
            groups.append(Group(i[0], i[1], i[2]))
        return groups
    
    @property
    def transactions(self) -> list[Transaction]:
        cursor = self.conn.execute("SELECT * FROM transactions")
        transactions_list = cursor.fetchall()
        transactions = []
        for i in transactions_list:
            transactions.append(Transaction(i[0], i[3], i[4], i[5], i[1], i[2]))
        return transactions
    
    @property
    def income(self):
        income = 0
        for transaction in self.transactions:
            if transaction.trans_type == INCOME_TYPE:
                income += transaction.amount
        return income
    
    @property
    def expense(self):
        expense = 0
        for transaction in self.transactions:
            if transaction.trans_type == EXPENSE_TYPE:
                income += transaction.amount
        return expense
    
    @property
    def total(self):
        return self.income-self.expense
    
    @property
    def next_available_transaction_id(self) -> int:
        ids = []
        for transaction in self.transactions:
            ids.append(transaction.id)
        ids.sort()
        return ids[-1]+1
    
    @property
    def next_available_group_id(self) -> int:
        ids = []
        for group in self.tgroups:
            ids.append(group.id)
        ids.sort()
        return ids[-1]+1

    def add_group(self, group: Group) -> None:
        self.conn.execute("INSERT INTO groups (id, name, description) VALUES ({}, '{}', '{}')".format(group.id, group.name, group.description))
        self.conn.commit()
    
    def update_group(self, group: Group) -> None:
        self.conn.execute("UPDATE groups SET name = '{}', description = '{}' WHERE id = {}".format(group.name, group.description, group.id))
        self.conn.commit()
    
    def delete_group(self, group: Group):
        self.conn.execute("DELETE FROM groups WHERE id ="+str(group.id))
        self.conn.commit()
    
    def add_transaction(self, transaction: Transaction) -> None:
        if transaction.gid == None:
            gid = 'NULL'
        else:
            gid = transaction.gid
        self.conn.execute("INSERT INTO transactions (id, date, description, type, repeat, amount, gid) VALUES ({}, '{}', '{}', {}, {}, {}, {})".format(transaction.id, transaction.date, transaction.description, transaction.trans_type, transaction.repeat, transaction.amount, gid))
        self.conn.commit()
    
    def update_transaction(self, transaction: Transaction) -> None:
        self.conn.execute("UPDATE transactions SET date = '{}', description = '{}', type = {}, repeat = {}, amount = {}, gid = {} WHERE id = {}".format(transaction.date, transaction.description, transaction.trans_type, transaction.repeat, transaction.amount, transaction.gid, transaction.id))
        self.conn.commit()
    
    def delete_transaction(self, transaction: Transaction):
        self.conn.execute("DELETE FROM transactions WHERE id ="+str(transaction.id))
        self.conn.commit()

# Main -------------------------------------------------

"""if args.clear == True:
    q = input("Do you really want to clear out all transactions? (y/n): ")
    if q.lower() in ['yes', 'no', 'y', 'n']:
        warn("Clearing out all transactions on request")
        configs = read_config(default_config, script_name)
        configs['transactions'] = default_config['transactions']
        write_config(configs, script_name)
    else:
        warn("Cancelled clearing out all transactions as confirmation was not provided") """

def main(args):
    pass
if __name__ == '__main__':
    main(args)
