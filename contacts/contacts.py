import json
import os

FILE_NAME = "contacts.json"


def safe_input(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def load_contacts():
    if not os.path.exists(FILE_NAME):
        return []
    try:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_contacts(contacts):
    try:
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2)
    except OSError:
        print("Error saving contacts.")


def add_contact(contacts):
    name = safe_input("Name: ")
    phone = safe_input("Phone: ")
    email = safe_input("Email: ")
    if not name or not phone or not email:
        print("All fields are required.")
        return
    contacts.append({"name": name, "phone": phone, "email": email})
    save_contacts(contacts)
    print("Contact added.")


def list_contacts(contacts):
    if not contacts:
        print("No contacts found.")
        return
    for c in contacts:
        print(f"{c.get('name', '')} | {c.get('phone', '')} | {c.get('email', '')}")


def search_contacts(contacts):
    query = safe_input("Search name: ").lower()
    if not query:
        print("Search query cannot be empty.")
        return
    results = [c for c in contacts if query in c.get("name", "").lower()]
    if not results:
        print("No matching contacts.")
        return
    for c in results:
        print(f"{c.get('name', '')} | {c.get('phone', '')} | {c.get('email', '')}")


def edit_contact(contacts):
    name = safe_input("Name to edit: ").lower()
    if not name:
        print("Name cannot be empty.")
        return
    for c in contacts:
        if c.get("name", "").lower() == name:
            new_name = safe_input(f"New name ({c['name']}): ") or c["name"]
            new_phone = safe_input(f"New phone ({c['phone']}): ") or c["phone"]
            new_email = safe_input(f"New email ({c['email']}): ") or c["email"]
            c["name"] = new_name
            c["phone"] = new_phone
            c["email"] = new_email
            save_contacts(contacts)
            print("Contact updated.")
            return
    print("Contact not found.")


def delete_contact(contacts):
    name = safe_input("Name to delete: ").lower()
    if not name:
        print("Name cannot be empty.")
        return
    for i, c in enumerate(contacts):
        if c.get("name", "").lower() == name:
            del contacts[i]
            save_contacts(contacts)
            print("Contact deleted.")
            return
    print("Contact not found.")


def main():
    contacts = load_contacts()
    while True:
        choice = safe_input("Menu (add, list, search, edit, delete, quit): ").lower()
        if choice == "add":
            add_contact(contacts)
        elif choice == "list":
            list_contacts(contacts)
        elif choice == "search":
            search_contacts(contacts)
        elif choice == "edit":
            edit_contact(contacts)
        elif choice == "delete":
            delete_contact(contacts)
        elif choice == "quit":
            break
        else:
            print("Invalid choice. Choose add, list, search, edit, delete, or quit.")


if __name__ == "__main__":
    main()