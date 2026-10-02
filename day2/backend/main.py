from datetime import date, datetime
from time import perf_counter
from typing import Optional
import asyncio

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel


app = FastAPI(
    title="CityCare Clinic Backend",
    description="FastAPI backend for the Day 2 clinic voice agent",
    version="1.0.0",
)


# ============================================================
# In-memory database
# ============================================================

appointments = {}

next_appointment_id = 1


# Available appointment slots for each date.
# If a date is not present, these default slots are available.
DEFAULT_SLOTS = [
    "09:00",
    "10:00",
    "11:00",
    "14:00",
    "15:00",
    "16:00",
]


# ============================================================
# Pydantic models
# ============================================================

class AppointmentCreate(BaseModel):
    name: str
    phone: str
    date: str
    time: str
    service: str


class AppointmentUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None


# ============================================================
# Timing middleware
# ============================================================

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start_time = perf_counter()

    response = await call_next(request)

    elapsed_ms = (perf_counter() - start_time) * 1000

    print(
        f"{request.method} {request.url.path} "
        f"-> {response.status_code} "
        f"({elapsed_ms:.2f} ms)"
    )

    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"

    return response


# ============================================================
# Helper functions
# ============================================================

def validate_date(date_string: str) -> None:
    """
    Validate date format YYYY-MM-DD.
    """
    try:
        date.fromisoformat(date_string)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )


def validate_time(time_string: str) -> None:
    """
    Validate time format HH:MM.
    """
    try:
        datetime.strptime(time_string, "%H:%M")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid time format. Use HH:MM.",
        )


def get_available_slots(target_date: str):
    """
    Return available slots for a particular date.
    """
    booked_times = {
        appointment["time"]
        for appointment in appointments.values()
        if appointment["date"] == target_date
    }

    return [
        slot
        for slot in DEFAULT_SLOTS
        if slot not in booked_times
    ]


# ============================================================
# Root endpoint
# ============================================================

@app.get("/")
async def root():
    return {
        "message": "CityCare Clinic backend is running"
    }


# ============================================================
# 1. GET /slots
# ============================================================

@app.get("/slots")
async def list_slots(date: str = Query(...)):
    """
    List free appointment times for a date.
    """

    validate_date(date)

    slots = get_available_slots(date)

    return slots


# ============================================================
# 2. POST /appointments
# ============================================================

@app.post("/appointments")
async def book_appointment(appointment: AppointmentCreate):
    """
    Book a new clinic appointment.
    """

    global next_appointment_id

    validate_date(appointment.date)
    validate_time(appointment.time)

    # Check whether the requested slot is already booked.
    available_slots = get_available_slots(appointment.date)

    if appointment.time not in available_slots:
        raise HTTPException(
            status_code=409,
            detail="The requested appointment time is not available.",
        )

    appointment_id = next_appointment_id

    appointments[appointment_id] = {
        "id": appointment_id,
        "name": appointment.name,
        "phone": appointment.phone,
        "date": appointment.date,
        "time": appointment.time,
        "service": appointment.service,
    }

    next_appointment_id += 1

    return {
        "message": "Appointment booked successfully",
        "appointment": appointments[appointment_id],
    }

@app.get("/appointments/all")
async def get_all_appointments():
    """Return all appointments."""
    return list(appointments.values())
# ============================================================
# 3. PATCH /appointments/{id}
# ============================================================

@app.patch("/appointments/{appointment_id}")
async def change_appointment(
    appointment_id: int,
    update: AppointmentUpdate,
):
    """
    Change the date or time of an existing appointment.
    """

    if appointment_id not in appointments:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    appointment = appointments[appointment_id]

    new_date = update.date if update.date is not None else appointment["date"]
    new_time = update.time if update.time is not None else appointment["time"]

    validate_date(new_date)
    validate_time(new_time)

    # If the date/time is changing, make sure the new slot is free.
    if new_date != appointment["date"] or new_time != appointment["time"]:

        available_slots = get_available_slots(new_date)

        # The current appointment's existing slot should not
        # block itself when moving within the same date.
        if (
            new_date == appointment["date"]
            and appointment["time"] not in available_slots
        ):
            available_slots.append(appointment["time"])

        if new_time not in available_slots:
            raise HTTPException(
                status_code=409,
                detail="The requested new time is not available.",
            )

    appointment["date"] = new_date
    appointment["time"] = new_time

    return {
        "message": "Appointment updated successfully",
        "appointment": appointment,
    }


# ============================================================
# 4. DELETE /appointments/{id}
# ============================================================

@app.delete("/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: int):
    """
    Cancel an existing appointment.
    """

    if appointment_id not in appointments:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    cancelled = appointments.pop(appointment_id)

    return {
        "message": "Appointment cancelled successfully",
        "appointment": cancelled,
    }


# ============================================================
# 5. GET /appointments?phone=...
# ============================================================

@app.get("/appointments")
async def find_appointments(
    phone: str = Query(...)
):
    """
    Find appointments using a phone number.
    """

    results = [
        appointment
        for appointment in appointments.values()
        if appointment["phone"] == phone
    ]

    return {
        "appointments": results
    }


# ============================================================
# 6. GET /slow
# ============================================================

@app.get("/slow")
async def slow_endpoint():
    """
    Intentionally waits 3 seconds for latency testing.
    """

    await asyncio.sleep(3)

    return {
        "message": "Slow endpoint completed"
    }


# ============================================================
# 7. GET /broken
# ============================================================

@app.get("/broken")
async def broken_endpoint():
    """
    Intentionally returns HTTP 500 for error handling testing.
    """

    raise HTTPException(
        status_code=500,
        detail="Booking backend is temporarily unavailable.",
    )