import random
import string
import os

TITLES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PREVIOUSLY_GENERATED_TITLES.txt")

def load_titles():
    """Load previously generated titles from the reference file."""
    titles = set()
    if os.path.exists(TITLES_FILE):
        with open(TITLES_FILE, "r") as f:
            for line in f:
                titles.add(line.strip())
    return titles

def save_title(title):
    """Append a new title to the reference file."""
    with open(TITLES_FILE, "a") as f:
        f.write(title + "\n")

generated_titles = load_titles()

def generate_title():
    """
    Generate a random 10-character composition title using uppercase ASCII letters and numbers.
    Ensures no duplicate titles are generated across all sessions on this machine.

    I don't like titles, they are a distraction.
    This function generates a random title to satisfy the requirement.
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        title = ''.join(random.choice(characters) for _ in range(10))
        if title not in generated_titles:
            generated_titles.add(title)
            save_title(title)
            return title

def view_titles():
    """Display all previously generated titles."""
    if not generated_titles:
        print("\nNo titles have been generated yet.")
    else:
        print("\nPreviously Generated Titles")
        for i, title in enumerate(sorted(generated_titles), 1):
            print(f"  {i}. {title}")
        print(f"Total: {len(generated_titles)} titles")

def main():
    """Main interactive loop."""
    new_title = generate_title()
    print(f"\nGenerated Title: {new_title}")
    
    while True:
        print("\nOptions:")
        print("  1: Generate another title")
        print("  2: View all previously generated titles")
        print("  3: Exit")
        
        choice = input("\nSelect an option (1-3): ").strip()
        
        if choice == "1":
            new_title = generate_title()
            print(f"\nGenerated Title: {new_title}")
        elif choice == "2":
            view_titles()
        elif choice == "3":
            print("Exiting program.")
            break
        else:
            print("Invalid option. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()