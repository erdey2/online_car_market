from graphviz import Digraph

# Create a directed graph for 3-party interaction
dot = Digraph("Three_Party_Sales", format="pdf")
dot.attr(rankdir="LR", size="10")

# Broker nodes
dot.node("B1", "Broker Sign-up & Verification")
dot.node("B2", "Pre-Payment to ERP")
dot.node("B3", "Car Reserved & Listed")
dot.node("B4", "Marketing & Lead Handling")
dot.node("B5", "Customer Buys via Broker")
dot.node("B6", "Commission Settlement")

# Dealer nodes
dot.node("D1", "Dealer Adds Cars to Inventory")
dot.node("D2", "Car Reserved for Broker (after payment)")
dot.node("D3", "Prepares Car for Delivery")

# ERP nodes
dot.node("E1", "ERP Verifies Broker")
dot.node("E2", "ERP Records Payment & Locks Car")
dot.node("E3", "ERP Generates Sales Order & Splits Commission")
dot.node("E4", "ERP Releases Payment to Dealer & Broker")

# Customer interaction
dot.node("C1", "Customer Buys Car")

# Flows
# Broker side
dot.edges([("B1", "E1"), ("B2", "E2"), ("B3", "B4"), ("B4", "C1"), ("C1", "B5"), ("B5", "E3"), ("E4", "B6")])

# Dealer side
dot.edge("D1", "D2")
dot.edge("D2", "D3")
dot.edge("D3", "E3")

# ERP side integration
dot.edge("E1", "B2")  # Approval → Payment step
dot.edge("E2", "D2")  # Lock car for broker
dot.edge("E3", "E4")  # Order → Payment release

# Render to PDF
dot.render("three_party_sales", format="pdf", view=True)
