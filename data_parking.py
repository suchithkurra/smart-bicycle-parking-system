import sqlite3
import datetime


class parking_lot:
    def __init__(self, db_name="bicyle_parking.db"):
        self.db_name = db_name

    def create_booking(self, user_id, spot_id, booking_time, start_time, end_time):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT available FROM parking_spots WHERE spot_id = ?", (spot_id,))
            spot = cursor.fetchone()

            if spot is None or spot[0] == 0:
                return None

            cursor.execute("INSERT INTO bookings (user_id, spot_id, booking_time, start_time, end_time) VALUES (?, ?, ?, ?, ?)", (user_id, spot_id, booking_time, start_time, end_time))
            booking_id = cursor.lastrowid
            connection.commit()
            return booking_id

        except sqlite3.Error:
            connection.rollback()
            return None

        finally:
            connection.close()

    def update_booking_status(self, booking_id, updated_status):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()

        try:
            cursor.execute("UPDATE bookings SET booking_status = ? WHERE booking_id = ?", (updated_status, booking_id))
            connection.commit()
            return cursor.rowcount > 0

        except sqlite3.Error:
            connection.rollback()
            return False

        finally:
            connection.close()

    def get_user_bookings(self, user_id):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()

        try:
            cursor.execute("""SELECT booking_id, user_id, spot_id, booking_time, start_time, end_time, booking_status FROM bookings WHERE user_id = ?""", (user_id,))
            return cursor.fetchall()

        except sqlite3.Error:
            return []

        finally:
            connection.close()

    def get_parking_lot_info(self):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT spot_id, spot_x, spot_y, accessible, available FROM parking_spots")
            return cursor.fetchall()

        except sqlite3.Error:
            return []

        finally:
            connection.close()


def main():
    parking = parking_lot()

    spots = parking.get_parking_lot_info()
    print("Parking spots:", len(spots))
    print(spots[:5])

    now = datetime.datetime.now()
    booking_time = now.strftime("%Y-%m-%d %H:%M:%S")
    start_time = (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    end_time = (now + datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

    booking_id = parking.create_booking(1, 11, booking_time, start_time, end_time)
    print("New booking:", booking_id)

    if booking_id is not None:
        updated = parking.update_booking_status(booking_id, "CONFIRMED")
        print("status updated:", updated)

    bookings = parking.get_user_bookings(1)
    print("bookings for userid 1:", bookings)


if __name__ == "__main__":
    main()