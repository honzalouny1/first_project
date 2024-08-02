import streamlit as st
from fpdf import FPDF, HTMLMixin
import base64
import qrcode
from io import BytesIO
import tempfile
import re

def convert_to_iban(account_number, bank_code):
    country_code = 'CZ'
    account_number_padded = account_number.zfill(16)
    bban = bank_code + account_number_padded
    bban_numeric = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in bban)
    checksum_numeric = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in country_code) + '00'
    checksum = 98 - (int(bban_numeric + checksum_numeric) % 97)
    return f"{country_code}{str(checksum).zfill(2)}{bban}"

class PDF(FPDF, HTMLMixin):
    def header(self):
        # Set background color
        self.set_fill_color(240, 248, 255)  # Light blue
        self.rect(0, 0, 210, 297, 'F')  # A4 size page
        self.set_y(10)

def generate_invoice(invoice_data):
    pdf = PDF()
    pdf.add_page()

    # Add font
    pdf.add_font('Montserrat', '', 'Montserrat-Regular.ttf', uni=True)
    pdf.add_font('Montserrat-Bold', '', 'Montserrat-Bold.ttf', uni=True)

    # Colors
    header_color = (30, 144, 255)
    fill_color = (240, 248, 255)
    text_color = (0, 0, 0)

    # Add title
    pdf.set_font('Montserrat-Bold', '', 16)
    pdf.set_text_color(*text_color)
    pdf.cell(0, 10, "Faktura", 0, 1, 'C')
    pdf.ln(10)

    # Client details
    pdf.set_font('Montserrat-Bold', '', 12)
    pdf.set_fill_color(*header_color)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "Odběratel", 0, 1, 'L', fill=True)

    pdf.set_font('Montserrat', '', 12)
    pdf.set_text_color(*text_color)
    pdf.cell(0, 10, f"{invoice_data['Client Name']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Adresa: {invoice_data['Client Address']}", 0, 1, 'L')
    pdf.cell(0, 10, f"IČO: {invoice_data['Client ICO']}", 0, 1, 'L')
    pdf.cell(0, 10, f"DIČ: {invoice_data['Client DIC']}", 0, 1, 'L')

    # Provider details to the right
    pdf.ln(10)
    pdf.set_font('Montserrat-Bold', '', 12)
    pdf.set_fill_color(*header_color)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "Dodavatel", 0, 1, 'L', fill=True)

    pdf.set_font('Montserrat', '', 12)
    pdf.set_text_color(*text_color)
    pdf.cell(0, 10, f"{invoice_data['Provider Name']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Adresa: {invoice_data['Provider Address']}", 0, 1, 'L')
    pdf.cell(0, 10, f"IČO: {invoice_data['Provider ICO']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Číslo účtu: {invoice_data['Provider Bank Account Number']}", 0, 1, 'L')

    pdf.ln(5)
    pdf.cell(0, 10, "Fyzická osoba zapsaná v živnostenském rejstříku", 0, 1, 'L')

    pdf.ln(10)

    # Invoice details
    pdf.set_font('Montserrat-Bold', '', 12)
    pdf.set_fill_color(*header_color)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "Údaje o faktuře", 0, 1, 'L', fill=True)

    pdf.set_font('Montserrat', '', 12)
    pdf.set_text_color(*text_color)
    pdf.cell(0, 10, f"Číslo faktury: {invoice_data['Invoice Number']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Datum vystavení: {invoice_data['Invoice Date']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Datum splatnosti: {invoice_data['Due Date']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Popis položky: {invoice_data['Item Description']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Množství: {invoice_data['Item Quantity']}", 0, 1, 'L')
    pdf.cell(0, 10, f"Cena položky: {invoice_data['Item Price']} Kč", 0, 1, 'L')
    pdf.cell(0, 10, f"Celkem k úhradě: {invoice_data['Total Amount']}", 0, 1, 'L')

    # QR Payment
    qr_y = pdf.get_y() - 70
    pdf.set_xy(150, qr_y)
    pdf.set_font('Montserrat-Bold', '', 12)
    pdf.set_text_color(*text_color)
    pdf.cell(50, 10, "QR Platba", 0, 1, 'C')

    # Generate QR code
    bank_account_number = invoice_data['Provider Bank Account Number']
    bank_code = bank_account_number.split('/')[1]
    account_number = bank_account_number.split('/')[0]
    iban = convert_to_iban(account_number, bank_code)
    
    qr_data = (
        f"SPD*1.0*ACC:{iban}*AM:{invoice_data['Total Amount'].split()[0]}*CC:CZK*X-VS:{invoice_data['Invoice Number']}"
    )
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Save the QR code to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        img.save(tmpfile.name)
        pdf.image(tmpfile.name, x=150, y=pdf.get_y() + 5, w=50)

    pdf_file = f"lounek_faktura_{invoice_data['Invoice Number']}.pdf"
    pdf.output(pdf_file)

    return pdf_file

def download_pdf(pdf_file):
    with open(pdf_file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    st.markdown(f'<a href="data:application/octet-stream;base64,{base64_pdf}" download="{pdf_file}">Stáhnout fakturu</a>', unsafe_allow_html=True)

def main():
    st.title("Lounyho generátor faktur")

    st.sidebar.header("Údaje o faktuře")
    client_name = st.sidebar.text_input("Název odběratele")
    client_address = st.sidebar.text_area("Adresa odběratele")
    client_ico = st.sidebar.text_input("IČO odběratele")
    client_dic = st.sidebar.text_input("DIČ odběratele")
    invoice_number = st.sidebar.text_input("Číslo faktury")
    invoice_date = st.sidebar.date_input("Datum vystavení")
    due_date = st.sidebar.date_input("Datum splatnosti")
    item_description = st.sidebar.text_input("Popis položky")
    item_quantity = st.sidebar.number_input("Množství", min_value=1, step=1)
    item_price = st.sidebar.number_input("Cena položky", min_value=0, step=1)
    provider_name = st.sidebar.text_input("Název dodavatele")
    provider_address = st.sidebar.text_input("Adresa dodavatele")
    provider_ico = st.sidebar.text_input("IČO dodavatele")
    bank_account_number = st.sidebar.text_input("Číslo bankovního účtu dodavatele ve formátu xxxx-xxxxxxx/xxxx")

    if st.sidebar.button("Vygenerovat fakturu"):
        invoice_data = {
            "Client Name": client_name,
            "Client Address": client_address,
            "Client ICO": client_ico,
            "Client DIC": client_dic,
            "Invoice Number": invoice_number,
            "Invoice Date": invoice_date,
            "Due Date": due_date,
            "Item Description": item_description,
            "Item Quantity": item_quantity,
            "Item Price": item_price,
            "Provider Name": provider_name,
            "Provider Address": provider_address,
            "Provider ICO": provider_ico,
            "Provider Bank Account Number": bank_account_number,
            "Total Amount": f"{item_quantity * item_price} Kč"
        }
        pdf_file = generate_invoice(invoice_data)
        st.success("Faktura byla úspěšně vygenerována!")
        download_pdf(pdf_file)

if __name__ == "__main__":
    main()
