import csv

with open('names.csv', 'w', newline='') as csvfile:
    fieldnames = ['first_name','Nothing','last_name']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerow({'first_name': 'Baked', 'last_name': 'Beans'})
    writer.writerow({'first_name': 'Lovely', 'last_name': 'Spam'})
    writer.writerow({'first_name': 'Wonderful', "Nothing":1,'last_name': 'Spam'})
