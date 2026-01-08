"""
Streamlit UI for server booking.
"""

from __future__ import annotations

import datetime
from typing import Dict, List

import pandas as pd
import streamlit as st

from lib.ui.tool import booking_utils
from lib.ui.tool.db_utils import get_database_connection, query_latest_server_connectivity


def is_server_available(
    server_id: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    state: booking_utils.BookingState,
) -> bool:
    """
    Check whether a server is available for a given time range.

    Parameters:
        server_id (str): Server identifier.
        start_time (datetime.datetime): Booking start time.
        end_time (datetime.datetime): Booking end time.
        state (booking_utils.BookingState): Current booking state.
    Returns:
        bool: True if available, False otherwise.
    Raises:
        None
    """
    start_ts = start_time.timestamp()
    end_ts = end_time.timestamp()

    for booking_info in state.values():
        if booking_info.get("server_id") != server_id:
            continue
        if booking_info.get("actual_release_at") is not None:
            continue

        booked_start = booking_info.get("booked_at", 0)
        booked_end = booking_info.get("expected_release_at", 0)
        if max(start_ts, booked_start) < min(end_ts, booked_end):
            return False
    return True


def handle_booking(
    server_id: str,
    user_name: str,
    purpose: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
) -> None:
    """
    Handle a booking submission and update the state file.

    Parameters:
        server_id (str): Server identifier.
        user_name (str): Booking user name.
        purpose (str): Booking purpose.
        start_time (datetime.datetime): Booking start time.
        end_time (datetime.datetime): Booking end time.
    Returns:
        None
    Raises:
        None
    """
    if not user_name or not purpose:
        st.error("Your name and purpose are required.")
        return

    if not start_time or not end_time:
        st.error("Start and end times are required.")
        return

    if start_time >= end_time:
        st.error("End time must be after start time.")
        return

    if booking_utils.acquire_lock():
        try:
            state = booking_utils.get_booking_state()
            if not is_server_available(server_id, start_time, end_time, state):
                st.error(f"Server {server_id} is not available for that range.")
                return

            booking_id = f"{server_id}_{int(start_time.timestamp())}"
            state[booking_id] = {
                "server_id": server_id,
                "user": user_name,
                "purpose": purpose,
                "booked_at": start_time.timestamp(),
                "expected_release_at": end_time.timestamp(),
                "actual_release_at": None,
            }
            booking_utils.save_booking_state(state)
            st.success(
                f"Server {server_id} booked from {start_time:%Y-%m-%d} to {end_time:%Y-%m-%d}."
            )
            st.rerun()
        finally:
            booking_utils.release_lock()
    else:
        st.warning("Booking system is busy. Please try again.")


def handle_release(booking_id: str) -> None:
    """
    Release a booking by marking its actual release time.

    Parameters:
        booking_id (str): Booking identifier.
    Returns:
        None
    Raises:
        None
    """
    if booking_utils.acquire_lock():
        try:
            state = booking_utils.get_booking_state()
            if booking_id in state:
                state[booking_id]["actual_release_at"] = datetime.datetime.now().timestamp()
                booking_utils.save_booking_state(state)
                st.success(f"Booking {booking_id} released.")
                st.rerun()
        finally:
            booking_utils.release_lock()
    else:
        st.warning("Booking system is busy. Please try again.")


def _clean_expired_bookings() -> booking_utils.BookingState:
    """
    Mark expired bookings as released.

    Parameters:
        None
    Returns:
        booking_utils.BookingState: Updated booking state.
    Raises:
        None
    """
    if booking_utils.acquire_lock():
        try:
            state = booking_utils.get_booking_state()
            current_time = datetime.datetime.now().timestamp()
            for info in state.values():
                if info.get("actual_release_at") is None and info.get("expected_release_at", 0) < current_time:
                    info["actual_release_at"] = info.get("expected_release_at")
            booking_utils.save_booking_state(state)
            return state
        finally:
            booking_utils.release_lock()
    else:
        st.warning("Could not acquire lock to clean state. Displaying may be stale.")
        return booking_utils.get_booking_state()


def show_booking_page() -> None:
    """
    Render the booking page UI.

    Parameters:
        None
    Returns:
        None
    Raises:
        None
    """
    st.header("Server Booking System")
    st.caption("Book a server for a specific date range.")

    booking_state = _clean_expired_bookings()

    connection = get_database_connection()
    if not connection:
        st.error("Failed to connect to the database.")
        return
    try:
        all_servers_data = query_latest_server_connectivity(connection)
    finally:
        connection.close()

    if not all_servers_data:
        st.warning("No server information available.")
        return

    df = pd.DataFrame(all_servers_data)

    st.subheader("Book a Server")
    available_servers = [str(s["server_id"]) for s in all_servers_data]

    with st.form("booking_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_server = st.selectbox("Select a server", available_servers)
            user_name = st.text_input("Your name")
        with col2:
            purpose = st.text_area("Purpose", height=120)

        st.subheader("Select Booking Dates")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.date.today())
        with col2:
            end_date = st.date_input("End Date", datetime.date.today())

        submitted = st.form_submit_button("Book Selected Server")

        if submitted:
            if not user_name or not purpose:
                st.error("Your name and purpose are required.")
            elif selected_server:
                start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
                end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
                handle_booking(selected_server, user_name, purpose, start_datetime, end_datetime)
            else:
                st.error("Please select a server to book.")

    st.divider()
    st.subheader("Server Status and Bookings")

    bookings_by_server: Dict[str, List] = {}
    for booking_id, info in booking_state.items():
        server_id = info.get("server_id")
        if server_id:
            bookings_by_server.setdefault(server_id, []).append((booking_id, info))

    table_data = []
    for _, server in df.iterrows():
        server_id = str(server["server_id"])
        server_bookings = sorted(
            bookings_by_server.get(server_id, []), key=lambda item: item[1]["booked_at"]
        )
        active_server_bookings = [
            (bid, info) for bid, info in server_bookings if info.get("actual_release_at") is None
        ]

        if not active_server_bookings:
            table_data.append(
                {
                    "Server ID": server_id,
                    "Status": "AVAILABLE",
                    "Booked By": "-",
                    "Purpose": "-",
                    "Start Time": "-",
                    "End Time": "-",
                }
            )
        else:
            for booking_id, booking_info in active_server_bookings:
                start_dt = datetime.datetime.fromtimestamp(booking_info.get("booked_at", 0))
                end_dt = datetime.datetime.fromtimestamp(booking_info.get("expected_release_at", 0))
                table_data.append(
                    {
                        "Server ID": server_id,
                        "Status": "BOOKED",
                        "Booked By": booking_info.get("user", "N/A"),
                        "Purpose": booking_info.get("purpose", "N/A"),
                        "Start Time": start_dt.strftime("%Y-%m-%d"),
                        "End Time": end_dt.strftime("%Y-%m-%d"),
                    }
                )

    st.dataframe(
        pd.DataFrame(table_data),
        hide_index=True,
        width="stretch",
        column_config={
            "Server ID": st.column_config.TextColumn("Server ID", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Booked By": st.column_config.TextColumn("Booked By"),
            "Purpose": st.column_config.TextColumn("Purpose"),
            "Start Time": st.column_config.TextColumn("Start Time"),
            "End Time": st.column_config.TextColumn("End Time"),
        },
    )

    st.divider()
    st.subheader("Active Bookings")
    active_bookings = {
        bid: info for bid, info in booking_state.items() if info.get("actual_release_at") is None
    }
    if active_bookings:
        for booking_id, booking_info in sorted(
            active_bookings.items(), key=lambda item: item[1]["booked_at"]
        ):
            cols = st.columns((1, 2, 2, 2, 2, 1))
            cols[0].write(booking_info.get("server_id"))
            cols[1].write(booking_info.get("user", "N/A"))
            cols[2].write(booking_info.get("purpose", "N/A"))
            start_dt = datetime.datetime.fromtimestamp(booking_info.get("booked_at", 0))
            end_dt = datetime.datetime.fromtimestamp(booking_info.get("expected_release_at", 0))
            cols[3].write(start_dt.strftime("%Y-%m-%d"))
            cols[4].write(end_dt.strftime("%Y-%m-%d"))
            if cols[5].button("Release", key=f"release_{booking_id}"):
                handle_release(booking_id)
    else:
        st.info("No active bookings.")

    st.divider()
    st.subheader("Recent Releases")
    released_bookings = {
        bid: info for bid, info in booking_state.items() if info.get("actual_release_at") is not None
    }

    if released_bookings:
        cols = st.columns((1, 2, 2, 2, 2))
        cols[0].write("Server ID")
        cols[1].write("Booked By")
        cols[2].write("Booked At")
        cols[3].write("Expected Release")
        cols[4].write("Actual Release")

        for booking_id, booking_info in sorted(
            released_bookings.items(), key=lambda item: item[1]["actual_release_at"], reverse=True
        ):
            booked_at_dt = datetime.datetime.fromtimestamp(booking_info.get("booked_at", 0))
            expected_release_at_dt = datetime.datetime.fromtimestamp(
                booking_info.get("expected_release_at", 0)
            )
            actual_release_at_dt = datetime.datetime.fromtimestamp(
                booking_info.get("actual_release_at", 0)
            )

            cols = st.columns((1, 2, 2, 2, 2))
            cols[0].write(booking_info.get("server_id"))
            cols[1].write(booking_info.get("user", "N/A"))
            cols[2].write(booked_at_dt.strftime("%Y-%m-%d"))
            cols[3].write(expected_release_at_dt.strftime("%Y-%m-%d"))
            cols[4].write(actual_release_at_dt.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        st.info("No recent releases.")
