from csv import writer
from internode import Account

USERNAME = "username"
PASSWORD = "password"

# Create a new account instance
account = Account(USERNAME, PASSWORD)

# Get services for the account
services = account.get_services()

# Loop over each service
for id, service in services.iteritems():
    history = service.get_history(verbose=True)

    # Create CSV file named after the service ID
    with open('%s.csv' % id, 'wb') as f:
        csv = writer(f)
        csv.writerow([
            'Date',
            'Unmetered Up',
            'Unmetered Down',
            'Metered Up',
            'Metered Down',
            'Total'
        ])

        # Write out history
        for date, data in history.iteritems():
            unmetered = data.get('unmetered', dict())
            metered = data.get('metered', dict())

            csv.writerow([
                date,
                unmetered.get('up', 0),
                unmetered.get('down', 0),
                metered.get('up', 0),
                metered.get('down', 0),
                data.get('total', 0)
            ])
