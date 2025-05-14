import qrcode

def generate_placeholder_qr():
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data('placeholder_qr_code')
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    img.save('static/images/placeholder_qr.png')
    print('Placeholder QR code created')

if __name__ == '__main__':
    generate_placeholder_qr() 