import base64
import csv
from io import StringIO


def generate(data):
    inventory = StringIO()
    csv.writer(inventory).writerows(data)
    inventory_file = inventory.getvalue()

    inventory_data = inventory_file.encode('latin-1')
    inventory_base_64 = base64.b64encode(inventory_data)
    inventory_string = inventory_base_64.decode('utf-8')

    return inventory_string


if __name__ == "__main__":
    sample_list = [
        ['Bad Moon Porter', 'Case of 24 12 ox bottles', 0, 54, 17, 89, 123],
        ['Bad Moon Porter', '15.5g Keg', 0, 2, 3, 4, 5],
        ['Naked Fish', 'Case of 24 12 ox bottles', 0, 54, 17, 89, 123],
        ['Naked Fish', '15.5g Keg', 0, 2, 3, 4, 5]
    ]

    csv_file = base64.b64decode(generate(sample_list))

    f = open('inventory.csv', 'wb')
    f.write(csv_file)
    f.close()
