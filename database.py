import sqlite3
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent / "bicycle_parking.db"


def connect_to_database():
    return sqlite3.connect(DB_NAME)



def register_user(user_id, name, email, accessibility_need=False):
    connection = connect_to_database()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO Users (
                user_id, name, email, accessibility_need
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            name,
            email,
            int(accessibility_need)
        ))

        connection.commit()
        return True, "User registered successfully!"

    except sqlite3.IntegrityError:
        connection.rollback()
        return False, "User ID or email already exists."

    except sqlite3.Error as error:
        connection.rollback()
        return False, f"Database error: {error}"

    finally:
        cursor.close()
        connection.close()




def check_user_exists(user_id):
    connection = connect_to_database()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT 1 FROM Users WHERE user_id = ?",
        (user_id,)
    )

    exists = cursor.fetchone() is not None

    cursor.close()
    connection.close()

    return exists





def find_user(user_id):
    connection = connect_to_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, user_id, name, email, accessibility_need
        FROM Users
        WHERE user_id = ?
    """, (user_id,))

    user = cursor.fetchone()

    cursor.close()
    connection.close()

    return user


def get_all_users():
    connection = connect_to_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, user_id, name, email, accessibility_need
        FROM Users
    """)

    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return users




'''register_user(
    "USER003",
    "Test User 3",
    "test3@example.com",
    True
) '''       

if __name__ == "__main__":
    for user in get_all_users():
        print(user)
    

