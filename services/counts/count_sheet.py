import base64
from count_pdf import PDF


def generate(item):
    pdf = PDF('P', 'mm', 'Letter')
    pdf.alias_nb_pages()
    pdf.add_page()

    index = 1
    fill = True
    for product in item["products"]:
        pdf.set_font('Arial', 'B', 16)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(10, 10, str(index), 0, 0, 'L', fill)
        pdf.cell(70, 10, product["brand_name"], 0, 0, 'R', fill)
        pdf.cell(5, 10, '', 0, 0, 'C', fill)
        pdf.cell(30, 10, '', 1, 0, 'C', fill)
        pdf.cell(10, 10, ' ', 0, 0, 'C')
        if product["units_per_pallet"] > 0:
            pdf.cell(30, 10, '', 1, 0, 'C', fill)
        else:
            pdf.cell(30, 10, '', 0, 0, 'C')
        pdf.cell(1, 10, '', 0, 1, 'C')
        pdf.cell(85, 10, '', 0, 0,)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(30, 5, product["package_type_name"], 0, 0, 'C')
        if product["units_per_pallet"] > 0:
            pdf.cell(10, 10, '', 0, 0)
            pdf.cell(30, 5, 'Pallets (' + str(product["units_per_pallet"]) + ' per pallet)', 0, 0, 'C')
        pdf.cell(1, 10, '', 0, 1)

        index = index + 1
        fill = not fill

    count_sheet_data = pdf.output('count-sheet.pdf', 'S').encode('latin-1')
    count_sheet_base_64 = base64.b64encode(count_sheet_data)
    count_sheet_string = count_sheet_base_64.decode('utf-8')

    return count_sheet_string


if __name__ == "__main__":
    count = {"status": "open",
             "package_types": [],
             "supplier_id": "4f5b7edc-5bfe-402b-bca4-4d2397efac3c",
             "user_id": "5d4a16f0eab56e0cc579da77",
             "products": [
                 {"units_per_pallet": 48, "pallet_quantity": 0, "product_id": "7ad75c06-748e-48a1-b208-8718aebee8e9", "package_type_name": "Case of 24 12oz Cans", "package_type_id": "7bea6377-3f77-47ab-9663-d9b6df2e16f1", "brand_name": "Bad Moon Porter", "brand_id": "2c10aa25-7b5c-4bd5-add3-f0239ca98b30", "unit_quantity": 0}, {"units_per_pallet": 48, "pallet_quantity": 0, "product_id": "b1efcea3-73f0-4384-a24c-197d67e46e92", "package_type_name": "Case of 24 12oz Cans", "package_type_id": "7bea6377-3f77-47ab-9663-d9b6df2e16f1", "brand_name": "Devil's Milk", "brand_id": "70d6499a-415c-4eb4-8287-bf88fcde62cc", "unit_quantity": 0}, {"units_per_pallet": 48, "pallet_quantity": 0, "product_id": "6f199d32-57d1-42c7-9b0b-046eb46cfd28", "package_type_name": "Case of 24 12oz Cans", "package_type_id": "7bea6377-3f77-47ab-9663-d9b6df2e16f1", "brand_name": "Mad Bishop", "brand_id": "a7aaa8f7-1921-4ad5-b542-56b5fbab34c2", "unit_quantity": 0}, {"units_per_pallet": 48, "pallet_quantity": 0, "product_id": "7f541f27-5308-414f-9d9d-061f0fd122ff", "package_type_name": "Case of 24 12oz Cans", "package_type_id": "7bea6377-3f77-47ab-9663-d9b6df2e16f1", "brand_name": "Naked Fish", "brand_id": "8c748b58-d3c8-4337-a16c-db9d147071e8", "unit_quantity": 0}, {"units_per_pallet": 0, "pallet_quantity": 0, "product_id": "75c9c921-b8fb-4264-b472-25de78c53a05", "package_type_name": "15.5gal Keg", "package_type_id": "8dd365b6-3167-4317-b218-20bd5fd2d833", "brand_name": "Bad Moon Porter", "brand_id": "2c10aa25-7b5c-4bd5-add3-f0239ca98b30", "unit_quantity": 0}, {"units_per_pallet": 0, "pallet_quantity": 0, "product_id": "745aa0e4-8d95-43ce-8d8e-0f0db505cdac", "package_type_name": "15.5gal Keg", "package_type_id": "8dd365b6-3167-4317-b218-20bd5fd2d833", "brand_name": "Devil's Milk", "brand_id": "70d6499a-415c-4eb4-8287-bf88fcde62cc", "unit_quantity": 0}, {"units_per_pallet": 0, "pallet_quantity": 0, "product_id": "328d77a2-c807-4459-b2ec-526610e34f9f", "package_type_name": "15.5gal Keg", "package_type_id": "8dd365b6-3167-4317-b218-20bd5fd2d833", "brand_name": "Mad Bishop", "brand_id": "a7aaa8f7-1921-4ad5-b542-56b5fbab34c2", "unit_quantity": 0}, {"units_per_pallet": 0, "pallet_quantity": 0, "product_id": "1a48ea48-5b5f-46e6-9495-0127f46bc1df", "package_type_name": "15.5gal Keg", "package_type_id": "8dd365b6-3167-4317-b218-20bd5fd2d833", "brand_name": "Naked Fish", "brand_id": "8c748b58-d3c8-4337-a16c-db9d147071e8", "unit_quantity": 0}],
             "count_date": "2019-08-15",
             "entity_id": "1334c1c8-9552-405b-9093-cefa649b17db",
             "version": "3605601a-17c8-4e76-a202-65a64d72e455",
             "changed_on": "2019-08-15T14:55:33Z"
             }

    count_string = generate(count)

    count_sheet = base64.b64decode(count_string)

    f = open('count_sheet.pdf', 'wb')
    f.write(count_sheet)
    f.close()

