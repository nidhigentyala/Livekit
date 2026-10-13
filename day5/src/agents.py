import httpx
import re

from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Optional

from livekit.agents import Agent, RunContext, function_tool
from livekit.agents.beta.tools import EndCallTool

from .userdata import CallerData


# ============================================================
# DEMO PATIENT RECORDS
# ============================================================

PATIENT_DOBS = {
    "9876543210": "1998-05-10",
    "9123456789": "1995-08-20",
}


# ============================================================
# COMMON HELPERS
# ============================================================

def normalize_phone(phone: str) -> str:
    """Keep digits only."""
    return re.sub(r"\D", "", phone or "")


def normalize_name(name: str) -> str:
    """Normalize whitespace and capitalization."""
    return " ".join((name or "").strip().split())


_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}

_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
    "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
    "twenty-first": 21, "twenty-second": 22, "twenty-third": 23,
    "twenty-fourth": 24, "twenty-fifth": 25, "twenty-sixth": 26,
    "twenty-seventh": 27, "twenty-eighth": 28, "twenty-ninth": 29,
    "thirtieth": 30, "thirty-first": 31,
}


def _words_to_number(text: str) -> Optional[int]:
    """Convert a small English number phrase to an integer."""
    text = re.sub(r"[-,]", " ", text.lower()).strip()
    if not text:
        return None

    if text in _ORDINAL_WORDS:
        return _ORDINAL_WORDS[text]
    if text in _NUMBER_WORDS:
        return _NUMBER_WORDS[text]

    parts = text.split()
    if len(parts) == 2 and parts[0] in _NUMBER_WORDS and parts[1] in _NUMBER_WORDS:
        a = _NUMBER_WORDS[parts[0]]
        b = _NUMBER_WORDS[parts[1]]
        if a >= 20 and b < 10:
            return a + b

    return None


def _normalize_spoken_dob(raw: str) -> Optional[str]:
    """Handle DOBs spoken fully or partly in words."""
    cleaned = re.sub(r"[^a-zA-Z0-9,\\-\\s]", " ", raw.lower())
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    cleaned = cleaned.replace(" of ", " ")

    month_names = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10,
        "nov": 11, "dec": 12,
    }

    tokens = cleaned.replace(",", " , ").split()
    month_index = next((i for i, t in enumerate(tokens) if t in month_names), None)
    if month_index is None:
        return None

    month = month_names[tokens[month_index]]
    remaining = [t for i, t in enumerate(tokens) if i != month_index and t != ","]

    # Find a 4-digit year first.
    year = None
    year_index = None
    for i, token in enumerate(remaining):
        if token.isdigit() and len(token) == 4:
            year = int(token)
            year_index = i
            break

    # Spoken year such as "nineteen ninety-eight" or "two thousand five".
    if year is None:
        for n in range(len(remaining)):
            phrase = " ".join(remaining[n:n+3])
            words = phrase.replace("-", " ").split()
            if len(words) >= 2 and words[0] in {"nineteen", "eighteen", "seventeen", "twenty"}:
                base = _NUMBER_WORDS.get(words[0])
                tail = _words_to_number(" ".join(words[1:]))
                if base in {17, 18, 19} and tail is not None and tail < 100:
                    year = base * 100 + tail
                    year_index = n
                    break
                if base == 20 and tail is not None and tail < 100:
                    year = base * 100 + tail
                    year_index = n
                    break
            if len(words) >= 3 and words[0] == "two" and words[1] == "thousand":
                tail = _words_to_number(" ".join(words[2:])) or 0
                year = 2000 + tail
                year_index = n
                break

    if year is None:
        return None

    # The remaining non-year portion should contain the day.
    day_candidates = []
    for i, token in enumerate(remaining):
        if year_index is not None and i == year_index:
            continue
        if token.isdigit():
            value = int(token)
            if 1 <= value <= 31:
                day_candidates.append(value)
        else:
            value = _words_to_number(token)
            if value is not None and 1 <= value <= 31:
                day_candidates.append(value)
            else:
                value = _words_to_number(token.replace("-", " "))
                if value is not None and 1 <= value <= 31:
                    day_candidates.append(value)

    if not day_candidates:
        return None

    try:
        return date_type(year, month, day_candidates[0]).isoformat()
    except ValueError:
        return None


def _spoken_number_to_int(text: str) -> Optional[int]:
    words = re.sub(r"[-,]", " ", text.lower()).split()
    units = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19}
    tens = {"twenty":20,"thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,"eighty":80,"ninety":90}
    total=current=0
    for w in words:
        if w in units: current += units[w]
        elif w in tens: current += tens[w]
        elif w == "hundred": current=max(current,1)*100
        elif w == "thousand": total += max(current,1)*1000; current=0
        else: return None
    return total+current

def _spoken_dob(value: str) -> Optional[str]:
    raw=re.sub(r"[,.]", " ", str(value or "").strip().lower())
    raw=re.sub(r"\s+", " ", raw)
    months={"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
    parts=raw.split()
    if len(parts)<3 or parts[0] not in months: return None
    ordinals={"first":1,"second":2,"third":3,"fourth":4,"fifth":5,"sixth":6,"seventh":7,"eighth":8,"ninth":9,"tenth":10,"eleventh":11,"twelfth":12,"thirteenth":13,"fourteenth":14,"fifteenth":15,"sixteenth":16,"seventeenth":17,"eighteenth":18,"nineteenth":19,"twentieth":20,"thirtieth":30,"thirty-first":31}
    day=ordinals.get(parts[1]) or _spoken_number_to_int(parts[1])
    year=_spoken_number_to_int(" ".join(parts[2:]))
    if day is None or year is None or not 1<=day<=31 or not 1900<=year<=2100: return None
    try: return date_type(year, months[parts[0]], day).isoformat()
    except ValueError: return None

def normalize_dob(value: str) -> Optional[str]:
    """
    Normalize DOB to YYYY-MM-DD.

    Accepted formats:
        YYYY-MM-DD
        YYYY/MM/DD
        MM/DD/YYYY
        MM-DD-YYYY
        Month DD, YYYY
        Month D, YYYY
        DD Month YYYY
    """

    if not value:
        return None

    raw = str(value).strip()

    # Already ISO-like
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass

    # MM/DD/YYYY
    # IMPORTANT:
    # 05/10/1998 means May 10, 1998.
    for fmt in (
        "%m/%d/%Y",
        "%m-%d-%Y",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass

    # Natural language dates
    for fmt in (
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass

    # Remove ordinal suffixes:
    # 10th May 1998
    # May 10th 1998
    cleaned = re.sub(
        r"(\d{1,2})(st|nd|rd|th)",
        r"\1",
        raw,
        flags=re.IGNORECASE,
    )

    for fmt in (
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            pass

    spoken = _normalize_spoken_dob(raw)
    if spoken is not None:
        return spoken

    spoken = _spoken_dob(raw)
    if spoken is not None:
        return spoken

    return None


def normalize_requested_date(value: str) -> Optional[str]:
    """
    Normalize appointment dates.

    Supports:
        YYYY-MM-DD
        MM/DD/YYYY
        MM-DD-YYYY
        today
        tomorrow
        weekday names
        next <weekday>
    """

    if not value:
        return None

    raw = str(value).strip().lower()

    # Remove conversational words.
    raw = re.sub(
        r"\b(instead|please|for me|then|actually)\b",
        "",
        raw,
    ).strip()

    today = date_type.today()

    # Relative dates
    if raw in {"today", "this day"}:
        return today.isoformat()

    if raw in {"tomorrow", "the next day"}:
        return (today + timedelta(days=1)).isoformat()

    # ISO
    try:
        return datetime.strptime(
            raw,
            "%Y-%m-%d",
        ).date().isoformat()
    except ValueError:
        pass

    # MM/DD/YYYY
    for fmt in (
        "%m/%d/%Y",
        "%m-%d-%Y",
    ):
        try:
            return datetime.strptime(
                raw,
                fmt,
            ).date().isoformat()
        except ValueError:
            pass

    # Natural-language dates such as "October 10, 2026".
    cleaned = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", raw, flags=re.IGNORECASE)
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            pass

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    # Plain weekday.
    if raw in weekdays:
        target = weekdays[raw]
        days_ahead = (target - today.weekday()) % 7

        # If today is the requested weekday,
        # interpret it as the next occurrence.
        if days_ahead == 0:
            days_ahead = 7

        return (today + timedelta(days=days_ahead)).isoformat()

    # "next friday"
    if raw.startswith("next "):
        weekday = raw.replace("next ", "", 1).strip()

        if weekday in weekdays:
            target = weekdays[weekday]
            days_ahead = (target - today.weekday()) % 7

            if days_ahead == 0:
                days_ahead = 7

            return (today + timedelta(days=days_ahead)).isoformat()

    return None


# ============================================================
# END CALL TOOL
# ============================================================

def end_call_tools():
    """
    Configure the EndCallTool.

    The agent must not end the call prematurely.
    """

    tool = EndCallTool(
        extra_description=(
            "Only end the call when the caller explicitly wants to end, "
            "or when the workflow has reached a genuine terminal state. "
            "NEVER call end_call merely because the caller corrected an "
            "appointment date, changed their mind, is missing information, "
            "or needs to continue identity verification. "
            "If verification has permanently failed, first provide a clear "
            "spoken explanation that the caller could not be verified and "
            "that no protected appointment or billing action was completed."
        ),
        delete_room=True,
        end_instructions=(
            "Give a short, clear final spoken response before disconnecting. "
            "If identity verification failed, explicitly say that verification "
            "could not be completed and that no booking, cancellation, or "
            "appointment change was made. Then say goodbye."
        ),
        ignore_on_enter=True,
    )

    return tool.tools


# ============================================================
# RECEPTION AGENT
# ============================================================

class ReceptionAgent(Agent):

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
You are the Reception Agent for CityCare Clinic.

============================================================
GREETING
============================================================

Greet the caller warmly.

Example:
"Hello, thank you for calling CityCare Clinic. How can I help you today?"

============================================================
CLINIC INFORMATION
============================================================

CityCare Clinic information:

Hours:
- Monday-Friday: 8:00 AM to 6:00 PM
- Saturday: 9:00 AM to 1:00 PM
- Sunday: Closed

Address:
12 Park Road

Services:
- General check-ups
- Blood tests
- Vaccinations
- Children's doctor

Parking:
Free parking is available behind the building.

Insurance:
Major insurance plans are accepted.

============================================================
MEDICAL ADVICE
============================================================

You are NOT a medical professional.

Do not:
- diagnose conditions
- recommend medications
- recommend dosages
- interpret symptoms medically
- provide treatment instructions

If the caller asks for medical advice, politely say that you cannot
provide medical advice and recommend speaking with a qualified
healthcare professional or booking an appointment.

============================================================
IDENTITY VERIFICATION
============================================================

Protected actions require verification.

Protected actions include:
- viewing appointment information
- changing an appointment
- cancelling an appointment
- booking an appointment
- accessing billing information

Verification order MUST be:

1. Full name
2. Phone number
3. Date of birth
4. Verify all three

Never skip a step.

Never claim that a caller is verified unless verify_caller
returns successful verification.

============================================================
NAME COLLECTION
============================================================

Ask for the caller's full name.

If the caller refuses to provide a name:
- explain that identity verification is required for protected actions
- do not invent a name
- do not continue protected actions
- do not immediately end the call unless the caller explicitly wants to leave

============================================================
PHONE COLLECTION
============================================================

Ask for the caller's phone number.

Store digits only.

Do not invent phone numbers.

============================================================
DOB COLLECTION
============================================================

Ask for the caller's date of birth only AFTER collect_name and collect_phone have both succeeded. Accept unambiguous spoken dates such as "January 1 2000" or "January first two thousand". Do not force numeric reformatting.

Example:
05/10/1998 means May 10, 1998.

Do NOT reinterpret 05/10/1998 as October 5.

Internally normalize the DOB to YYYY-MM-DD.

============================================================
VERIFICATION
============================================================

Verification is strictly gated. The ONLY valid order is:
1. collect_name succeeds.
2. collect_phone succeeds.
3. collect_dob succeeds.
4. verify_caller is called.
NEVER call verify_caller at greeting, before collect_name, after only the name, or after only the phone. Details merely spoken by the caller do not count as recorded state until the matching collection tool succeeds. If collect_dob accepts a spoken DOB, continue to verify_caller immediately.

If verification succeeds:
- clearly tell the caller they are verified
- continue with the requested protected action

If verification fails:
- tell the caller immediately that verification failed
- tell them the protected action was NOT completed
- do not expose private information
- do not claim success

============================================================
APPOINTMENT DATE CORRECTIONS
============================================================

If the caller changes an appointment date:

Example:
"I want tomorrow."
Then:
"Actually, Friday instead."

The latest date ALWAYS replaces the earlier date.

Do NOT call end_call.

Do NOT restart the entire conversation.

Acknowledge the correction and continue.

============================================================
BOOKING
============================================================

A booking requires:

1. Successful identity verification.
2. Requested date/time/service.
3. Free slot lookup when necessary.
4. Explicit caller confirmation.
5. Only then call book_appointment.

Never book without explicit confirmation.

For a normal check-up request, treat "check-up", "check up", "checkup",
and "general check-up" as the General check-up service.

============================================================
CANCELLATION / CHANGE
============================================================

A cancellation or appointment change requires successful identity
verification.

Never perform these actions based only on a caller's claim.

============================================================
ENDING CALLS
============================================================

Do not end a call prematurely.

Use end_call only when:
- caller explicitly wants to end
- workflow has genuinely reached a terminal state
- terminal verification failure has been clearly explained

============================================================
STYLE
============================================================

Be concise and friendly.

Use 1-3 short sentences at a time.

Do not expose internal tool names or internal reasoning.
""",
            tools=end_call_tools(),
            chat_ctx=chat_ctx,
        )

    # ========================================================
    # COLLECT NAME
    # ========================================================

    @function_tool()
    async def collect_name(
        self,
        name: str,
        context: RunContext = None,
    ) -> str:
        """Collect and store the caller's full name."""

        value = normalize_name(name)

        if not value:
            return (
                "No name was provided. Ask the caller for their full name. "
                "Do not invent a name and do not end the call."
            )

        refusal_phrases = {
            "no",
            "no name",
            "i don't want to say",
            "i do not want to say",
            "rather not",
            "prefer not",
            "i won't say",
            "not telling",
            "skip",
        }

        placeholder_names = {
            "user", "caller", "patient", "customer", "unknown",
            "someone", "somebody", "person", "guest", "test",
            "name", "the user", "the caller", "the patient",
        }

        if value.lower() in refusal_phrases or value.lower() in placeholder_names:
            return (
                "A valid caller-provided full name was not provided. "
                "Ask the caller for their actual full name. Do not invent or "
                "accept placeholders such as User, Caller, or Patient."
            )

        if context is not None:
            context.userdata.name = value
            context.userdata.verified = False

        return (
            f"Caller name recorded as {value}. "
            "Ask for the phone number next."
        )

    # ========================================================
    # COLLECT PHONE
    # ========================================================

    @function_tool()
    async def collect_phone(
        self,
        phone: str,
        context: RunContext = None,
    ) -> str:
        """Collect and store the caller's phone number."""

        normalized = normalize_phone(phone)

        if context is not None and not normalize_name(getattr(context.userdata, "name", "")):
            return (
                "The caller's full name has not been recorded yet. "
                "Ask for and record the actual full name before collecting the phone number."
            )

        if len(normalized) < 7:
            return (
                "The phone number is incomplete. "
                "Ask the caller to provide the full phone number."
            )

        if context is not None:
            context.userdata.phone = normalized
            context.userdata.verified = False

        return (
            "Phone number recorded. "
            "Ask for the caller's date of birth in MM/DD/YYYY format."
        )

    # ========================================================
    # COLLECT DOB
    # ========================================================

    @function_tool()
    async def collect_dob(
        self,
        date_of_birth: str,
        context: RunContext = None,
    ) -> str:
        """Collect and normalize the caller's date of birth."""

        normalized = normalize_dob(date_of_birth)

        if context is not None:
            name = normalize_name(getattr(context.userdata, "name", ""))
            phone = normalize_phone(getattr(context.userdata, "phone", ""))
            if not name or not phone:
                return (
                    "Identity information is incomplete. Collect and record the "
                    "full name and phone number before collecting the date of birth."
                )

        if normalized is None:
            return (
                "The date of birth could not be understood. "
                "Ask the caller to provide it in MM/DD/YYYY format, "
                "for example 05/10/1998."
            )

        if context is not None:
            context.userdata.date_of_birth = normalized
            context.userdata.verified = False

            # Verify immediately once all identity fields are available.
            # This makes DOB verification deterministic in text and audio runs.
            name = normalize_name(getattr(context.userdata, "name", ""))
            phone = normalize_phone(getattr(context.userdata, "phone", ""))
            if name and phone:
                return await self.verify_caller(context)

        return (
            f"Date of birth recorded as {normalized}. "
            "The date was understood successfully. Continue identity verification with the collected name, phone, and DOB."
        )

    # ========================================================
    # VERIFY CALLER
    # ========================================================

    @function_tool()
    async def verify_caller(
        self,
        context: RunContext = None,
    ) -> str:
        """Verify the caller against demo patient records.

IMPORTANT: Do not call this tool until collect_name, collect_phone, and
collect_dob have each succeeded in that exact order. Mentioned details alone
do not count as recorded fields.
"""

        if context is None:
            return (
                "The caller could not be verified because verification "
                "context is unavailable."
            )

        userdata = context.userdata

        # Always reset before a new verification attempt.
        userdata.verified = False

        name = normalize_name(
            getattr(userdata, "name", "")
        )
        phone = normalize_phone(
            getattr(userdata, "phone", "")
        )
        dob = normalize_dob(
            getattr(userdata, "date_of_birth", "")
        )

        if not name or name.lower() in {
            "user", "caller", "patient", "customer", "unknown", "someone",
            "somebody", "person", "guest", "test", "name",
        }:
            return (
                "The caller could not be verified because a valid caller-provided "
                "full name has not been collected. No protected action was completed."
            )

        if not phone:
            return (
                "The caller could not be verified because the phone number "
                "has not been collected. No protected action was completed."
            )

        if not dob:
            return (
                "The caller could not be verified because the date of birth "
                "has not been collected correctly. No protected action was completed."
            )

        expected_dob = PATIENT_DOBS.get(phone)

        if expected_dob is None:
            return (
                "The caller could not be verified because the phone number "
                "does not match a patient record. No protected action was completed."
            )

        expected_normalized = normalize_dob(expected_dob)

        if dob != expected_normalized:
            return (
                "The caller could not be verified because the date of birth "
                "does not match the patient record. No protected action was completed."
            )

        userdata.verified = True

        return (
            "The caller has been successfully verified. "
            "Protected actions may now continue."
        )

    # ========================================================
    # GO TO BOOKING
    # ========================================================

    @function_tool()
    async def go_to_booking(
        self,
        context: RunContext = None,
    ):
        """Transfer to booking only after successful verification."""

        if context is None or not context.userdata.verified:
            return (
                "Booking cannot start because the caller has not been verified. "
                "Collect name, phone number, and date of birth, then verify first."
            )

        return (
            BookingAgent(chat_ctx=self.chat_ctx),
            "Transferring you to the booking assistant. I will first check the requested date for available slots.",
        )

    # ========================================================
    # GO TO BILLING
    # ========================================================

    @function_tool()
    async def go_to_billing(
        self,
        context: RunContext = None,
    ):
        """Transfer to billing only after successful verification."""

        if context is None or not context.userdata.verified:
            return (
                "Billing information cannot be accessed because the caller "
                "has not been verified."
            )

        return (
            BillingAgent(chat_ctx=self.chat_ctx),
            "Transferring you to the billing assistant.",
        )


# ============================================================
# BOOKING AGENT
# ============================================================

class BookingAgent(Agent):

    def __init__(self, chat_ctx=None):
        # Runtime-only booking state. This is intentionally not part of the
        # tool schema, so it does not affect pytest/mock signatures.
        self._last_lookup_date = None
        self._last_lookup_slots = []
        self._confirmation_needed = False

        super().__init__(
            instructions="""
You are the Booking Agent for CityCare Clinic.

============================================================
SECURITY
============================================================

The caller MUST already be verified before protected booking actions.

Never bypass verification.

Before booking, follow this exact order: 1. Verify caller. 2. Call list_free_slots. 3. Wait for its result. 4. Tell the caller the exact returned service/date/time. 5. Ask for confirmation AFTER the lookup. 6. STOP and wait for the caller's NEXT turn. 7. Only after that new affirmative response call book_appointment with confirmed=true. A yes before lookup is NOT confirmation. Never call book_appointment in the same turn as list_free_slots. Never claim a booking until book_appointment returns success.

============================================================
DATE CORRECTIONS
============================================================

The caller may change their requested date during the conversation.

Example:

Caller:
"I want an appointment tomorrow."

Later:

"Actually, Friday instead."

Treat Friday as the NEW requested date.

Do NOT:
- end the call
- restart the conversation
- keep using the old date
- claim the appointment was booked

Instead acknowledge the correction and check the new date.

============================================================
BOOKING CONFIRMATION
============================================================

NEVER call book_appointment until the caller explicitly confirms.

Valid confirmation examples:
- "Yes"
- "Yes, book it"
- "That's fine"
- "Please book it"
- "Confirm"

After list_free_slots returns, tell the caller the service, requested date, and an actual returned time. Ask for explicit confirmation and wait for the caller's next affirmative response. Only then call book_appointment.

============================================================
GENERAL
============================================================

Be concise.

Never invent availability.

Clinic hours are Monday-Friday 8:00 AM-6:00 PM, Saturday 9:00 AM-1:00 PM, Sunday closed.
Never infer a weekday from memory. The calendar date returned by list_free_slots is authoritative.
Never offer a time until list_free_slots has returned it.

If the backend is unavailable, say that appointment availability
is temporarily unavailable.

If no slots are returned, say that no slots are currently available.

Do not invent a time.
""",
            tools=end_call_tools(),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        """Start every booking handoff with an availability-first workflow."""
        await self.session.generate_reply(
            instructions=(
                "Continue the booking request from the conversation history. "
                "Do not invent a weekday, date, or time. Identify the latest "
                "requested appointment date and service. BEFORE offering any "
                "appointment time, call list_free_slots for that date. Only "
                "offer a time returned by that tool. If the caller has not yet "
                "provided a date, ask for the date first. If the caller changes "
                "the date, discard the old date and check the new date."
            )
        )

    # ========================================================
    # LIST FREE SLOTS
    # ========================================================

    @function_tool()
    async def list_free_slots(
        self,
        date: str,
        context: RunContext = None,
    ) -> str:
        """Get available appointment slots for a requested date."""

        normalized_date = normalize_requested_date(date)

        if normalized_date is None:
            return (
                "I couldn't determine that appointment date. "
                "Please provide the date in YYYY-MM-DD or MM/DD/YYYY format."
            )

        requested_day = datetime.strptime(normalized_date, "%Y-%m-%d").date()
        weekday_name = requested_day.strftime("%A")

        # Sunday is closed according to clinic policy. Do not invent slots.
        if weekday_name == "Sunday":
            return (
                f"CityCare Clinic is closed on Sunday, {normalized_date}. "
                "No appointment slots are available for that date."
            )

        url = "http://127.0.0.1:8000/slots"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    url,
                    params={"date": normalized_date},
                )

            if response.status_code != 200:
                return (
                    "Appointment availability is temporarily unavailable. "
                    "Please try again later."
                )

            data = response.json()

            # Backend/test can return:
            # ["09:00", "10:00"]
            #
            # or:
            # {"slots": ["09:00", "10:00"]}
            if isinstance(data, list):
                slots = data

            elif isinstance(data, dict):
                slots = data.get("slots", [])

            else:
                slots = []

            # Record the exact backend result. Booking is only allowed to use
            # a slot returned by this lookup.
            self._last_lookup_date = normalized_date
            self._last_lookup_slots = [str(slot).strip() for slot in slots]
            self._confirmation_needed = True

            if not slots:
                return (
                    f"No free appointment slots are available for "
                    f"{normalized_date}."
                )

            slot_text = ", ".join(
                str(slot)
                for slot in slots
            )

            return (
                f"Free appointment slots for {weekday_name}, {normalized_date}: "
                f"{slot_text}. Use only one of these returned times; do not invent availability."
            )

        except httpx.RequestError:
            return (
                "Appointment availability is temporarily unavailable. "
                "Please try again later."
            )

        except Exception:
            return (
                "Appointment availability is temporarily unavailable. "
                "Please try again later."
            )

    # ========================================================
    # BOOK APPOINTMENT
    # ========================================================

    @function_tool()
    async def book_appointment(
        self,
        date: str,
        time: str,
        service: str,
        confirmed: bool = False,
        context: RunContext = None,
    ) -> str:
        """Book an appointment after verification and confirmation."""

        if context is None or not context.userdata.verified:
            return (
                "The caller has not been verified. "
                "The appointment has not been booked."
            )

        if not context.userdata.name or not context.userdata.phone:
            return (
                "Required caller information is missing. "
                "The appointment has not been booked."
            )

        confirmed_value = confirmed
        if isinstance(confirmed, str):
            confirmed_value = confirmed.strip().lower() in {
                "true", "yes", "y", "confirm", "confirmed", "book", "book it"
            }

        if not confirmed_value:
            return (
                "The appointment has not been booked. "
                "Explicit caller confirmation is required first."
            )

        normalized_date = normalize_requested_date(date)

        if normalized_date is None:
            return (
                "The appointment date could not be understood. "
                "The appointment has not been booked."
            )

        service_normalized = re.sub(r"\s+", " ", (service or "").strip().lower())
        service_normalized = service_normalized.replace("–", "-").replace("—", "-")

        # Accept common spoken variants of the clinic's supported services.
        service_aliases = {
            "check-up": "General check-up",
            "check up": "General check-up",
            "checkup": "General check-up",
            "general check-up": "General check-up",
            "general check up": "General check-up",
            "general checkup": "General check-up",
            "general check-up appointment": "General check-up",
            "general check up appointment": "General check-up",
            "blood test": "Blood tests",
            "blood tests": "Blood tests",
            "vaccination": "Vaccinations",
            "vaccinations": "Vaccinations",
            "vaccine": "Vaccinations",
            "vaccines": "Vaccinations",
            "children's doctor": "Children's doctor",
            "childrens doctor": "Children's doctor",
            "children doctor": "Children's doctor",
            "child doctor": "Children's doctor",
        }

        canonical_service = service_aliases.get(service_normalized)

        if canonical_service is None:
            return (
                "That service is not available in the clinic's supported "
                "booking services. The appointment has not been booked."
            )

        # If availability was just checked, enforce that the booking uses the
        # exact date/time returned by the backend. The first booking attempt
        # after a lookup is intentionally rejected so that a pre-lookup "yes"
        # cannot be treated as confirmation for the actual returned slot.
        if self._last_lookup_date is not None:
            if self._last_lookup_date != normalized_date:
                return (
                    "The requested date is different from the date whose "
                    "availability was checked. Please check the new date first. "
                    "The appointment has not been booked."
                )

            requested_time = str(time).strip()
            available_times = {str(slot).strip() for slot in self._last_lookup_slots}

            if requested_time not in available_times:
                return (
                    f"The requested time {requested_time} was not returned as "
                    "available by the latest slot lookup. The appointment has "
                    "not been booked."
                )

            if self._confirmation_needed:
                self._confirmation_needed = False
                return (
                    f"The slot {normalized_date} at {requested_time} is available. "
                    "Tell the caller the exact service, date, and time, ask for a "
                    "new explicit confirmation, and wait for the caller's next "
                    "turn before calling book_appointment again. The appointment "
                    "has not been booked."
                )

        payload = {
            "name": context.userdata.name,
            "phone": context.userdata.phone,
            "date": normalized_date,
            "time": time,
            "service": canonical_service,
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/appointments",
                    json=payload,
                )

            if response.status_code == 409:
                return (
                    "That appointment slot is no longer available. "
                    "The appointment has not been booked."
                )

            if response.status_code not in (200, 201):
                return (
                    "The appointment system is temporarily unavailable. "
                    "The appointment has not been booked. The caller can be handed "
                    "off to clinic staff with the requested service, date, and time."
                )

            data = response.json()

            # A successful booking consumes the lookup/confirmation state.
            self._confirmation_needed = False
            self._last_lookup_date = None
            self._last_lookup_slots = []

            appointment_id = None

            if isinstance(data, dict):
                appointment_id = data.get("id")

                if appointment_id is None:
                    appointment = data.get("appointment")

                    if isinstance(appointment, dict):
                        appointment_id = appointment.get("id")

                if appointment_id is None:
                    appointment_id = data.get("appointment_id")

            if appointment_id is not None:
                return (
                    f"The appointment has been booked successfully for "
                    f"{normalized_date} at {time}. "
                    f"Appointment ID: {appointment_id}."
                )

            return (
                f"The appointment has been booked successfully for "
                f"{normalized_date} at {time}."
            )

        except httpx.RequestError:
            return (
                "The appointment system is temporarily unavailable. "
                "The appointment has not been booked. The caller can be handed "
                "off to clinic staff with the requested service, date, and time."
            )

        except Exception:
            return (
                "The appointment system is temporarily unavailable. "
                "The appointment has not been booked. The caller can be handed "
                "off to clinic staff with the requested service, date, and time."
            )

    # ========================================================
    # FIND APPOINTMENTS
    # ========================================================

    @function_tool()
    async def find_my_appointments(
        self,
        context: RunContext = None,
    ) -> str:
        """Find appointments for the verified caller."""

        if context is None or not context.userdata.verified:
            return (
                "The caller has not been verified. "
                "Appointment information cannot be accessed."
            )

        phone = normalize_phone(
            context.userdata.phone
        )

        if not phone:
            return (
                "The caller's phone number is unavailable. "
                "Appointment information cannot be accessed."
            )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/appointments",
                    params={"phone": phone},
                )

            if response.status_code != 200:
                return (
                    "Appointment information is temporarily unavailable."
                )

            data = response.json()

            if not data:
                return (
                    "No appointments were found for the verified caller."
                )

            return f"Verified caller appointments: {data}"

        except httpx.RequestError:
            return (
                "Appointment information is temporarily unavailable."
            )

        except Exception:
            return (
                "Appointment information is temporarily unavailable."
            )

    # ========================================================
    # CANCEL APPOINTMENT
    # ========================================================

    @function_tool()
    async def cancel_appointment(
        self,
        appointment_id: int,
        confirmed: bool = False,
        context: RunContext = None,
    ) -> str:
        """Cancel an appointment after verification and confirmation."""

        if context is None or not context.userdata.verified:
            return (
                "The caller has not been verified. "
                "The appointment has not been cancelled."
            )

        if not confirmed:
            return (
                "The appointment has not been cancelled. "
                "Explicit caller confirmation is required first."
            )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.delete(
                    f"http://127.0.0.1:8000/appointments/{appointment_id}"
                )

            if response.status_code == 404:
                return (
                    "The appointment could not be found. "
                    "No appointment was cancelled."
                )

            if response.status_code != 200:
                return (
                    "The appointment system is temporarily unavailable. "
                    "The appointment has not been cancelled."
                )

            return (
                "The appointment has been cancelled successfully."
            )

        except httpx.RequestError:
            return (
                "The appointment system is temporarily unavailable. "
                "The appointment has not been cancelled."
            )

        except Exception:
            return (
                "The appointment system is temporarily unavailable. "
                "The appointment has not been cancelled."
            )

    # ========================================================
    # CHANGE APPOINTMENT
    # ========================================================

    @function_tool()
    async def change_appointment(
        self,
        appointment_id: int,
        date: str,
        time: str,
        confirmed: bool = False,
        context: RunContext = None,
    ) -> str:
        """Change an appointment after verification and confirmation."""

        if context is None or not context.userdata.verified:
            return (
                "The caller has not been verified. "
                "The appointment has not been changed."
            )

        if not confirmed:
            return (
                "The appointment has not been changed. "
                "Explicit caller confirmation is required first."
            )

        normalized_date = normalize_requested_date(date)

        if normalized_date is None:
            return (
                "The new appointment date could not be understood. "
                "The appointment has not been changed."
            )

        payload = {
            "date": normalized_date,
            "time": time,
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.patch(
                    f"http://127.0.0.1:8000/appointments/{appointment_id}",
                    json=payload,
                )

            if response.status_code == 404:
                return (
                    "The appointment could not be found. "
                    "The appointment has not been changed."
                )

            if response.status_code == 409:
                return (
                    "That new appointment slot is unavailable. "
                    "The appointment has not been changed."
                )

            if response.status_code != 200:
                return (
                    "The appointment system is temporarily unavailable. "
                    "The appointment has not been changed."
                )

            return (
                f"The appointment has been changed successfully to "
                f"{normalized_date} at {time}."
            )

        except httpx.RequestError:
            return (
                "The appointment system is temporarily unavailable. "
                "The appointment has not been changed."
            )

        except Exception:
            return (
                "The appointment system is temporarily unavailable. "
                "The appointment has not been changed."
            )

    # ========================================================
    # RETURN TO RECEPTION
    # ========================================================

    @function_tool()
    async def return_to_reception(
        self,
        context: RunContext = None,
    ):
        """Return the caller to reception."""

        return ReceptionAgent(
            chat_ctx=(
                context.session.chat_ctx
                if context is not None
                else None
            )
        )


# ============================================================
# BILLING AGENT
# ============================================================

class BillingAgent(Agent):

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
You are the Billing Agent for CityCare Clinic.

Only discuss billing after successful identity verification.

Never disclose billing information to an unverified caller.

If the billing backend is unavailable, clearly say:

"The billing system is unavailable right now."

Do not invent billing amounts, invoices, balances, or payment details.

Be concise and professional.
""",
            tools=end_call_tools(),
            chat_ctx=chat_ctx,
        )

    # ========================================================
    # GET BILL
    # ========================================================

    @function_tool()
    async def get_bill(
        self,
        phone_or_context=None,
        context: RunContext = None,
    ) -> str:
        """
        Retrieve billing information for the verified caller.

        Supports:
            get_bill(context)

        and:
            get_bill(phone, context)
        """

        # Unit-test compatibility:
        # get_bill(context)
        if context is None and hasattr(phone_or_context, "userdata"):
            context = phone_or_context

            phone = getattr(
                context.userdata,
                "phone",
                "",
            )
        else:
            phone = phone_or_context or ""

        # Security check
        if context is None or not context.userdata.verified:
            return (
                "The caller has not been verified. "
                "Billing information cannot be disclosed."
            )

        # Use verified phone when no phone was explicitly supplied.
        if not phone:
            phone = context.userdata.phone

        normalized_phone = normalize_phone(phone)

        verified_phone = normalize_phone(
            context.userdata.phone
        )

        if normalized_phone != verified_phone:
            return (
                "The supplied phone number does not match "
                "the verified caller."
            )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/bills",
                    params={"phone": normalized_phone},
                )

            if response.status_code != 200:
                return (
                    "The billing system is unavailable right now."
                )

            data = response.json()

            if not data:
                return (
                    "No billing information was found."
                )

            return f"Verified billing information: {data}"

        except httpx.RequestError:
            return (
                "The billing system is unavailable right now."
            )

        except Exception:
            return (
                "The billing system is unavailable right now."
            )

    # ========================================================
    # RETURN TO RECEPTION
    # ========================================================

    @function_tool()
    async def return_to_reception(
        self,
        context: RunContext = None,
    ):
        """Return the caller to reception."""

        return ReceptionAgent(
            chat_ctx=(
                context.session.chat_ctx
                if context is not None
                else None
            )
        )