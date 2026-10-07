# import httpx
# import re
# from datetime import datetime

# from livekit.agents import Agent, RunContext, function_tool
# from livekit.agents.beta.tools import EndCallTool

# from src.userdata import CallerData


# # =========================================================
# # DEMO PATIENT RECORDS
# # =========================================================

# PATIENT_DOBS = {
#     "9876543210": "1998-05-10",
#     "9123456789": "1995-08-20",
# }


# # =========================================================
# # RECEPTION AGENT
# # =========================================================

# class ReceptionAgent(Agent):

#     def __init__(self, chat_ctx=None):

#         end_call_tool = EndCallTool(
#             end_instructions=(
#                 "Thank the caller for contacting CityCare Clinic "
#                 "and wish them a good day."
#             )
#         )

#         super().__init__(
#             instructions="""
# You are the Reception Agent for CityCare Clinic.

# Your job is to greet the caller warmly and handle the first part
# of every caller interaction.

# =========================================================
# CITYCARE CLINIC INFORMATION
# =========================================================

# Opening hours:
# - Monday to Friday: 8:00 AM to 6:00 PM
# - Saturday: 9:00 AM to 1:00 PM
# - Sunday: Closed

# Address:
# - 12 Park Road

# Services:
# - General check-up
# - Blood tests
# - Vaccinations
# - Children's doctor

# Parking:
# - Free parking is available behind the building.

# Insurance:
# - Major insurance plans are accepted.

# Only describe services using the documented clinic information.

# For vaccinations, only say "vaccinations".

# Do NOT invent specific vaccine types such as:
# - flu shots
# - COVID shots
# - travel vaccinations
# - childhood vaccines

# =========================================================
# CONTACT INFORMATION
# =========================================================

# The clinic phone number has not been provided.

# Never invent or guess a clinic phone number.

# 12 Park Road is the clinic address, not a phone number.

# If the caller asks for the clinic phone number, explain that
# the phone number is not available in your information.

# =========================================================
# WHEN IDENTITY VERIFICATION IS REQUIRED
# =========================================================

# Identity verification is required ONLY for protected actions.

# Protected actions are:
# - Appointment booking
# - Appointment cancellation
# - Appointment changes
# - Billing information

# Do NOT start identity collection merely because:
# - the caller is confused
# - the caller asks a general question
# - the caller asks about clinic hours
# - the caller asks about services
# - the caller asks about parking
# - the caller asks about insurance
# - the caller asks a general clinic question

# First understand what the caller wants.

# For a normal clinic question, answer directly using the documented
# clinic information.

# For a confused caller who does not know what they need, help them
# understand the documented clinic services first.

# Only begin identity collection when the caller actually requests
# a protected action.

# =========================================================
# STRICT IDENTITY COLLECTION ORDER
# =========================================================

# For a protected action, collect identity in EXACTLY this order:

# 1. Name
# 2. Phone number
# 3. Date of birth
# 4. Verification

# NEVER skip a step.

# NEVER call verify_caller until all three collection tools have
# successfully stored their values.

# The required sequence is:

# collect_name
#     ↓
# SUCCESS
#     ↓
# collect_phone
#     ↓
# SUCCESS
#     ↓
# collect_dob
#     ↓
# SUCCESS
#     ↓
# verify_caller

# =========================================================
# NAME COLLECTION
# =========================================================

# First ask:

# "Could you please provide your full name?"

# WAIT for the caller to actually provide a name.

# Only after the caller provides a name:

# - Call collect_name with the actual name.
# - Wait for the tool result.
# - Do not call collect_phone before collect_name succeeds.

# NEVER call collect_name with:
# - an empty string
# - no argument
# - a guessed name
# - information that the caller did not provide

# If the caller has not provided a name, simply ask for the name.

# If the caller repeats their request, that is NOT a refusal.

# For example:

# Caller:
# "I just want to cancel my appointment."

# This does NOT mean the caller refused verification.

# Explain briefly:

# "To cancel an appointment, I need to verify your identity first."

# Then ask:

# "Could you please provide your full name?"

# Only treat the caller as refusing when they explicitly say things such as:

# "I don't want to provide it."
# "I don't know."
# "I don't remember."
# "I cannot provide it."

# =========================================================
# PHONE COLLECTION
# =========================================================

# Only after collect_name succeeds:

# Ask:

# "Could you please provide your phone number?"

# WAIT for the caller's response.

# Only after the caller provides a phone number:

# - Call collect_phone with the actual phone number.
# - Wait for the result.
# - Do not call collect_dob until collect_phone succeeds.

# NEVER call collect_phone with an empty value.

# NEVER invent a phone number.

# =========================================================
# DATE OF BIRTH COLLECTION
# =========================================================

# Only after collect_phone succeeds:

# Ask:

# "Could you please provide your date of birth?"

# WAIT for the caller's response.

# When the caller provides the DOB:

# 1. Immediately call collect_dob with the actual DOB.
# 2. Wait for the collect_dob result.
# 3. Only after successful storage call verify_caller.

# NEVER call verify_caller immediately after hearing the DOB.

# The DOB must first be successfully stored.

# NEVER call collect_dob with:
# - an empty value
# - no argument
# - an invented DOB

# =========================================================
# VERIFICATION
# =========================================================

# Only call verify_caller after:

# collect_name -> SUCCESS
# collect_phone -> SUCCESS
# collect_dob -> SUCCESS

# If verify_caller returns:

# VERIFICATION_SUCCESS:

# The caller is verified.

# Protected actions may proceed.

# If verify_caller returns:

# VERIFICATION_DOB_MISMATCH:

# Say:

# "The date of birth you provided does not match our records,
# so I can't verify your identity."

# Do NOT reveal the correct DOB.

# Do NOT perform any protected action.

# Do NOT provide billing information.

# Do NOT transfer to BookingAgent or BillingAgent.

# If verify_caller returns another verification failure:

# Clearly state that the caller could not be verified.

# Do not perform any protected action.

# Do not disclose billing information.

# =========================================================
# CALLER REFUSES OR CANNOT PROVIDE INFORMATION
# =========================================================

# Only treat the caller as unable or unwilling to provide
# information when they explicitly say things such as:

# "I don't know."
# "I don't remember."
# "I don't want to provide it."
# "I cannot provide it."

# Do NOT interpret these as refusal:

# "I just want to cancel."
# "I want to book an appointment."
# "I want to change my appointment."
# "Why do you need that?"
# "Can I just cancel it?"
# "I need help cancelling."

# If the caller explicitly refuses or cannot provide the required
# information:

# 1. Explain that verification cannot be completed.
# 2. State that no protected action was taken.
# 3. Do not disclose billing information.
# 4. Tell the caller they can try again later.
# 5. Say goodbye.
# 6. Immediately use end_call.

# Do not repeatedly ask for the same information.

# =========================================================
# TERMINAL FAILURE
# =========================================================

# When verification cannot be completed and the caller cannot
# continue:

# The final sequence MUST be:

# 1. Explain why verification cannot be completed.
# 2. State that no protected action was taken.
# 3. Say goodbye.
# 4. Immediately call end_call.

# Do NOT wait for another caller response.

# Do NOT keep asking for identity information.

# Do NOT finish with only "goodbye".

# The end_call tool must be used.

# =========================================================
# CONFUSED CALLERS
# =========================================================

# If the caller says they are unsure what they need:

# Do NOT start identity verification.

# Explain the documented services:

# - General check-up
# - Blood tests
# - Vaccinations
# - Children's doctor

# Ask which service they would like help with.

# Do not invent additional services.

# =========================================================
# MEDICAL ADVICE
# =========================================================

# Do not diagnose the caller.

# Do not provide medical advice.

# If the caller asks what medicine they should take or asks
# what they should do about symptoms:

# Do not recommend medication.

# Say that you cannot provide medical advice.

# Suggest booking an appointment with the clinic or contacting
# an appropriate qualified healthcare professional.

# =========================================================
# DATE CHANGES
# =========================================================

# If the caller changes their requested appointment date or time:

# Always use the latest date and time provided by the caller.

# =========================================================
# ENDING THE CALL
# =========================================================

# When the caller has no more questions:

# 1. Say goodbye politely.
# 2. Immediately use end_call.

# Be concise, friendly, natural, and professional.
# """,
#             chat_ctx=chat_ctx,
#             tools=end_call_tool.tools,
#         )

#     # =====================================================
#     # ON ENTER
#     # =====================================================

#     async def on_enter(self):

#         await self.session.generate_reply(
#             instructions=(
#                 "Greet the caller warmly and ask how you can help "
#                 "today."
#             )
#         )

#     # =====================================================
#     # HANDOFF TO BOOKING
#     # =====================================================

#     @function_tool()
#     async def go_to_booking(
#         self,
#         context: RunContext[CallerData],
#     ):

#         if not context.userdata.verified:
#             return (
#                 "The caller is not verified yet. "
#                 "Complete identity verification before "
#                 "transferring to appointment booking."
#             )

#         return (
#             BookingAgent(
#                 chat_ctx=self.chat_ctx.copy(
#                     exclude_instructions=True
#                 )
#             ),
#             "Sure, I'll connect you with appointment booking.",
#         )

#     # =====================================================
#     # HANDOFF TO BILLING
#     # =====================================================

#     @function_tool()
#     async def go_to_billing(
#         self,
#         context: RunContext[CallerData],
#     ):

#         if not context.userdata.verified:
#             return (
#                 "The caller is not verified yet. "
#                 "Complete identity verification before "
#                 "transferring to billing."
#             )

#         return (
#             BillingAgent(
#                 chat_ctx=self.chat_ctx.copy(
#                     exclude_instructions=True
#                 )
#             ),
#             "Sure, I'll connect you with billing.",
#         )

#     # =====================================================
#     # COLLECT NAME
#     # =====================================================

#     @function_tool()
#     async def collect_name(
#         self,
#         context: RunContext[CallerData],
#         name: str,
#     ):

#         name = name.strip()

#         if not name:
#             return (
#                 "NAME_COLLECTION_FAILED: no name was provided. "
#                 "Ask the caller for their full name. "
#                 "Do not continue to phone collection."
#             )

#         # Reject obvious non-name request phrases.
#         lowered = name.lower()

#         invalid_phrases = [
#             "i want to cancel",
#             "i want to book",
#             "i want to change",
#             "cancel my appointment",
#             "book an appointment",
#             "change my appointment",
#             "just cancel",
#             "just book",
#         ]

#         if any(phrase in lowered for phrase in invalid_phrases):
#             return (
#                 "NAME_COLLECTION_FAILED: the provided value is not "
#                 "a caller name. Ask the caller for their full name."
#             )

#         context.userdata.name = name

#         return (
#             f"NAME_COLLECTION_SUCCESS: caller name recorded as {name}. "
#             "The name has been successfully stored."
#         )

#     # =====================================================
#     # COLLECT PHONE
#     # =====================================================

#     @function_tool()
#     async def collect_phone(
#         self,
#         context: RunContext[CallerData],
#         phone: str,
#     ):

#         if not context.userdata.name:
#             return (
#                 "PHONE_COLLECTION_BLOCKED: the caller name has not "
#                 "been successfully stored. Collect the name first."
#             )

#         phone = phone.strip()

#         if not phone:
#             return (
#                 "PHONE_COLLECTION_FAILED: no phone number was provided. "
#                 "Ask the caller for their phone number."
#             )

#         normalized_phone = re.sub(r"\D", "", phone)

#         if not normalized_phone:
#             return (
#                 "PHONE_COLLECTION_FAILED: no valid phone number was "
#                 "provided. Ask the caller for their phone number."
#             )

#         context.userdata.phone = normalized_phone

#         return (
#             "PHONE_COLLECTION_SUCCESS: phone number recorded "
#             "successfully. The phone number has been stored."
#         )

#     # =====================================================
#     # COLLECT DOB
#     # =====================================================

#     @function_tool()
#     async def collect_dob(
#         self,
#         context: RunContext[CallerData],
#         dob: str,
#     ):

#         if not context.userdata.name:
#             return (
#                 "DOB_COLLECTION_BLOCKED: the caller name has not "
#                 "been successfully stored. Collect the name first."
#             )

#         if not context.userdata.phone:
#             return (
#                 "DOB_COLLECTION_BLOCKED: the caller phone number has "
#                 "not been successfully stored. Collect the phone "
#                 "number first."
#             )

#         dob = dob.strip()

#         if not dob:
#             return (
#                 "DOB_COLLECTION_FAILED: no date of birth was provided. "
#                 "Ask the caller for their date of birth."
#             )

#         cleaned = re.sub(
#             r"(\d{1,2})(st|nd|rd|th)",
#             r"\1",
#             dob,
#             flags=re.IGNORECASE,
#         )

#         formats = [
#             "%Y-%m-%d",
#             "%B %d %Y",
#             "%B %d, %Y",
#             "%b %d %Y",
#             "%b %d, %Y",
#             "%d %B %Y",
#             "%d %b %Y",
#             "%m/%d/%Y",
#             "%d/%m/%Y",
#         ]

#         normalized_dob = None

#         for fmt in formats:
#             try:
#                 normalized_dob = datetime.strptime(
#                     cleaned,
#                     fmt,
#                 ).date().isoformat()
#                 break
#             except ValueError:
#                 continue

#         if normalized_dob is None:
#             return (
#                 "DOB_COLLECTION_FAILED: the date of birth format "
#                 "could not be understood. Ask the caller to provide "
#                 "their date of birth again."
#             )

#         context.userdata.date_of_birth = normalized_dob

#         return (
#             f"DOB_COLLECTION_SUCCESS: date of birth recorded as "
#             f"{normalized_dob}. The caller's date of birth has been "
#             "successfully stored."
#         )

#     # =====================================================
#     # VERIFY CALLER
#     # =====================================================

#     @function_tool()
#     async def verify_caller(
#         self,
#         context: RunContext[CallerData],
#     ):

#         context.userdata.verified = False

#         name = context.userdata.name
#         phone = context.userdata.phone
#         dob = context.userdata.date_of_birth

#         if not name:
#             return (
#                 "VERIFICATION_BLOCKED: caller name is missing. "
#                 "Collect and successfully store the caller's name first. "
#                 "Do not proceed to verification."
#             )

#         if not phone:
#             return (
#                 "VERIFICATION_BLOCKED: caller phone number is missing. "
#                 "Collect and successfully store the caller's phone number "
#                 "first. Do not proceed to verification."
#             )

#         if not dob:
#             return (
#                 "VERIFICATION_BLOCKED: caller date of birth is missing. "
#                 "Collect and successfully store the caller's date of birth "
#                 "first. Do not proceed to verification."
#             )

#         expected_dob = PATIENT_DOBS.get(phone)

#         if expected_dob is None:
#             return (
#                 "VERIFICATION_FAILED: the caller could not be verified. "
#                 "Do not disclose protected information or perform "
#                 "protected actions."
#             )

#         if dob != expected_dob:
#             return (
#                 "VERIFICATION_DOB_MISMATCH: the date of birth provided by "
#                 "the caller does not match our records. The caller could "
#                 "not be verified. Do not reveal the DOB stored in the "
#                 "records. The caller is not verified and no protected "
#                 "action may be performed."
#             )

#         context.userdata.verified = True

#         return (
#             "VERIFICATION_SUCCESS: the caller has been successfully "
#             "verified. Protected actions may now proceed."
#         )


# # =========================================================
# # BOOKING AGENT
# # =========================================================

# class BookingAgent(Agent):

#     def __init__(self, chat_ctx=None):

#         end_call_tool = EndCallTool(
#             end_instructions=(
#                 "Thank the caller for contacting CityCare Clinic "
#                 "and wish them a good day."
#             )
#         )

#         super().__init__(
#             instructions="""
# You are the Booking Agent for CityCare Clinic.

# The caller has already been verified by the Reception Agent.

# Use the caller information already stored in userdata.

# Do not ask again for:
# - Name
# - Phone number
# - Date of birth

# unless absolutely necessary.

# =========================================================
# NEW APPOINTMENT
# =========================================================

# 1. Ask what service the caller wants.
# 2. Ask for the appointment date.
# 3. Call list_free_slots for that exact date.
# 4. Tell the caller the available times.
# 5. Ask which time they want.
# 6. Repeat:
#    - Service
#    - Date
#    - Time
# 7. Ask for explicit confirmation.
# 8. Only after explicit confirmation call book_appointment
#    with confirmed=True.
# 9. Never book before confirmation.

# Only use documented clinic services:
# - General check-up
# - Blood tests
# - Vaccinations
# - Children's doctor

# Do not invent specific vaccine types.

# =========================================================
# CHANGING AN APPOINTMENT
# =========================================================

# 1. Find the caller's existing appointments.
# 2. Ask which appointment they want to change.
# 3. Ask for the new date and time.
# 4. If the caller changes the date or time, use ONLY the latest value.
# 5. Repeat the new appointment details.
# 6. Ask for explicit confirmation.
# 7. Only after confirmation call change_appointment
#    with confirmed=True.

# If the change fails:
# - Do not claim it succeeded.
# - Clearly say the appointment was not changed.
# - Say the existing appointment remains unchanged.
# - Offer to try again later if appropriate.

# =========================================================
# CANCELLING AN APPOINTMENT
# =========================================================

# 1. Find the caller's existing appointments.
# 2. Ask which appointment they want to cancel.
# 3. Repeat the appointment details.
# 4. Ask for explicit confirmation.
# 5. Only after explicit confirmation call cancel_appointment
#    with confirmed=True.

# If cancellation fails:
# - Do not claim it succeeded.
# - Clearly say the appointment was NOT cancelled.
# - Say the existing appointment remains unchanged.
# - Do not repeatedly retry the same failed operation.
# - If there is no other request, say goodbye and use end_call.

# =========================================================
# SECURITY
# =========================================================

# Never perform appointment operations for an unverified caller.

# If a tool reports that the caller is not verified:
# - Do not bypass verification.
# - Do not repeatedly retry.
# - Return the caller to ReceptionAgent if appropriate.

# =========================================================
# ENDING THE CALL
# =========================================================

# When the request is completed and the caller has no more questions:

# 1. Say goodbye politely.
# 2. Immediately use end_call.

# Do not stop after saying goodbye.

# Be concise, natural, and honest.
# """,
#             chat_ctx=chat_ctx,
#             tools=end_call_tool.tools,
#         )

#     # =====================================================
#     # ON ENTER
#     # =====================================================

#     async def on_enter(self):

#         caller = self.session.userdata

#         await self.session.generate_reply(
#             instructions=(
#                 "The caller is already verified. "
#                 f"Their name is {caller.name}. "
#                 "Ask how you can help with their appointment."
#             )
#         )

#     # =====================================================
#     # LIST FREE SLOTS
#     # =====================================================

#     @function_tool()
#     async def list_free_slots(
#         self,
#         date: str,
#     ):

#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.get(
#                     "http://127.0.0.1:8000/slots",
#                     params={"date": date},
#                 )

#             if response.status_code != 200:
#                 return (
#                     "I could not retrieve the available "
#                     "appointment slots."
#                 )

#             slots = response.json()

#             if not slots:
#                 return (
#                     f"There are no available appointment "
#                     f"slots on {date}."
#                 )

#             return (
#                 f"Available appointment slots on {date}: "
#                 + ", ".join(slots)
#             )

#         except httpx.RequestError:
#             return (
#                 "The appointment service is currently "
#                 "unavailable. Please try again later."
#             )

#     # =====================================================
#     # BOOK APPOINTMENT
#     # =====================================================

#     @function_tool()
#     async def book_appointment(
#         self,
#         context: RunContext[CallerData],
#         date: str,
#         time: str,
#         service: str,
#         confirmed: bool,
#     ):

#         caller = context.userdata

#         if not caller.verified:
#             return (
#                 "The caller is not verified. "
#                 "I cannot book the appointment."
#             )

#         if not caller.name:
#             return "The caller's name is missing."

#         if not caller.phone:
#             return "The caller's phone number is missing."

#         if not confirmed:
#             return (
#                 "The appointment has not been booked. "
#                 "Please explicitly confirm the appointment "
#                 "details first."
#             )

#         payload = {
#             "name": caller.name,
#             "phone": caller.phone,
#             "date": date,
#             "time": time,
#             "service": service,
#         }

#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.post(
#                     "http://127.0.0.1:8000/appointments",
#                     json=payload,
#                 )

#             if response.status_code == 409:
#                 return (
#                     "That appointment time is no longer "
#                     "available. The appointment was not booked. "
#                     "Please choose another time."
#                 )

#             if response.status_code != 200:
#                 return (
#                     "I could not book the appointment. "
#                     "The appointment was not booked. "
#                     "Please try again later."
#                 )

#             data = response.json()

#             appointment = data.get("appointment", {})

#             return (
#                 "The appointment has been booked successfully. "
#                 f"{appointment.get('service', service)} "
#                 f"on {appointment.get('date', date)} "
#                 f"at {appointment.get('time', time)}."
#             )

#         except httpx.RequestError:
#             return (
#                 "The appointment service is currently "
#                 "unavailable. The appointment was not booked."
#             )

#     # =====================================================
#     # FIND EXISTING APPOINTMENTS
#     # =====================================================

#     @function_tool()
#     async def find_my_appointments(
#         self,
#         context: RunContext[CallerData],
#     ):

#         caller = context.userdata

#         if not caller.verified:
#             return "The caller is not verified."

#         if not caller.phone:
#             return "The caller's phone number is missing."

#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.get(
#                     "http://127.0.0.1:8000/appointments",
#                     params={"phone": caller.phone},
#                 )

#             if response.status_code != 200:
#                 return "I could not retrieve your appointments."

#             data = response.json()

#             appointments = data.get("appointments", [])

#             if not appointments:
#                 return (
#                     "I could not find any appointments "
#                     "for this caller."
#                 )

#             appointment_text = []

#             for appointment in appointments:
#                 appointment_text.append(
#                     f"ID {appointment.get('id')}, "
#                     f"{appointment.get('service')}, "
#                     f"{appointment.get('date')} at "
#                     f"{appointment.get('time')}"
#                 )

#             return (
#                 "The caller's appointments are: "
#                 + "; ".join(appointment_text)
#             )

#         except httpx.RequestError:
#             return (
#                 "The appointment service is currently "
#                 "unavailable. Please try again later."
#             )

#     # =====================================================
#     # CANCEL APPOINTMENT
#     # =====================================================

#     @function_tool()
#     async def cancel_appointment(
#         self,
#         context: RunContext[CallerData],
#         appointment_id: int,
#         confirmed: bool,
#     ):

#         caller = context.userdata

#         if not caller.verified:
#             return (
#                 "The caller is not verified. "
#                 "I cannot cancel the appointment."
#             )

#         if not confirmed:
#             return (
#                 "The appointment has not been cancelled. "
#                 "Please explicitly confirm the cancellation."
#             )

#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.delete(
#                     f"http://127.0.0.1:8000/appointments/"
#                     f"{appointment_id}"
#                 )

#             if response.status_code == 404:
#                 return (
#                     "I could not find that appointment. "
#                     "No appointment was cancelled."
#                 )

#             if response.status_code != 200:
#                 return (
#                     "I could not cancel the appointment. "
#                     "The appointment remains unchanged. "
#                     "Please try again later."
#                 )

#             data = response.json()

#             appointment = data.get("appointment", {})

#             return (
#                 "The appointment has been cancelled successfully. "
#                 "The appointment was scheduled for "
#                 f"{appointment.get('date')} at "
#                 f"{appointment.get('time')}."
#             )

#         except httpx.RequestError:
#             return (
#                 "The appointment service is currently "
#                 "unavailable. The appointment remains unchanged "
#                 "and was not cancelled."
#             )

#     # =====================================================
#     # CHANGE APPOINTMENT
#     # =====================================================

#     @function_tool()
#     async def change_appointment(
#         self,
#         context: RunContext[CallerData],
#         appointment_id: int,
#         new_date: str,
#         new_time: str,
#         confirmed: bool,
#     ):

#         caller = context.userdata

#         if not caller.verified:
#             return (
#                 "The caller is not verified. "
#                 "I cannot change the appointment."
#             )

#         if not confirmed:
#             return (
#                 "The appointment has not been changed. "
#                 "Please explicitly confirm the new "
#                 "appointment details."
#             )

#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.patch(
#                     f"http://127.0.0.1:8000/appointments/"
#                     f"{appointment_id}",
#                     json={
#                         "date": new_date,
#                         "time": new_time,
#                     },
#                 )

#             if response.status_code == 404:
#                 return (
#                     "I could not find that appointment. "
#                     "No appointment was changed."
#                 )

#             if response.status_code == 409:
#                 return (
#                     "That new appointment time is not available. "
#                     "The existing appointment remains unchanged. "
#                     "Please choose another time."
#                 )

#             if response.status_code != 200:
#                 return (
#                     "I could not change the appointment. "
#                     "The existing appointment remains unchanged. "
#                     "Please try again later."
#                 )

#             data = response.json()

#             appointment = data.get("appointment", {})

#             return (
#                 "Your appointment has been changed successfully. "
#                 "It is now scheduled for "
#                 f"{appointment.get('date')} at "
#                 f"{appointment.get('time')}."
#             )

#         except httpx.RequestError:
#             return (
#                 "The appointment service is currently "
#                 "unavailable. The existing appointment remains "
#                 "unchanged and was not changed."
#             )

#     # =====================================================
#     # RETURN TO RECEPTION
#     # =====================================================

#     @function_tool()
#     async def return_to_reception(
#         self,
#         context: RunContext[CallerData],
#     ):

#         return (
#             ReceptionAgent(
#                 chat_ctx=self.chat_ctx.copy(
#                     exclude_instructions=True
#                 )
#             ),
#             "I'll return you to reception for "
#             "further assistance.",
#         )


# # =========================================================
# # BILLING AGENT
# # =========================================================

# class BillingAgent(Agent):

#     def __init__(self, chat_ctx=None):

#         end_call_tool = EndCallTool(
#             end_instructions=(
#                 "Thank the caller for contacting CityCare Clinic "
#                 "and wish them a good day."
#             )
#         )

#         super().__init__(
#             instructions="""
# You are the Billing Agent for CityCare Clinic.

# The caller has already been identified and verified by
# the Reception Agent.

# Use the caller information already stored in userdata.

# Do not ask again for:
# - Name
# - Phone number
# - Date of birth

# Only provide billing information after successful identity
# verification.

# If the caller is not verified:
# - Do not disclose billing information.
# - Do not repeatedly ask for verification information.
# - Return the caller to ReceptionAgent if appropriate.

# If billing cannot be completed because verification or the
# billing service failed:
# - Clearly explain that no billing information was disclosed.
# - Do not invent billing information.
# - Do not repeatedly retry a failed operation.
# - If no recovery is possible, say goodbye and immediately use end_call.

# When the billing task is complete and the caller has no more
# questions:
# - Say goodbye.
# - Immediately use end_call.

# Do not stop after saying goodbye.

# Be concise, natural, and professional.
# """,
#             chat_ctx=chat_ctx,
#             tools=end_call_tool.tools,
#         )

#     # =====================================================
#     # ON ENTER
#     # =====================================================

#     async def on_enter(self):

#         caller = self.session.userdata

#         await self.session.generate_reply(
#             instructions=(
#                 "The caller is already verified. "
#                 f"Their name is {caller.name}. "
#                 "Ask how you can help with billing."
#             )
#         )

#     # =====================================================
#     # GET BILL
#     # =====================================================

#     @function_tool()
#     async def get_bill(
#         self,
#         context: RunContext[CallerData],
#     ):

#         caller = context.userdata

#         if not caller.verified:
#             return (
#                 "The caller is not verified. "
#                 "I cannot provide billing information. "
#                 "No billing information was disclosed."
#             )

#         if not caller.phone:
#             return (
#                 "The caller's phone number is missing. "
#                 "I cannot provide billing information."
#             )

#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.get(
#                     "http://127.0.0.1:8000/bills",
#                     params={"phone": caller.phone},
#                 )

#             if response.status_code != 200:
#                 return (
#                     "I could not retrieve the billing information. "
#                     "No billing information was disclosed."
#                 )

#             data = response.json()

#             amount = data.get("bill_amount")
#             due_date = data.get("due_date")

#             if amount is None and due_date is None:
#                 return "No billing information was found."

#             return (
#                 f"Your current bill amount is {amount}. "
#                 f"The due date is {due_date}."
#             )

#         except httpx.RequestError:
#             return (
#                 "The billing service is currently unavailable. "
#                 "No billing information was disclosed."
#             )

#     # =====================================================
#     # RETURN TO RECEPTION
#     # =====================================================

#     @function_tool()
#     async def return_to_reception(
#         self,
#         context: RunContext[CallerData],
#     ):

#         return (
#             ReceptionAgent(
#                 chat_ctx=self.chat_ctx.copy(
#                     exclude_instructions=True
#                 )
#             ),
#             "I'll return you to reception for "
#             "further assistance.",
#         )

import httpx
import re
from datetime import datetime
from typing import Annotated

from pydantic import Field

from livekit.agents import Agent, RunContext, function_tool
from livekit.agents.beta.tools import EndCallTool

from src.userdata import CallerData


# =========================================================
# DEMO PATIENT RECORDS
# =========================================================

PATIENT_DOBS = {
    "9876543210": "1998-05-10",
    "9123456789": "1995-08-20",
}


# =========================================================
# RECEPTION AGENT
# =========================================================

class ReceptionAgent(Agent):

    def __init__(self, chat_ctx=None):

        end_call_tool = EndCallTool(
            extra_description=(
                "This is a ONE-SHOT terminal tool. Call end_call at most once. "
                "Never call end_call twice. Do not call any other tool after "
                "end_call. Use it only when the call is truly finished."
            ),
            end_instructions=(
                "Generate one concise final response for the caller. "
                "If a failure or refusal occurred, briefly explain that the "
                "requested protected action was not completed. Then thank "
                "the caller for contacting CityCare Clinic, wish them a good "
                "day, and say goodbye. Do not ask another question and do "
                "not call any other tool."
            ),
            ignore_on_enter=True,
        )

        super().__init__(
            instructions="""
You are the Reception Agent for CityCare Clinic.

Your job is to greet the caller warmly and handle the first part
of every caller interaction.

=========================================================
CITYCARE CLINIC INFORMATION
=========================================================

Opening hours:
- Monday to Friday: 8:00 AM to 6:00 PM
- Saturday: 9:00 AM to 1:00 PM
- Sunday: Closed

Address:
- 12 Park Road

Services:
- General check-up
- Blood tests
- Vaccinations
- Children's doctor

Parking:
- Free parking is available behind the building.

Insurance:
- Major insurance plans are accepted.

Only describe services using the documented clinic information.

For vaccinations, only say "vaccinations".

Do NOT invent specific vaccine types such as:
- flu shots
- COVID shots
- travel vaccinations
- childhood vaccines

=========================================================
CONTACT INFORMATION
=========================================================

The clinic phone number has not been provided.

Never invent or guess a clinic phone number.

12 Park Road is the clinic address, not a phone number.

If the caller asks for the clinic phone number, explain that
the phone number is not available in your information.

=========================================================
WHEN IDENTITY VERIFICATION IS REQUIRED
=========================================================

Identity verification is required ONLY for protected actions.

Protected actions are:
- Appointment booking
- Appointment cancellation
- Appointment changes
- Billing information

Do NOT start identity collection merely because:
- the caller is confused
- the caller asks a general question
- the caller asks about clinic hours
- the caller asks about services
- the caller asks about parking
- the caller asks about insurance
- the caller asks a general clinic question

First understand what the caller wants.

For a normal clinic question, answer directly using the documented
clinic information.

For a confused caller who does not know what they need, help them
understand the documented clinic services first.

Only begin identity collection when the caller actually requests
a protected action.

=========================================================
STRICT IDENTITY COLLECTION ORDER
=========================================================

For a protected action, collect identity in EXACTLY this order:

1. Name
2. Phone number
3. Date of birth
4. Verification

NEVER skip a step.

NEVER call verify_caller until all three collection tools have
successfully stored their values.

The required sequence is:

collect_name
    ↓
SUCCESS
    ↓
collect_phone
    ↓
SUCCESS
    ↓
collect_dob
    ↓
SUCCESS
    ↓
verify_caller

=========================================================
NAME COLLECTION
=========================================================

First ask:

"Could you please provide your full name?"

WAIT for the caller to actually provide a name.

Only after the caller provides a name:

- Call collect_name with the actual name.
- Wait for the tool result.
- Do not call collect_phone before collect_name succeeds.

NEVER call collect_name with:
- an empty string
- no argument
- a guessed name
- information that the caller did not provide

If the caller has not provided a name, simply ask for the name.

CRITICAL TOOL-GATING RULE:
- Do NOT call collect_name in the same response in which you ask for the name.
- First ask the caller for the name and wait for their next utterance.
- Only then call collect_name with the non-empty name from that utterance.
- Never call collect_name with "" or any empty/placeholder value.
- If the caller has not answered the name question yet, do not call any identity collection tool.

If the caller repeats their request, that is NOT a refusal.

For example:

Caller:
"I just want to cancel my appointment."

This does NOT mean the caller refused verification.

Explain briefly:

"To cancel an appointment, I need to verify your identity first."

Then ask:

"Could you please provide your full name?"

Only treat the caller as refusing when they explicitly say things such as:

"I don't want to provide it."
"I don't know."
"I don't remember."
"I cannot provide it."

=========================================================
PHONE COLLECTION
=========================================================

Only after collect_name succeeds:

Ask:

"Could you please provide your phone number?"

WAIT for the caller's response.

Only after the caller provides a phone number:

- Call collect_phone with the actual phone number.
- Wait for the result.
- Do not call collect_dob until collect_phone succeeds.

NEVER call collect_phone with an empty value.

NEVER invent a phone number.

=========================================================
DATE OF BIRTH COLLECTION
=========================================================

Only after collect_phone succeeds:

Ask:

"Could you please provide your date of birth?"

WAIT for the caller's response.

When the caller provides the DOB:

1. Immediately call collect_dob with the actual DOB.
2. Wait for the collect_dob result.
3. Only after successful storage call verify_caller.

NEVER call verify_caller immediately after hearing the DOB.

The DOB must first be successfully stored.

NEVER call collect_dob with:
- an empty value
- no argument
- an invented DOB

=========================================================
VERIFICATION
=========================================================

Only call verify_caller after:

collect_name -> SUCCESS
collect_phone -> SUCCESS
collect_dob -> SUCCESS

If verify_caller returns:

VERIFICATION_SUCCESS:

The caller is verified.

Protected actions may proceed.

If verify_caller returns:

VERIFICATION_DOB_MISMATCH:

Say:

"The date of birth you provided does not match our records,
so I can't verify your identity."

Do NOT reveal the correct DOB.

Do NOT perform any protected action.

Do NOT provide billing information.

Do NOT transfer to BookingAgent or BillingAgent.

If verify_caller returns another verification failure:

Clearly state that the caller could not be verified.

Do not perform any protected action.

Do not disclose billing information.

=========================================================
CALLER REFUSES OR CANNOT PROVIDE INFORMATION
=========================================================

Only treat the caller as unable or unwilling to provide
information when they explicitly say things such as:

"I don't know."
"I don't remember."
"I don't want to provide it."
"I cannot provide it."

Do NOT interpret these as refusal:

"I just want to cancel."
"I want to book an appointment."
"I want to change my appointment."
"Why do you need that?"
"Can I just cancel it?"
"I need help cancelling."

If the caller explicitly refuses or cannot provide the required
information:

1. Explain that verification cannot be completed.
2. State that no protected action was taken.
3. Do not disclose billing information.
4. Tell the caller they can try again later.
5. Say goodbye.
6. Immediately use end_call.

Do not repeatedly ask for the same information.

=========================================================
TERMINAL FAILURE
=========================================================

When verification cannot be completed and the caller cannot
continue:

The final sequence MUST be:

1. Explain why verification cannot be completed.
2. State that no protected action was taken.
3. Say goodbye.
4. Immediately call end_call.

Do NOT wait for another caller response.

Do NOT keep asking for identity information.

Do NOT finish with only "goodbye".

The end_call tool must be used exactly once for a terminal call.
After invoking end_call, do not invoke end_call again and do not invoke any other tool.
Do not call end_call during the initial greeting.

=========================================================
CONFUSED CALLERS
=========================================================

If the caller says they are unsure what they need:

Do NOT start identity verification.

Explain the documented services:

- General check-up
- Blood tests
- Vaccinations
- Children's doctor

Ask which service they would like help with.

Do not invent additional services.

=========================================================
MEDICAL ADVICE
=========================================================

Do not diagnose the caller.

Do not provide medical advice.

If the caller asks what medicine they should take or asks
what they should do about symptoms:

Do not recommend medication.

Say that you cannot provide medical advice.

Suggest booking an appointment with the clinic or contacting
an appropriate qualified healthcare professional.

=========================================================
DATE CHANGES
=========================================================

If the caller changes their requested appointment date or time:

Always use the latest date and time provided by the caller.

=========================================================
ENDING THE CALL
=========================================================

When the caller has no more questions:

1. Say goodbye politely.
2. Immediately use end_call.

Be concise, friendly, natural, and professional.
""",
            chat_ctx=chat_ctx,
            tools=end_call_tool.tools,
        )

    # =====================================================
    # ON ENTER
    # =====================================================

    async def on_enter(self):

        await self.session.generate_reply(
            instructions=(
                "Greet the caller warmly and ask how you can help "
                "today."
            )
        )

    # =====================================================
    # HANDOFF TO BOOKING
    # =====================================================

    @function_tool()
    async def go_to_booking(
        self,
        context: RunContext[CallerData],
    ):

        if not context.userdata.verified:
            return (
                "The caller is not verified yet. "
                "Complete identity verification before "
                "transferring to appointment booking."
            )

        return (
            BookingAgent(
                chat_ctx=self.chat_ctx.copy(
                    exclude_instructions=True
                )
            ),
            "Sure, I'll connect you with appointment booking.",
        )

    # =====================================================
    # HANDOFF TO BILLING
    # =====================================================

    @function_tool()
    async def go_to_billing(
        self,
        context: RunContext[CallerData],
    ):

        if not context.userdata.verified:
            return (
                "The caller is not verified yet. "
                "Complete identity verification before "
                "transferring to billing."
            )

        return (
            BillingAgent(
                chat_ctx=self.chat_ctx.copy(
                    exclude_instructions=True
                )
            ),
            "Sure, I'll connect you with billing.",
        )

    # =====================================================
    # COLLECT NAME
    # =====================================================

    @function_tool()
    async def collect_name(
        self,
        context: RunContext[CallerData],
        name: Annotated[
            str,
            Field(
                min_length=1,
                description=(
                    "The caller's actual non-empty full name exactly as "
                    "provided by the caller. Never use an empty string."
                ),
            ),
        ],
    ):
        """Store the caller's name only after the caller has actually provided it.
        Never call this tool with an empty value or before asking for the name.
        """

        name = name.strip()

        if not name:
            return (
                "NAME_COLLECTION_FAILED: no name was provided. "
                "Ask the caller for their full name. "
                "Do not continue to phone collection."
            )

        # Reject obvious non-name request phrases.
        lowered = name.lower()

        invalid_phrases = [
            "i want to cancel",
            "i want to book",
            "i want to change",
            "cancel my appointment",
            "book an appointment",
            "change my appointment",
            "just cancel",
            "just book",
        ]

        if any(phrase in lowered for phrase in invalid_phrases):
            return (
                "NAME_COLLECTION_FAILED: the provided value is not "
                "a caller name. Ask the caller for their full name."
            )

        context.userdata.name = name

        return (
            f"NAME_COLLECTION_SUCCESS: caller name recorded as {name}. "
            "The name has been successfully stored."
        )

    # =====================================================
    # COLLECT PHONE
    # =====================================================

    @function_tool()
    async def collect_phone(
        self,
        context: RunContext[CallerData],
        phone: Annotated[
            str,
            Field(
                min_length=1,
                description=(
                    "The caller's actual non-empty phone number exactly as "
                    "provided by the caller. Never use an empty string."
                ),
            ),
        ],
    ):
        """Store the caller's phone only after the caller has actually provided it.
        Never call this tool with an empty value.
        """

        if not context.userdata.name:
            return (
                "PHONE_COLLECTION_BLOCKED: the caller name has not "
                "been successfully stored. Collect the name first."
            )

        phone = phone.strip()

        if not phone:
            return (
                "PHONE_COLLECTION_FAILED: no phone number was provided. "
                "Ask the caller for their phone number."
            )

        normalized_phone = re.sub(r"\D", "", phone)

        if not normalized_phone:
            return (
                "PHONE_COLLECTION_FAILED: no valid phone number was "
                "provided. Ask the caller for their phone number."
            )

        context.userdata.phone = normalized_phone

        return (
            "PHONE_COLLECTION_SUCCESS: phone number recorded "
            "successfully. The phone number has been stored."
        )

    # =====================================================
    # COLLECT DOB
    # =====================================================

    @function_tool()
    async def collect_dob(
        self,
        context: RunContext[CallerData],
        dob: Annotated[
            str,
            Field(
                min_length=1,
                description=(
                    "The caller's actual non-empty date of birth exactly as "
                    "provided by the caller. Never use an empty string."
                ),
            ),
        ],
    ):
        """Store the caller's DOB only after the caller has actually provided it.
        Never call this tool with an empty value.
        """

        if not context.userdata.name:
            return (
                "DOB_COLLECTION_BLOCKED: the caller name has not "
                "been successfully stored. Collect the name first."
            )

        if not context.userdata.phone:
            return (
                "DOB_COLLECTION_BLOCKED: the caller phone number has "
                "not been successfully stored. Collect the phone "
                "number first."
            )

        dob = dob.strip()

        if not dob:
            return (
                "DOB_COLLECTION_FAILED: no date of birth was provided. "
                "Ask the caller for their date of birth."
            )

        cleaned = re.sub(
            r"(\d{1,2})(st|nd|rd|th)",
            r"\1",
            dob,
            flags=re.IGNORECASE,
        )

        formats = [
            "%Y-%m-%d",
            "%B %d %Y",
            "%B %d, %Y",
            "%b %d %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]

        normalized_dob = None

        for fmt in formats:
            try:
                normalized_dob = datetime.strptime(
                    cleaned,
                    fmt,
                ).date().isoformat()
                break
            except ValueError:
                continue

        if normalized_dob is None:
            return (
                "DOB_COLLECTION_FAILED: the date of birth format "
                "could not be understood. Ask the caller to provide "
                "their date of birth again."
            )

        context.userdata.date_of_birth = normalized_dob

        return (
            f"DOB_COLLECTION_SUCCESS: date of birth recorded as "
            f"{normalized_dob}. The caller's date of birth has been "
            "successfully stored."
        )

    # =====================================================
    # VERIFY CALLER
    # =====================================================

    @function_tool()
    async def verify_caller(
        self,
        context: RunContext[CallerData],
    ):

        context.userdata.verified = False

        name = context.userdata.name
        phone = context.userdata.phone
        dob = context.userdata.date_of_birth

        if not name:
            return (
                "VERIFICATION_BLOCKED: caller name is missing. "
                "Collect and successfully store the caller's name first. "
                "Do not proceed to verification."
            )

        if not phone:
            return (
                "VERIFICATION_BLOCKED: caller phone number is missing. "
                "Collect and successfully store the caller's phone number "
                "first. Do not proceed to verification."
            )

        if not dob:
            return (
                "VERIFICATION_BLOCKED: caller date of birth is missing. "
                "Collect and successfully store the caller's date of birth "
                "first. Do not proceed to verification."
            )

        expected_dob = PATIENT_DOBS.get(phone)

        if expected_dob is None:
            return (
                "VERIFICATION_FAILED: the caller could not be verified. "
                "Do not disclose protected information or perform "
                "protected actions."
            )

        if dob != expected_dob:
            return (
                "VERIFICATION_DOB_MISMATCH: the date of birth provided by "
                "the caller does not match our records. The caller could "
                "not be verified. Do not reveal the DOB stored in the "
                "records. The caller is not verified and no protected "
                "action may be performed."
            )

        context.userdata.verified = True

        return (
            "VERIFICATION_SUCCESS: the caller has been successfully "
            "verified. Protected actions may now proceed."
        )


# =========================================================
# BOOKING AGENT
# =========================================================

class BookingAgent(Agent):

    def __init__(self, chat_ctx=None):

        end_call_tool = EndCallTool(
            extra_description=(
                "This is a ONE-SHOT terminal tool. Call end_call at most once. "
                "Never call end_call twice. Do not call any other tool after "
                "end_call. Use it only when the call is truly finished."
            ),
            end_instructions=(
                "Generate one concise final response for the caller. "
                "If a failure or refusal occurred, briefly explain that the "
                "requested protected action was not completed. Then thank "
                "the caller for contacting CityCare Clinic, wish them a good "
                "day, and say goodbye. Do not ask another question and do "
                "not call any other tool."
            ),
            ignore_on_enter=True,
        )

        super().__init__(
            instructions="""
You are the Booking Agent for CityCare Clinic.

The caller has already been verified by the Reception Agent.

Use the caller information already stored in userdata.

Do not ask again for:
- Name
- Phone number
- Date of birth

unless absolutely necessary.

=========================================================
NEW APPOINTMENT
=========================================================

1. Ask what service the caller wants.
2. Ask for the appointment date.
3. Call list_free_slots for that exact date.
4. Tell the caller the available times.
5. Ask which time they want.
6. Repeat:
   - Service
   - Date
   - Time
7. Ask for explicit confirmation.
8. Only after explicit confirmation call book_appointment
   with confirmed=True.
9. Never book before confirmation.

Only use documented clinic services:
- General check-up
- Blood tests
- Vaccinations
- Children's doctor

Do not invent specific vaccine types.

=========================================================
CHANGING AN APPOINTMENT
=========================================================

1. Find the caller's existing appointments.
2. Ask which appointment they want to change.
3. Ask for the new date and time.
4. If the caller changes the date or time, use ONLY the latest value.
5. Repeat the new appointment details.
6. Ask for explicit confirmation.
7. Only after confirmation call change_appointment
   with confirmed=True.

If the change fails:
- Do not claim it succeeded.
- Clearly say the appointment was not changed.
- Say the existing appointment remains unchanged.
- Offer to try again later if appropriate.

=========================================================
CANCELLING AN APPOINTMENT
=========================================================

1. Find the caller's existing appointments.
2. Ask which appointment they want to cancel.
3. Repeat the appointment details.
4. Ask for explicit confirmation.
5. Only after explicit confirmation call cancel_appointment
   with confirmed=True.

If cancellation fails:
- Do not claim it succeeded.
- Clearly say the appointment was NOT cancelled.
- Say the existing appointment remains unchanged.
- Do not repeatedly retry the same failed operation.
- If there is no other request, say goodbye and use end_call.

=========================================================
SECURITY
=========================================================

Never perform appointment operations for an unverified caller.

If a tool reports that the caller is not verified:
- Do not bypass verification.
- Do not repeatedly retry.
- Return the caller to ReceptionAgent if appropriate.

=========================================================
ENDING THE CALL
=========================================================

When the request is completed and the caller has no more questions:

1. Say goodbye politely.
2. Immediately use end_call.

Do not stop after saying goodbye.

For a terminal outcome, use end_call exactly once. Never invoke end_call twice
and never invoke another tool after end_call.

Be concise, natural, and honest.
""",
            chat_ctx=chat_ctx,
            tools=end_call_tool.tools,
        )

    # =====================================================
    # ON ENTER
    # =====================================================

    async def on_enter(self):

        caller = self.session.userdata

        await self.session.generate_reply(
            instructions=(
                "The caller is already verified. "
                f"Their name is {caller.name}. "
                "Ask how you can help with their appointment."
            )
        )

    # =====================================================
    # LIST FREE SLOTS
    # =====================================================

    @function_tool()
    async def list_free_slots(
        self,
        date: str,
    ):

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://127.0.0.1:8000/slots",
                    params={"date": date},
                )

            if response.status_code != 200:
                return (
                    "I could not retrieve the available "
                    "appointment slots."
                )

            slots = response.json()

            if not slots:
                return (
                    f"There are no available appointment "
                    f"slots on {date}."
                )

            return (
                f"Available appointment slots on {date}: "
                + ", ".join(slots)
            )

        except httpx.RequestError:
            return (
                "The appointment service is currently "
                "unavailable. Please try again later."
            )

    # =====================================================
    # BOOK APPOINTMENT
    # =====================================================

    @function_tool()
    async def book_appointment(
        self,
        context: RunContext[CallerData],
        date: str,
        time: str,
        service: str,
        confirmed: bool,
    ):

        caller = context.userdata

        if not caller.verified:
            return (
                "The caller is not verified. "
                "I cannot book the appointment."
            )

        if not caller.name:
            return "The caller's name is missing."

        if not caller.phone:
            return "The caller's phone number is missing."

        if not confirmed:
            return (
                "The appointment has not been booked. "
                "Please explicitly confirm the appointment "
                "details first."
            )

        payload = {
            "name": caller.name,
            "phone": caller.phone,
            "date": date,
            "time": time,
            "service": service,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://127.0.0.1:8000/appointments",
                    json=payload,
                )

            if response.status_code == 409:
                return (
                    "That appointment time is no longer "
                    "available. The appointment was not booked. "
                    "Please choose another time."
                )

            if response.status_code != 200:
                return (
                    "I could not book the appointment. "
                    "The appointment was not booked. "
                    "Please try again later."
                )

            data = response.json()

            appointment = data.get("appointment", {})

            return (
                "The appointment has been booked successfully. "
                f"{appointment.get('service', service)} "
                f"on {appointment.get('date', date)} "
                f"at {appointment.get('time', time)}."
            )

        except httpx.RequestError:
            return (
                "The appointment service is currently "
                "unavailable. The appointment was not booked."
            )

    # =====================================================
    # FIND EXISTING APPOINTMENTS
    # =====================================================

    @function_tool()
    async def find_my_appointments(
        self,
        context: RunContext[CallerData],
    ):

        caller = context.userdata

        if not caller.verified:
            return "The caller is not verified."

        if not caller.phone:
            return "The caller's phone number is missing."

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://127.0.0.1:8000/appointments",
                    params={"phone": caller.phone},
                )

            if response.status_code != 200:
                return "I could not retrieve your appointments."

            data = response.json()

            appointments = data.get("appointments", [])

            if not appointments:
                return (
                    "I could not find any appointments "
                    "for this caller."
                )

            appointment_text = []

            for appointment in appointments:
                appointment_text.append(
                    f"ID {appointment.get('id')}, "
                    f"{appointment.get('service')}, "
                    f"{appointment.get('date')} at "
                    f"{appointment.get('time')}"
                )

            return (
                "The caller's appointments are: "
                + "; ".join(appointment_text)
            )

        except httpx.RequestError:
            return (
                "The appointment service is currently "
                "unavailable. Please try again later."
            )

    # =====================================================
    # CANCEL APPOINTMENT
    # =====================================================

    @function_tool()
    async def cancel_appointment(
        self,
        context: RunContext[CallerData],
        appointment_id: int,
        confirmed: bool,
    ):

        caller = context.userdata

        if not caller.verified:
            return (
                "The caller is not verified. "
                "I cannot cancel the appointment."
            )

        if not confirmed:
            return (
                "The appointment has not been cancelled. "
                "Please explicitly confirm the cancellation."
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"http://127.0.0.1:8000/appointments/"
                    f"{appointment_id}"
                )

            if response.status_code == 404:
                return (
                    "I could not find that appointment. "
                    "No appointment was cancelled."
                )

            if response.status_code != 200:
                return (
                    "I could not cancel the appointment. "
                    "The appointment remains unchanged. "
                    "Please try again later."
                )

            data = response.json()

            appointment = data.get("appointment", {})

            return (
                "The appointment has been cancelled successfully. "
                "The appointment was scheduled for "
                f"{appointment.get('date')} at "
                f"{appointment.get('time')}."
            )

        except httpx.RequestError:
            return (
                "The appointment service is currently "
                "unavailable. The appointment remains unchanged "
                "and was not cancelled."
            )

    # =====================================================
    # CHANGE APPOINTMENT
    # =====================================================

    @function_tool()
    async def change_appointment(
        self,
        context: RunContext[CallerData],
        appointment_id: int,
        new_date: str,
        new_time: str,
        confirmed: bool,
    ):

        caller = context.userdata

        if not caller.verified:
            return (
                "The caller is not verified. "
                "I cannot change the appointment."
            )

        if not confirmed:
            return (
                "The appointment has not been changed. "
                "Please explicitly confirm the new "
                "appointment details."
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"http://127.0.0.1:8000/appointments/"
                    f"{appointment_id}",
                    json={
                        "date": new_date,
                        "time": new_time,
                    },
                )

            if response.status_code == 404:
                return (
                    "I could not find that appointment. "
                    "No appointment was changed."
                )

            if response.status_code == 409:
                return (
                    "That new appointment time is not available. "
                    "The existing appointment remains unchanged. "
                    "Please choose another time."
                )

            if response.status_code != 200:
                return (
                    "I could not change the appointment. "
                    "The existing appointment remains unchanged. "
                    "Please try again later."
                )

            data = response.json()

            appointment = data.get("appointment", {})

            return (
                "Your appointment has been changed successfully. "
                "It is now scheduled for "
                f"{appointment.get('date')} at "
                f"{appointment.get('time')}."
            )

        except httpx.RequestError:
            return (
                "The appointment service is currently "
                "unavailable. The existing appointment remains "
                "unchanged and was not changed."
            )

    # =====================================================
    # RETURN TO RECEPTION
    # =====================================================

    @function_tool()
    async def return_to_reception(
        self,
        context: RunContext[CallerData],
    ):

        return (
            ReceptionAgent(
                chat_ctx=self.chat_ctx.copy(
                    exclude_instructions=True
                )
            ),
            "I'll return you to reception for "
            "further assistance.",
        )


# =========================================================
# BILLING AGENT
# =========================================================

class BillingAgent(Agent):

    def __init__(self, chat_ctx=None):

        end_call_tool = EndCallTool(
            extra_description=(
                "This is a ONE-SHOT terminal tool. Call end_call at most once. "
                "Never call end_call twice. Do not call any other tool after "
                "end_call. Use it only when the call is truly finished."
            ),
            end_instructions=(
                "Generate one concise final response for the caller. "
                "If a failure or refusal occurred, briefly explain that the "
                "requested protected action was not completed. Then thank "
                "the caller for contacting CityCare Clinic, wish them a good "
                "day, and say goodbye. Do not ask another question and do "
                "not call any other tool."
            ),
            ignore_on_enter=True,
        )

        super().__init__(
            instructions="""
You are the Billing Agent for CityCare Clinic.

The caller has already been identified and verified by
the Reception Agent.

Use the caller information already stored in userdata.

Do not ask again for:
- Name
- Phone number
- Date of birth

Only provide billing information after successful identity
verification.

If the caller is not verified:
- Do not disclose billing information.
- Do not repeatedly ask for verification information.
- Return the caller to ReceptionAgent if appropriate.

If billing cannot be completed because verification or the
billing service failed:
- Clearly explain that no billing information was disclosed.
- Do not invent billing information.
- Do not repeatedly retry a failed operation.
- If no recovery is possible, say goodbye and immediately use end_call.

When the billing task is complete and the caller has no more
questions:
- Say goodbye.
- Immediately use end_call.

Do not stop after saying goodbye.

For a terminal outcome, use end_call exactly once. Never invoke end_call twice
and never invoke another tool after end_call.

Be concise, natural, and professional.
""",
            chat_ctx=chat_ctx,
            tools=end_call_tool.tools,
        )

    # =====================================================
    # ON ENTER
    # =====================================================

    async def on_enter(self):

        caller = self.session.userdata

        await self.session.generate_reply(
            instructions=(
                "The caller is already verified. "
                f"Their name is {caller.name}. "
                "Ask how you can help with billing."
            )
        )

    # =====================================================
    # GET BILL
    # =====================================================

    @function_tool()
    async def get_bill(
        self,
        context: RunContext[CallerData],
    ):

        caller = context.userdata

        if not caller.verified:
            return (
                "The caller is not verified. "
                "I cannot provide billing information. "
                "No billing information was disclosed. "
                "This is a terminal outcome: give the caller a brief goodbye "
                "and call end_call exactly once."
            )

        if not caller.phone:
            return (
                "The caller's phone number is missing. "
                "I cannot provide billing information."
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://127.0.0.1:8000/bills",
                    params={"phone": caller.phone},
                )

            if response.status_code != 200:
                return (
                    "I could not retrieve the billing information. "
                    "No billing information was disclosed. "
                    "This is a terminal outcome if the caller has no other "
                    "request: give a brief goodbye and call end_call exactly once."
                )

            data = response.json()

            amount = data.get("bill_amount")
            due_date = data.get("due_date")

            if amount is None and due_date is None:
                return "No billing information was found."

            return (
                f"Your current bill amount is {amount}. "
                f"The due date is {due_date}."
            )

        except httpx.RequestError:
            return (
                "The billing service is currently unavailable. "
                "No billing information was disclosed."
            )

    # =====================================================
    # RETURN TO RECEPTION
    # =====================================================

    @function_tool()
    async def return_to_reception(
        self,
        context: RunContext[CallerData],
    ):

        return (
            ReceptionAgent(
                chat_ctx=self.chat_ctx.copy(
                    exclude_instructions=True
                )
            ),
            "I'll return you to reception for "
            "further assistance.",
        )