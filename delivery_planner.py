from pathfinding import astar, campus_graph, START_LOCATION
from database import initialize_database, get_pending_orders

ROBOT_CAPACITY = 5.0
BATTERY_RESERVE = 10.0

# Illustrative food weights in kilograms
FOOD_WEIGHTS = {
    "Burger": 0.3,
    "Sandwich": 0.25,
    "Pizza": 0.6,
    "Juice": 0.3
}

PRIORITY_VALUES = {
    "High": 3,
    "Normal": 2,
    "Low": 1
}


def sort_orders_by_priority(orders):
    """Sort orders from High to Low priority."""
    return sorted(
        orders,
        key=lambda order: PRIORITY_VALUES.get(
            order["priority"], 0
        ),
        reverse=True
    )


def check_capacity(order, robot_capacity):
    """Check whether the order fits within the weight limit."""
    food_item = order["food_item"]
    quantity = order["quantity"]

    if food_item not in FOOD_WEIGHTS or quantity <= 0:
        return False

    total_weight = FOOD_WEIGHTS[food_item] * quantity
    return total_weight <= robot_capacity


def check_battery(distance, battery_level):
    """Check battery for a round trip.
    Distance is the one-way distance in metres.
    """
    round_trip_distance = distance * 2
    battery_required = round_trip_distance * 10 / 100

    return battery_level - battery_required >= BATTERY_RESERVE


def generate_delivery_plan(
    orders, campus_graph=campus_graph, battery_level=100
):
    """Generate delivery plans using Student 2's A* algorithm."""
    plan = []

    for order in sort_orders_by_priority(orders):
        result = {
            "order_id": order["order_id"],
            "destination": order["destination"],
            "priority": order["priority"],
            "route": [],
            "distance": None,
            "total_trip_distance": None,
            "battery_required": None,
            "feasible": False,
            "reason": ""
        }

        if not check_capacity(order, ROBOT_CAPACITY):
            result["reason"] = (
                "Order exceeds capacity or has an invalid food item/quantity."
            )
            plan.append(result)
            continue

        try:
            route, distance = astar(
                campus_graph, START_LOCATION, order["destination"]
            )

            if route is None:
                result["reason"] = "No route available."
                plan.append(result)
                continue

            return_route, return_distance = astar(
                campus_graph, order["destination"], START_LOCATION
            )

            if return_route is None:
                result["reason"] = "No return route available."
                plan.append(result)
                continue

        except (ValueError, KeyError) as error:
            result["reason"] = f"Route calculation failed: {error}"
            plan.append(result)
            continue

        total_trip_distance = distance + return_distance
        battery_required = total_trip_distance * 10 / 100

        result["route"] = route
        result["distance"] = distance
        result["total_trip_distance"] = total_trip_distance
        result["battery_required"] = battery_required

        # Check the reserve using the calculated round-trip battery use.
        if battery_level - battery_required < BATTERY_RESERVE:
            result["reason"] = (
                "Insufficient battery or 10% reserve would be violated."
            )
        else:
            result["feasible"] = True
            result["reason"] = "Ready for simulated delivery."

        plan.append(result)

    return plan


def display_delivery_plan(plan):
    """Display the delivery plan in a clear, readable format."""
    print("\n" + "=" * 60)
    print("       INTELLIGENT FOOD DELIVERY AGENT")
    print("                 DELIVERY PLAN")
    print("=" * 60)

    if not plan:
        print("\nNo pending orders available for delivery.")
        print("=" * 60)
        return

    for number, item in enumerate(plan, start=1):
        print(f"\nORDER {number}")
        print("-" * 60)
        print(f"Order ID            : {item['order_id']}")
        print(f"Destination         : {item['destination']}")
        print(f"Priority            : {item['priority']}")

        if item["route"]:
            print("Delivery route      :")
            print("  " + " -> ".join(item["route"]))
            print(f"One-way distance    : {item['distance']:.2f} metres")
            print(
                f"Round-trip distance : "
                f"{item['total_trip_distance']:.2f} metres"
            )
            print(
                f"Battery required    : "
                f"{item['battery_required']:.2f}%"
            )
        else:
            print("Delivery route      : Not available")

        status = "FEASIBLE" if item["feasible"] else "NOT FEASIBLE"
        print(f"Delivery status     : {status}")
        print(f"Reason              : {item['reason']}")

    print("\n" + "=" * 60)
    print("Delivery planning completed.")
    print("=" * 60)


if __name__ == "__main__":
    initialize_database()

    orders = get_pending_orders()

    print("\n" + "=" * 60)
    print("          ORDER PRIORITY AND CAPACITY")
    print("=" * 60)

    if not orders:
        print("\nNo pending orders found in the database.")

    for order in sort_orders_by_priority(orders):
        fits = check_capacity(order, ROBOT_CAPACITY)

        print(f"\nOrder ID   : {order['order_id']}")
        print(f"Customer   : {order['customer']}")
        print(f"Food       : {order['food_item']}")
        print(f"Priority   : {order['priority']}")
        print(f"Quantity   : {order['quantity']}")
        print(f"Capacity OK: {'Yes' if fits else 'No'}")

    plan = generate_delivery_plan(
        orders, campus_graph, battery_level=100
    )

    display_delivery_plan(plan)