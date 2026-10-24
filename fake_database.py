# Temporary database for our prototype

users = [
    {
        "user_id": "USER001",
        "name": "Kaleab",
        "email": "kaleab@example.com"
    }
]


def add_user(name, email):
    user_id = f"USER{len(users) + 1:03}"

    new_user = {
        "user_id": user_id,
        "name": name,
        "email": email
    }

    users.append(new_user)

    return new_user


new_user = add_user("Sara", "sara@example.com")

print(new_user)
print(users)