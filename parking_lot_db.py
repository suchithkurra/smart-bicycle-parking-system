import sqlite3

connection = sqlite3.connect('bicyle_parking.db')

cursor = connection.cursor()

create_table_parking_spots = """CREATE TABLE parking_spots (
    spot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_x INTEGER NOT NULL,
    spot_y INTEGER NOT NULL,
    accessible INTEGER NOT NULL DEFAULT 0,
    available INTEGER NOT NULL DEFAULT 1)"""

create_table_bookings = """CREATE TABLE bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    spot_id INTEGER NOT NULL,
    booking_time DATETIME NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    booking_status TEXT NOT NULL DEFAULT 'WAITING',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (spot_id) REFERENCES parking_spots(spot_id))"""

cursor.execute(create_table_parking_spots)
cursor.execute(create_table_bookings)

parking_spots = []

for i in range(1, 101):
    if i <= 10:
        accessible = 1
    else:
        accessible = 0

    parking_spots.append((i, i, accessible))

cursor.executemany("""INSERT INTO parking_spots (spot_x, spot_y, accessible) VALUES (?, ?, ?)""", parking_spots)

cursor.execute("SELECT * FROM parking_spots")
results = cursor.fetchall()
print(results)

connection.commit()
connection.close()



