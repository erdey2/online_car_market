from django.test import SimpleTestCase
from django.urls import resolve, reverse


class BidApiUrlTests(SimpleTestCase):
	def test_bids_and_auctions_routes_are_top_level(self):
		assert reverse("bids-list") == "/api/bids/"
		assert resolve("/api/bids/").view_name == "bids-list"

		assert reverse("auctions-list") == "/api/auctions/"
		assert resolve("/api/auctions/").view_name == "auctions-list"
