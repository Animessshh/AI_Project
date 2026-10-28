
import sqlite3
import pandas as pd
import streamlit as st

from database import (
    DB_PATH, initialize_database, get_food_items,
    get_locations, place_order, update_order_status
)
from pathfinding import campus_graph, START_LOCATION
from delivery_planner import generate_delivery_plan

st.set_page_config(
    page_title="BiteQ | Campus Eats",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded",
)
initialize_database()

# ---------- BiteQ design system ----------
st.markdown("""
<style>
.stApp {background:#FAF7F2;color:#292333}
[data-testid="stHeader"] {background:#FAF7F2}
[data-testid="stSidebar"] {
    background:#FFFDF9;border-right:1px solid #EEE5DA
}
h1,h2,h3,h4 {color:#292333!important;letter-spacing:-.6px}
h1 {font-size:2.45rem!important}
p,label,.stCaption {color:#756D7B}
[data-testid="stMetric"] {
    background:#FFFFFF;border:1px solid #EEE5DA;
    border-radius:16px;padding:17px
}
[data-testid="stMetricLabel"] {color:#756D7B!important}
[data-testid="stMetricValue"] {color:#E56B35!important}
.stButton>button,.stFormSubmitButton>button {
    background:#E56B35!important;color:white!important;
    border:1px solid #E56B35!important;border-radius:10px;
    font-weight:700;min-height:42px
}
.stButton>button:hover,.stFormSubmitButton>button:hover {
    background:#C95424!important;border-color:#C95424!important
}
.stButton>button p,.stFormSubmitButton>button p {color:white!important}
input,textarea,[data-baseweb="select"]>div {
    background:#FFFFFF!important;color:#292333!important;
    border-color:#E5DCD2!important;border-radius:9px!important
}
[data-baseweb="select"] * {color:#292333!important}
[data-testid="stDataFrame"] {
    background:white;border:1px solid #EEE5DA;border-radius:12px
}
[data-testid="stVerticalBlockBorderWrapper"] {
    background:#FFFFFF;border-color:#EEE5DA!important;
    border-radius:15px
}
hr {border-color:#EEE5DA}
.bq-eyebrow {
    color:#E56B35;font-size:11px;font-weight:800;
    letter-spacing:2px;text-transform:uppercase
}
.bq-card {
    background:#FFFFFF;border:1px solid #EEE5DA;
    border-radius:17px;padding:19px;margin-bottom:10px
}
.bq-price {color:#E56B35;font-size:24px;font-weight:850}
.bq-muted {color:#756D7B;font-size:13px}
.bq-pill {
    display:inline-block;background:#FFF0E7;color:#C95424;
    border-radius:30px;padding:5px 10px;
    font-size:11px;font-weight:800
}
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------
def load_orders():
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query(
            "SELECT * FROM orders ORDER BY order_id DESC", con
        )


def food_name(food):
    return str(food.get("name", "Food"))


def location_name(loc):
    return loc.get("name", "") if isinstance(loc, dict) else str(loc)


def money(value):
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def title_block(eyebrow, title, subtitle):
    st.markdown(f'<div class="bq-eyebrow">{eyebrow}</div>',
                unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)
    st.write("")


def select_and_order(item_name):
    st.session_state["selected_food"] = item_name
    st.session_state["nav_page"] = "Order Food"


# ---------- Sidebar ----------
pages = ["Discover", "Order Food", "Delivery Planner", "Order History"]

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Discover"

with st.sidebar:
    st.markdown(
        '<div style="font-size:29px;font-weight:900;color:#292333">'
        'bite<span style="color:#E56B35">Q</span> 🍊</div>',
        unsafe_allow_html=True,
    )
    st.caption("CAMPUS FOOD, MADE EASY")
    st.divider()
    page = st.radio("YOUR SPACE", pages, key="nav_page")
    st.divider()
    st.markdown("**CAMPUS DELIVERY**")
    st.caption(f"Robot base · {START_LOCATION}")
    st.caption("Fresh choices. Simple delivery.")


# ---------- Current data ----------
orders = load_orders()
foods = get_food_items()
locations = [location_name(x) for x in get_locations()]
food_names = [food_name(x) for x in foods]
food_map = {food_name(x): x for x in foods}
pending = orders[orders["status"] == "Pending"].copy() if not orders.empty else orders.copy()


# ==================================================
# DISCOVER
# ==================================================
if page == "Discover":
    title_block("WELCOME TO BITEQ", "Good food. Right on campus.",
                "Find your favourite, place an order, and let campus delivery do the rest.")

    a, b, c, d = st.columns(4)
    a.metric("All orders", len(orders))
    b.metric("Waiting", int((orders["status"] == "Pending").sum()) if len(orders) else 0)
    c.metric("In progress", int((orders["status"] == "Planned").sum()) if len(orders) else 0)
    d.metric("Delivered", int((orders["status"] == "Delivered").sum()) if len(orders) else 0)

    st.write("")
    st.markdown('<div class="bq-eyebrow">THE CAMPUS MENU</div>',
                unsafe_allow_html=True)
    st.subheader("What are you craving?")

    if not foods:
        st.info("No menu items found. Add food items in database.py.")
    else:
        cols = st.columns(min(3, len(foods)))
        icons = ["🍔", "🥪", "🍕", "🥤", "🍟", "🍜"]

        for i, food in enumerate(foods):
            with cols[i % len(cols)]:
                st.markdown(
                    f'<div class="bq-card">'
                    f'<div style="font-size:38px">{icons[i % len(icons)]}</div>'
                    f'<div class="bq-eyebrow">CAMPUS FAVOURITE</div>'
                    f'<h3>{food_name(food)}</h3>'
                    f'<div class="bq-price">{money(food.get("price", 0))}</div>'
                    f'<p class="bq-muted">A tasty pick for your campus day.</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    "Order this →",
                    key=f"food_{i}",
                    use_container_width=True,
                    on_click=select_and_order,
                    args=(food_name(food),),
                )

    st.write("")
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("Recently placed")
        if orders.empty:
            st.info("Your first order will appear here.")
        else:
            st.dataframe(orders.head(5), use_container_width=True, hide_index=True)

    with right:
        st.subheader("Delivery progress")
        delivered = int((orders["status"] == "Delivered").sum()) if len(orders) else 0
        st.progress(delivered / len(orders) if len(orders) else 0)
        st.caption(f"{delivered} of {len(orders)} orders delivered")
        st.markdown(
            f'<div class="bq-card"><div class="bq-eyebrow">DELIVERY ZONE</div>'
            f'<h3>{len(locations)} campus locations</h3>'
            f'<p class="bq-muted">Robot base: {START_LOCATION}</p></div>',
            unsafe_allow_html=True,
        )


# ==================================================
# ORDER FOOD
# ==================================================
elif page == "Order Food":
    title_block("MAKE IT A GOOD MEAL", "Place your order.",
                "Choose your food and tell us where to deliver it.")

    if not foods or not locations:
        st.warning("The menu or campus locations are empty. Check database.py.")
    else:
        left, right = st.columns([1.05, 1], gap="large")

        with left:
            st.markdown('<div class="bq-eyebrow">01 / PICK YOUR FOOD</div>',
                        unsafe_allow_html=True)
            selected = st.selectbox(
                "Menu item", food_names,
                index=food_names.index(st.session_state["selected_food"])
                if st.session_state.get("selected_food") in food_names else 0,
            )
            food = food_map[selected]
            st.markdown(
                f'<div class="bq-card"><div style="font-size:46px">🍽️</div>'
                f'<h2>{selected}</h2>'
                f'<div class="bq-price">{money(food.get("price", 0))}</div>'
                f'<p class="bq-muted">Prepared for your campus delivery.</p>'
                f'<span class="bq-pill">AVAILABLE TO ORDER</span></div>',
                unsafe_allow_html=True,
            )

        with right:
            st.markdown('<div class="bq-eyebrow">02 / DELIVERY DETAILS</div>',
                        unsafe_allow_html=True)
            with st.form("order_form"):
                customer = st.text_input("Your name", placeholder="Enter your name")
                quantity = st.number_input("Quantity", 1, 10, 1)
                destination = st.selectbox("Campus destination", locations)
                priority = st.selectbox("Priority", ["Normal", "High", "Low"])
                st.divider()
                st.markdown("**ORDER SUMMARY**")
                st.markdown(f"### {quantity} × {selected}")
                st.markdown(f'<div class="bq-price">{money(food.get("price", 0) * quantity)}</div>',
                            unsafe_allow_html=True)
                submit = st.form_submit_button("Confirm order →",
                                               use_container_width=True)

            if submit:
                if not customer.strip():
                    st.error("Please enter your name.")
                else:
                    try:
                        place_order(customer.strip(), selected, destination,
                                    priority, int(quantity))
                        st.success("Order placed successfully!")
                        st.session_state.pop("selected_food", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not place order: {e}")


# ==================================================
# DELIVERY PLANNER
# ==================================================
elif page == "Delivery Planner":
    title_block("SMART CAMPUS LOGISTICS", "Delivery planner.",
                "Build routes for pending orders using your existing A* planner.")

    if pending.empty:
        st.success("No pending orders. You're all caught up!")
    else:
        st.markdown(
            f'<div class="bq-card"><div class="bq-eyebrow">QUEUE STATUS</div>'
            f'<h2>{len(pending)} orders waiting for a route</h2>'
            f'<p class="bq-muted">Review the queue, then generate a plan.</p></div>',
            unsafe_allow_html=True,
        )
        st.dataframe(pending, use_container_width=True, hide_index=True)
        battery = st.slider("Available robot battery (%)", 0, 100, 100, 5)

        if st.button("Generate delivery routes →", use_container_width=True):
            st.session_state.pop("delivery_plan", None)
            try:
                st.session_state["delivery_plan"] = generate_delivery_plan(
                    pending.to_dict("records"), campus_graph,
                    battery_level=battery,
                )
            except Exception as e:
                st.error(f"Could not generate plan: {e}")

        for item in st.session_state.get("delivery_plan", []):
            with st.container(border=True):
                good = bool(item.get("feasible"))
                st.markdown(
                    f"### Order #{item.get('order_id', '—')} · "
                    f"{item.get('destination', 'Unknown')}"
                )
                st.markdown("🟢 Feasible" if good else "🟠 Needs attention")
                route = item.get("route") or []
                st.write(" → ".join(map(str, route)) if route else "No route returned")
                x, y, z = st.columns(3)
                x.metric("Distance", str(item.get("distance", "—")))
                y.metric("Trip distance", str(item.get("total_trip_distance", "—")))
                z.metric("Battery needed", f"{item.get('battery_required', '—')}%")
                if item.get("reason"):
                    st.caption(item["reason"])


# ==================================================
# ORDER HISTORY
# ==================================================
elif page == "Order History":
    title_block("ORDER DESK", "Order history.",
                "Review your campus orders and update their status.")

    if orders.empty:
        st.info("No orders have been placed yet.")
    else:
        filter_status = st.selectbox(
            "Show orders", ["All", "Pending", "Planned", "Delivered", "Cancelled"]
        )
        visible = orders if filter_status == "All" else orders[orders["status"] == filter_status]
        st.dataframe(visible, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Update order status")
        order_id = st.selectbox("Order ID", orders["order_id"].tolist())
        current = str(orders.loc[orders["order_id"] == order_id, "status"].iloc[0])
        statuses = ["Pending", "Planned", "Delivered", "Cancelled"]

        with st.form("update_form"):
            new_status = st.selectbox(
                "New status", statuses,
                index=statuses.index(current) if current in statuses else 0,
            )
            save = st.form_submit_button("Save changes", use_container_width=True)

        if save:
            try:
                update_order_status(int(order_id), new_status)
                st.success("Order status updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not update status: {e}")


st.divider()
st.caption("biteQ · Campus food, without the hassle.")
