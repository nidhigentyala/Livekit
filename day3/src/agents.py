# import httpx
# from livekit.agents import Agent, RunContext, function_tool
# from livekit.agents.beta.workflows import (
#     GetNameTask,
#     GetPhoneNumberTask,
#     GetDOBTask,
# )
# from userdata import CallerData


# class ReceptionAgent(Agent):

#     def __init__(self):
#         super().__init__(
#             instructions="""
# You are the Reception Agent for CityCare Clinic.

# Your responsibilities:
# 1. Greet the caller.
# 2. Find out why they are calling.
# 3. Collect the caller's name.
# 4. Collect the caller's phone number.
# 5. Collect the caller's date of birth.
# 6. Verify the caller before allowing access to Booking or Billing.
# 7. If the caller wants an appointment, transfer to BookingAgent.
# 8. If the caller wants billing information, transfer to BillingAgent.

# Be concise and natural.

# Never send an unverified caller to BookingAgent or BillingAgent.
# Do not ask BookingAgent or BillingAgent questions that have already
# been answered and stored in userdata.
# """
#         )

#     async def on_enter(self):
#         await self.session.generate_reply(
#             instructions=(
#                 "Greet the caller warmly and ask how you can help today."
#             )
#         )
#         @function_tool()
#         async def go_to_booking(
#             self,
#             context: RunContext[CallerData]
#         ):
#             """Transfer the caller to Booking."""

#             if not context.userdata.verified:
#                 return "The caller is not verified yet."

#             return (
#                 BookingAgent(
#                     chat_ctx=self.chat_ctx.copy(
#                         exclude_instructions=True
#                     )
#                 ),
#                 "Sure, I'll connect you with appointment booking."
#             )
#         @function_tool()
#         async def go_to_billing(
#             self,
#             context: RunContext[CallerData]
#         ):
#             """Transfer the caller to Billing."""

#             if not context.userdata.verified:
#                 return "The caller is not verified yet."

#             return (
#                 BillingAgent(
#                     chat_ctx=self.chat_ctx.copy(
#                         exclude_instructions=True
#                 )
#             ),
#                 "Sure, I'll connect you with billing."
#             )

#         @function_tool()
#         async def collect_name(
#             self,
#             context: RunContext[CallerData]
#         ):
#             """Collect and store the caller's name."""

#             result = await GetNameTask(
#                 chat_ctx=context.session.chat_ctx,
#                 require_confirmation=True,
#             )

#             first = result.first_name or ""
#             middle = result.middle_name or ""
#             last = result.last_name or ""

#             full_name = " ".join(
#                 part for part in [first, middle, last] if part
#             )

#             context.userdata.name = full_name

#             return f"Caller name recorded as {full_name}."

#         @function_tool()
#         async def collect_phone(
#             self,
#             context: RunContext[CallerData]
#         ):
#             """Collect and store the caller's phone number."""

#             result = await GetPhoneNumberTask(
#                 chat_ctx=context.session.chat_ctx,
#                 require_confirmation=True,
#             )

#             context.userdata.phone = result.phone_number

#             return f"Phone number recorded as {result.phone_number}."

#         @function_tool()
#         async def collect_dob(
#             self,
#             context: RunContext[CallerData]
#         ):
#             """Collect and store the caller's date of birth."""

#             result = await GetDOBTask(
#                 chat_ctx=context.session.chat_ctx,
#                 require_confirmation=True,
#             )

#             context.userdata.date_of_birth = (
#                 result.date_of_birth.isoformat()
#             )

#             return (
#                 f"Date of birth recorded as "
#                 f"{context.userdata.date_of_birth}."
#             )
            
#         @function_tool()
#         async def verify_caller(
#             self,
#             context: RunContext[CallerData]
#         ):
#             """
#             Verify the caller after name, phone and DOB
#             have been collected.
#             """

#             caller = context.userdata

#             if not caller.name:
#                 return "The caller's name is missing."

#             if not caller.phone:
#                 return "The caller's phone number is missing."

#             if not caller.date_of_birth:
#                 return "The caller's date of birth is missing."

#             caller.verified = True

#             return "Caller identity verified successfully."
        

# class BookingAgent(Agent):

#     def __init__(self, chat_ctx=None):
#         super().__init__(
#             instructions="""
# You are the Booking Agent for CityCare Clinic.

# You handle:
# - New appointments
# - Changing appointments
# - Cancelling appointments

# The caller has already been identified by Reception.

# Use the shared userdata:
# - name
# - phone
# - date_of_birth
# - verified

# Do NOT ask the caller for these details again.

# Help the caller with the appointment request.
# When the booking-related request is finished, ask whether they
# need anything else and return control to Reception.
# """
#             ,
#             chat_ctx=chat_ctx,
#         )

#     async def on_enter(self):
#         caller = self.session.userdata

#         await self.session.generate_reply(
#             instructions=(
#                 f"The caller is already verified. "
#                 f"Their name is {caller.name}. "
#                 f"Continue helping with their appointment request."
#             )
#         )

#         @function_tool()
#         async def return_to_reception(
#             self,
#             context: RunContext[CallerData]
#         ):
#             """
#             Return control to Reception when the appointment request
#             has been completed and the caller may need something else.
#             """

#             return (
#                 ReceptionAgent(
#                     chat_ctx=self.chat_ctx.copy(
#                         exclude_instructions=True
#                     )
#                 ),
#                 "I'll return you to reception for anything else you need."
#             )

# # class BillingAgent(Agent):

# #     def __init__(self, chat_ctx=None):
# #         super().__init__(
# #             instructions="""
# # You are the Billing Agent for CityCare Clinic.

# # You handle patient billing questions.

# # The caller has already been identified by Reception.

# # Use the shared userdata:
# # - name
# # - phone
# # - date_of_birth
# # - verified

# # Do NOT ask for the name, phone number, or date of birth again.

# # Use the billing tool to retrieve the caller's bill.

# # When finished, ask whether they need anything else and return
# # control to Reception.
# # """
# #             ,
# #             chat_ctx=chat_ctx,
# #         )

# #     async def on_enter(self):
# #         caller = self.session.userdata

# #         await self.session.generate_reply(
# #             instructions=(
# #                 f"The caller is already verified. "
# #                 f"The caller's name is {caller.name}. "
# #                 f"Help with their billing question."
# #             )
# #         )

# #         @function_tool()
# #         async def return_to_reception(
# #             self,
# #             context: RunContext[CallerData]
# #         ):
# #             """
# #             Return control to Reception after billing assistance.
# #             """

# #             return (
# #                 ReceptionAgent(
# #                     chat_ctx=self.chat_ctx.copy(
# #                         exclude_instructions=True
# #                     )
# #                 ),
# #                 "I'll return you to reception in case you need anything else."
# #             )


# class BillingAgent(Agent):

#     def __init__(self, chat_ctx=None):

#         super().__init__(
#             instructions="""
# You are the Billing Agent for CityCare Clinic.

# You handle patient billing questions.

# The caller has already been identified by Reception.

# Use the shared userdata:

# - name
# - phone
# - date_of_birth
# - verified

# Do NOT ask for the name, phone number, or date of birth again.

# Use the billing tool to retrieve the caller's bill.

# When finished, ask whether they need anything else and return
# control to Reception.
# """,
#             chat_ctx=chat_ctx,
#         )

#     async def on_enter(self):

#         caller = self.session.userdata

#         await self.session.generate_reply(
#             instructions=(
#                 f"The caller is already verified. "
#                 f"The caller's name is {caller.name}. "
#                 f"Help with their billing question."
#             )
#         )

#     @function_tool()
#     async def get_bill(
#         self,
#         context: RunContext[CallerData]
#     ):
#         """Retrieve the caller's current bill."""

#         caller = context.userdata

#         # Safety check: caller must be verified
#         if not caller.verified:
#             return "The caller must be verified before checking the bill."

#         # Make sure we have a phone number
#         if not caller.phone:
#             return "No phone number is available."

#         url = "http://127.0.0.1:8000/bills"

#         async with httpx.AsyncClient() as client:
#             response = await client.get(
#                 url,
#                 params={"phone": caller.phone},
#                 timeout=5.0,
#             )

#         response.raise_for_status()

#         data = response.json()

#         return (
#             f"Your current bill is "
#             f"{data['bill_amount']:.2f} "
#             f"and the due date is {data['due_date']}."
#         )

#     @function_tool()
#     async def return_to_reception(
#         self,
#         context: RunContext[CallerData]
#     ):
#         """
#         Return control to Reception after billing assistance.
#         """

#         return (
#             ReceptionAgent(
#                 chat_ctx=self.chat_ctx.copy(
#                     exclude_instructions=True
#                 )
#             ),
#             "I'll return you to reception in case you need anything else."
#         )



import httpx

from livekit.agents import Agent, RunContext, function_tool
from livekit.agents.beta.tools import EndCallTool
from livekit.agents.beta.workflows import (
    GetNameTask,
    GetPhoneNumberTask,
    GetDOBTask,
)

from src.userdata import CallerData


class ReceptionAgent(Agent):
    def __init__(self, chat_ctx=None):
        end_call_tool = EndCallTool(
            end_instructions=(
                "Thank the caller for contacting CityCare Clinic "
                "and wish them a good day."
            )
        )

        super().__init__(
            instructions="""
You are the Reception Agent for CityCare Clinic.

Your responsibilities:
1. Greet the caller.
2. Find out why they are calling.
3. Collect the caller's name.
4. Collect the caller's phone number.
5. Collect the caller's date of birth.
6. Verify the caller before allowing access to Booking or Billing.
7. If the caller wants an appointment, transfer to BookingAgent.
8. If the caller wants billing information, transfer to BillingAgent.

Be concise and natural.

Never send an unverified caller to BookingAgent or BillingAgent.

Do not ask BookingAgent or BillingAgent questions that have already
been answered and stored in userdata.

When the caller says they have no more questions,
say goodbye politely and use the end_call tool.
""",
            chat_ctx=chat_ctx,
            tools=end_call_tool.tools,
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="Greet the caller warmly and ask how you can help today."
        )

    @function_tool()
    async def go_to_booking(self, context: RunContext[CallerData]):
        if not context.userdata.verified:
            return "The caller is not verified yet."

        return (
            BookingAgent(
                chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
            ),
            "Sure, I'll connect you with appointment booking.",
        )

    @function_tool()
    async def go_to_billing(self, context: RunContext[CallerData]):
        if not context.userdata.verified:
            return "The caller is not verified yet."

        return (
            BillingAgent(
                chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
            ),
            "Sure, I'll connect you with billing.",
        )

    @function_tool()
    async def collect_name(self, context: RunContext[CallerData]):
        result = await GetNameTask(
            chat_ctx=context.session.chat_ctx,
            require_confirmation=True,
        )

        first = result.first_name or ""
        middle = result.middle_name or ""
        last = result.last_name or ""

        full_name = " ".join(
            part for part in [first, middle, last] if part
        )

        context.userdata.name = full_name

        return f"Caller name recorded as {full_name}."

    @function_tool()
    async def collect_phone(self, context: RunContext[CallerData]):
        result = await GetPhoneNumberTask(
            chat_ctx=context.session.chat_ctx,
            require_confirmation=True,
        )

        context.userdata.phone = result.phone_number

        return f"Phone number recorded as {result.phone_number}."

    @function_tool()
    async def collect_dob(self, context: RunContext[CallerData]):
        result = await GetDOBTask(
            chat_ctx=context.session.chat_ctx,
            require_confirmation=True,
        )

        context.userdata.date_of_birth = result.date_of_birth.isoformat()

        return (
            f"Date of birth recorded as "
            f"{context.userdata.date_of_birth}."
        )

    @function_tool()
    async def verify_caller(self, context: RunContext[CallerData]):
        caller = context.userdata

        if not caller.name:
            return "The caller's name is missing."

        if not caller.phone:
            return "The caller's phone number is missing."

        if not caller.date_of_birth:
            return "The caller's date of birth is missing."

        caller.verified = True

        return "Caller identity verified successfully."


class BookingAgent(Agent):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
You are the Booking Agent for CityCare Clinic.

The caller has already been identified and verified by the
Reception Agent.

Use the caller information already stored in userdata.

Do not ask the caller for their name, phone number, or date of birth
again unless absolutely necessary.

Handle:
- New appointment booking
- Changing an appointment
- Cancelling an appointment

When the booking task is complete, ask the caller if they need
anything else.

If the caller has another request, return control to the
Reception Agent.
""",
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        caller = self.session.userdata

        await self.session.generate_reply(
            instructions=(
                f"The caller is already verified. "
                f"Their name is {caller.name}. "
                "Help them with their appointment request."
            )
        )

    @function_tool()
    async def return_to_reception(
        self,
        context: RunContext[CallerData],
    ):
        return (
            ReceptionAgent(
                chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
            ),
            "I'll return you to reception for further assistance.",
        )


class BillingAgent(Agent):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
You are the Billing Agent for CityCare Clinic.

The caller has already been identified and verified by the
Reception Agent.

Use the caller information already stored in userdata.

Do not ask the caller for their name, phone number, or date of birth
again.

Handle patient billing questions and provide billing information
when requested.

When the billing task is complete, ask the caller if they need
anything else.

If the caller has another request, return control to the
Reception Agent.
""",
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        caller = self.session.userdata

        await self.session.generate_reply(
            instructions=(
                f"The caller is already verified. "
                f"Their name is {caller.name}. "
                "Ask how you can help with billing."
            )
        )

    @function_tool()
    async def get_bill(
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
                    "http://127.0.0.1:8000/bills",
                    params={"phone": caller.phone},
                )

            if response.status_code != 200:
                return "I could not retrieve the billing information."

            data = response.json()

            amount = data.get("amount")
            due_date = data.get("due_date")

            if amount is None and due_date is None:
                return "No billing information was found."

            return (
                f"Your current bill amount is {amount}. "
                f"The due date is {due_date}."
            )

        except httpx.RequestError:
            return "The billing service is currently unavailable."

    @function_tool()
    async def return_to_reception(
        self,
        context: RunContext[CallerData],
    ):
        return (
            ReceptionAgent(
                chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
            ),
            "I'll return you to reception for further assistance.",
        )