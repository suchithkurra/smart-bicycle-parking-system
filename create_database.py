import sqlite3

DB_NAME = "bicycle_parking.db"

connection = sqlite3.connect(DB_NAME)
cursor = connection.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table' AND name = 'Users'
""")

table_exists = cursor.fetchone()

def create_users_table():
    cursor.execute("""
        CREATE TABLE Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            accessibility_need INTEGER NOT NULL DEFAULT 0
                CHECK (accessibility_need IN (0, 1))
        )
    """)


if not table_exists:
    create_users_table()
    print("New Users table created.")

else:
    cursor.execute("PRAGMA table_info(Users)")
    columns = [column[1] for column in cursor.fetchall()]

    required_columns = {
        "id", "user_id", "name", "email", "accessibility_need"
    }

    if not required_columns.issubset(set(columns)):
        cursor.execute("ALTER TABLE Users RENAME TO Users_old")

        create_users_table()

        cursor.execute("""
            INSERT INTO Users (
                user_id, name, email, accessibility_need
            )
            SELECT user_id, name, email, 0
            FROM Users_old
        """)

        cursor.execute("DROP TABLE Users_old")
        print("Existing user records migrated.")

    else:
        print("Users table already has the required columns.")

connection.commit()

cursor.execute("PRAGMA table_info(Users)")
print("\nUsers table structure:")
for column in cursor.fetchall():
    print(column)

cursor.execute("SELECT * FROM Users")
print("\nExisting users:")
for user in cursor.fetchall():
    print(user)

connection.close()
print("\nDatabase setup completed.")