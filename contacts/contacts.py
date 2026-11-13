print()

def main():
    while True:
        choice = input("Menu (add, list, search, edit, delete, quit): ").strip().lower()
        if choice == "quit":
            break
        elif choice in ("add", "list", "search", "edit", "delete"):
            print(choice)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()