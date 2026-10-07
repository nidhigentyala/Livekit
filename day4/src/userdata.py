# # from dataclasses import dataclass


# # @dataclass
# # class CallerData:
# #     name: str | None = None
# #     phone: str | None = None
# #     date_of_birth: str | None = None
# #     verified: bool = False

# from dataclasses import dataclass


# @dataclass
# class CallerData:
#     name: str | None = None
#     phone: str | None = None
#     date_of_birth: str | None = None
#     verified: bool = False

#     # Buffers for speech that may arrive in multiple fragments
#     phone_input_buffer: str = ""
#     dob_input_buffer: str = ""

from dataclasses import dataclass


@dataclass
class CallerData:
    name: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    verified: bool = False

    # Buffers for speech that may arrive in multiple fragments
    phone_input_buffer: str = ""
    dob_input_buffer: str = ""

    # Tracks which identity step is currently required
    identity_stage: str = "name"