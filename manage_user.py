
import sqlite3
import nd.db
import sys
import getpass
from argparse import ArgumentParser

parser = ArgumentParser(description='An utility to create user accounts.')
parser.add_argument("-n", "--new-user", type=str, help="Create a new user or update his password", required=False)
parser.add_argument("-r", "--delete-user", type=str, help="Delete a user", required=False)
parser.add_argument("-d", "--db", type=str, default="newspapers", help="The database used to store metadata")

options = parser.parse_args()

if bool(options.delete_user) == bool(options.new_user):
  parser.print_help()
  sys.exit(0)

db_name = '%s.db' % options.db
try:
    ndb = sqlite3.connect(db_name)
    db = nd.db.DB(ndb)
    if options.new_user:
        newpassword = getpass.getpass('Password:')
        db.add_user(options.new_user, newpassword)
        print("This user has been created/updated")
    else:
        db.delete_user(options.delete_user)
        print("This user has been deleted")

except (nd.db.DBException, sqlite3.DatabaseError) as e:
  print(e, file=sys.stderr)

