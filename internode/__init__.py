import requests
from xml.etree import ElementTree
from datetime import datetime
from platform import python_implementation, python_version

PACKAGE_VERSION = '0.1.0'


def timestamp():
    return str(datetime.utcnow().isoformat())


class Api:
    """
    Abstraction of the Internode API that automatically passes the provided
    username and password with each request.
    """
    spec_version = '1.5'
    host = "https://customer-webtools-api.internode.on.net/api/v1.5"
    headers = {
        'User-Agent': 'internode.py/%s (%s %s, api/%s)' % (PACKAGE_VERSION, python_implementation(), python_version(), spec_version),
    }

    def __init__(self, username, password):
        """
        Initializes Api with your Internode account username and password.

        Args:
            username: Username for your Internode account. (do not include
                @internode.on.net)
            password: Password for your Internode account.
        """
        self.auth = (username, password)

    def get(self, url="", **kwargs):
        """
        Sends a GET request to the Internode API.

        Args:
            url: Additional URL part. Appended to the Internode API URL.
        Returns:
            API response. See:
            http://docs.python-requests.org/en/latest/user/quickstart/#response-content
        """
        url = "%s/%s" % (self.host, url)
        response = requests.get(url, auth=self.auth, headers=self.headers, **kwargs)

        # It is possible for the server to return a 500 error,
        # but still respond with a valid body.
        assert response.status_code != 401, "Request failed. Authorization was missing or invalid."
        return ElementTree.fromstring(response.content)


class Account:
    """
    Represents an Internode account. An account owns one or more Services (e.g.
    Home ADSL, Business ADSL, etc.).
    """
    services = {}

    def __init__(self, username, password):
        """
        Initializes Account with your Internode account username and password.

        Args:
            username: Username for your Internode account. (do not include
                @internode.on.net)
            password: Password for your Internode account.
        """
        self.api = Api(username, password)

    def get_services(self):
        """
        Retrieves all of the Services associated with this account.
        """
        tree = self.api.get()
        services_tree = tree.find('api/services')
        assert services_tree is not None, "XML was not as expected"
        assert int(services_tree.get('count')) > 0, "There are no services for this account"

        self.services = {}
        for element in services_tree:
            self.services[element.text] = Service(int(element.text), self.api)
        return self.services


class Service:
    def __init__(self, id, api):
        """
        Initializes Service.

        Args:
            id: Service ID
            api: Instance of the Api class. The service ID must belong to an
            Account with the username and password provided to the Api instance.
        """
        self.id = id
        self.api = api

    def get_service(self):
        """
        Retrieves information about this service
        """
        tree = self.api.get('/%s/service' % self.id)
        service_tree = tree.find('api/service')
        assert service_tree is not None, "XML was not as expected"

        self.service = {}
        for i in service_tree:
            self.service[i.tag] = i.text

        # Convert to bool where appropriate
        if "excess-charged" in self.service:
            self.service["excess-charged"] = self.service["excess-charged"] == 'yes'
        if "excess-restrict-access" in self.service:
            self.service["excess-restrict-access"] = self.service["excess-restrict-access"] == 'yes'
        if "excess-shaped" in self.service:
            self.service["excess-shaped"] = self.service["excess-shaped"] == 'yes'

        # Convert to int where appropriate
        if "id" in self.service:
            self.service["id"] = int(self.service["id"])
        if "quota" in self.service:
            self.service["quota"] = int(self.service["quota"])
        return self.service

    def get_history(self, verbose=True):
        """
        Retrieves usage history for this service.

        Args:
            verbose: When true, output will include a breakdown of the usage,
            amount uploaded and downloaded, to both metered and non-metered
            sources.
        """
        tree = self.api.get('/%s/history' % self.id, params={
            "verbose": int(verbose)
        })
        history_tree = tree.find('api/usagelist')
        assert history_tree is not None, "Response was not as expected and can not be processed further."

        self.history = {}
        for element in history_tree:
            total = element.find('traffic[@name="total"]')

            if verbose is True:
                unmetered_up = element.find('traffic[@direction="up"][@name="unmetered"]')
                unmetered_down = element.find('traffic[@direction="down"][@name="unmetered"]')
                metered_up = element.find('traffic[@direction="up"][@name="metered"]')
                metered_down = element.find('traffic[@direction="down"][@name="metered"]')

            output = {}

            if total is not None:
                output['total'] = int(total.text)

            if unmetered_up is not None or unmetered_down is not None:
                output['unmetered'] = {}
            if metered_up is not None or metered_down is not None:
                output['metered'] = {}

            if unmetered_up is not None:
                output['unmetered']['up'] = int(unmetered_up.text)
            if unmetered_down is not None:
                output['unmetered']['down'] = int(unmetered_down.text)
            if metered_up is not None:
                output['metered']['up'] = int(metered_up.text)
            if metered_down is not None:
                output['metered']['down'] = int(metered_down.text)

            self.history[element.get('day')] = output

        return self.history

    def get_usage(self):
        """
        Retrieves current usage information for this service
        """
        tree = self.api.get('/%s/usage' % self.id)
        traffic_tree = tree.find('api/traffic')
        assert traffic_tree is not None, "Response was not as expected and can not be processed further."

        self.usage = {}
        for i in ['name', 'plan-interval', 'rollover', 'unit']:
            self.usage[i] = traffic_tree.get(i)

        self.usage['quota'] = int(traffic_tree.get('quota'))
        self.usage['usage'] = int(traffic_tree.text)
        return self.usage

    def dump(self):
        """
        Produce a simple representation of this class, which can be output to
        a human-readable formats like JSON.
        """
        return {
            "generated": timestamp(),
            "service": self.get_service(),
            "history": self.get_history(),
            "usage": self.get_usage()
        }
