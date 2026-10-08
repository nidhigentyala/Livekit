from pathlib import Path
import json
import re
from datetime import datetime

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)

from livekit.plugins import ai_coustics

from .agents import ReceptionAgent
from .userdata import CallerData


# =========================================================
# REPORT DIRECTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# CITYCARE FRONT DESK
# =========================================================

class FrontDesk(Agent):

    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="""
You are the Front Desk Agent for CityCare Clinic.

CityCare Clinic information:

Opening hours:
- Monday to Friday: 8:00 AM to 6:00 PM
- Saturday: 9:00 AM to 1:00 PM
- Sunday: Closed

Address:
12 Park Road

Services:
- General check-up
- Blood tests
- Vaccinations
- Children's doctor

Parking:
Free parking is available behind the building.

Insurance:
Major insurance plans are accepted.

Do not provide medical advice.

If the caller asks what medicine they should take,
do not recommend medication.

If the caller describes symptoms and asks what they should do,
do not diagnose them or provide treatment advice.

Instead, explain that you cannot provide medical advice
and suggest booking an appointment with the clinic or
contacting an appropriate qualified healthcare professional.

Only answer questions related to CityCare Clinic.

Do not invent clinic information.

Be concise and natural.
""",
            chat_ctx=chat_ctx,
        )


# =========================================================
# SESSION REPORT
# =========================================================

async def save_session_report(ctx: JobContext) -> None:
    """
    Generate a LiveKit session report when the session ends
    and save it as a JSON file inside the reports directory.
    """

    try:
        report = ctx.make_session_report().to_dict()

        # Room names can contain characters that are inconvenient
        # in filenames, so make the name filesystem-safe.
        room_name = re.sub(
            r"[^a-zA-Z0-9_.-]",
            "_",
            ctx.room.name,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        report_file = (
            REPORTS_DIR
            / f"session_{room_name}_{timestamp}.json"
        )

        with open(
            report_file,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                report,
                f,
                indent=2,
                default=str,
            )

        print(
            f"\nSession report saved to: {report_file}\n"
        )

    except Exception as e:
        print(
            f"\nFailed to save session report: {e}\n"
        )


# =========================================================
# LIVEKIT SERVER
# =========================================================

server = AgentServer()


# =========================================================
# DAY 4 RTC SESSION
# =========================================================

@server.rtc_session(
    agent_name="day4",
    on_session_end=save_session_report,
)
async def my_agent(ctx: JobContext):

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession[CallerData](
        # Shared caller state
        userdata=CallerData(),

        # Day 4 LLM
        llm=inference.LLM(
            model="openai/gpt-oss-120b",
        ),

        # Speech-to-text
        stt=inference.STT(
            model="assemblyai/universal-3-5-pro",
            language="en",
        ),

        # Text-to-speech
        tts=inference.TTS(
            model="fishaudio/s2.1-pro",
            voice="fa4c9eb3dccc4806b382b40d61c6b10a",
        ),

        # Voice turn handling
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),

            endpointing={
                "mode": "fixed",
                "min_delay": 0.5,
                "max_delay": 3.0,
            },

            interruption={
                "mode": "adaptive",
            },

            preemptive_generation={
                "preemptive_tts": False,
            },
        ),

        expressive=True,
    )

    # =====================================================
    # START RECEPTION AGENT
    # =====================================================

    await session.start(
        agent=ReceptionAgent(),
        room=ctx.room,

        room_options=room_io.RoomOptions(
            # Text simulation / text input
            text_input=True,

            # Audio input
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
                pre_connect_audio=True,
            ),

            # Agent audio output
            audio_output=True,

            # Text/transcript output
            text_output=True,
        ),
    )

    # =====================================================
    # CONNECT TO LIVEKIT ROOM
    # =====================================================

    await ctx.connect()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    cli.run_app(server)