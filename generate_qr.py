import qrcode
from io import BytesIO


def generate_qr(user_id):
    qr_image = qrcode.make(user_id)

    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    return qr_buffer