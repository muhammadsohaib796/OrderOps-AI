import requests

BASE_URL = "http://127.0.0.1:8000"


def test_happy_path():
    print("\n=== TEST 1: Happy path (in-stock item, no negotiation) ===")
    response = requests.post(
        f"{BASE_URL}/orders",
        json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 1}]},
    )
    data = response.json()
    print("Response:", data)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["graph_result"]["out_of_stock_items"] == [], "Expected no out-of-stock items"
    assert data["graph_result"]["final_status"] == "fulfilled", "Expected immediate fulfillment"
    print("PASSED: order fulfilled immediately, no pause needed")


def test_negotiation_path():
    print("\n=== TEST 2: Out-of-stock item triggers negotiation, then customer accepts ===")
    response = requests.post(
        f"{BASE_URL}/orders",
        json={"customer_id": 1, "items": [{"product_id": 2, "quantity": 1}]},
    )
    data = response.json()
    print("Create order response:", data)

    assert data["graph_result"]["out_of_stock_items"] == [2], "Expected product 2 out of stock"
    assert data["graph_result"]["alternative_product_id"] is not None, "Expected an alternative to be found"
    assert data["graph_result"]["final_status"] is None, "Expected graph to be paused, not finished"

    order_id = data["order_id"]

    respond = requests.get(f"{BASE_URL}/respond", params={"order_id": order_id, "decision": "accept"})
    respond_data = respond.json()
    print("Respond response:", respond_data)

    assert respond_data["final_status"] == "updated", "Expected final_status to be 'updated' after accepting"
    print("PASSED: negotiation triggered, paused correctly, resumed correctly on accept")


if __name__ == "__main__":
    test_happy_path()
    test_negotiation_path()
    print("\nAll end-to-end tests passed.")