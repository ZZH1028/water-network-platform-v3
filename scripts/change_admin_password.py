from getpass import getpass
from services.auth_service import create_or_update_user
username=input("Username [admin]: ").strip() or "admin"
password=getpass("New password: ")
role=input("Role [管理员]: ").strip() or "管理员"
create_or_update_user(username,password,role)
print("User updated.")
