from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    STTContextOptions,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)

from livekit.plugins import ai_coustics

# import langchain
# from langgraph_agent.graph import graph
from livekit.plugins import langchain
from langgraph_agent.graph import graph

from src.userdata import CallerData
from src.agents import ReceptionAgent


# ============================================================
# Day 2 FrontDesk Agent
# ============================================================

class FrontDesk(Agent):
    def __init__(self):
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

Be concise and natural.

Do not provide medical advice.

If the caller needs medical advice, suggest booking an
appointment with the clinic.

Only answer questions related to CityCare Clinic.
"""
        )


# ============================================================
# LiveKit Agent Server
# ============================================================

server = AgentServer()


@server.rtc_session(agent_name="day3")
async def my_agent(ctx: JobContext):

    ctx.log_context_fields = {
        "room": ctx.room.name
    }

    # ========================================================
    # Agent Session
    # ========================================================

    session = AgentSession[CallerData](
        # ----------------------------------------------------
        # Shared caller data
        # ----------------------------------------------------
        userdata=CallerData(),

        # ----------------------------------------------------
        # Day 2 LangGraph + Groq LLM
        #
        # The graph is defined in:
        # langgraph_agent/graph.py
        #
        # The graph should contain your Groq LLM configuration.
        # ----------------------------------------------------
        llm=langchain.LLMAdapter(
            graph=graph
        ),

        # ----------------------------------------------------
        # Day 2 STT
        # ----------------------------------------------------
        stt=inference.STT(
            model="assemblyai/universal-3-5-pro",
            language="en",
        ),

        # ----------------------------------------------------
        # STT context options
        # ----------------------------------------------------
        stt_context_options=STTContextOptions(
            keyterms=[
                "LiveKit",
                "CityCare",
                "CityCare Clinic",
            ],
            keyterm_detection={
                "enabled": True,
            },
        ),

        # ----------------------------------------------------
        # Day 2 TTS
        # ----------------------------------------------------
        tts=inference.TTS(
            model="fishaudio/s2.1-pro",
            voice="fa4c9eb3dccc4806b382b40d61c6b10a",
        ),

        # ----------------------------------------------------
        # Day 3 Turn Handling
        # ----------------------------------------------------
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

    # ========================================================
    # Start session with Reception Agent
    # ========================================================

    await session.start(
        agent=ReceptionAgent(),
        room=ctx.room,

        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )

    # ========================================================
    # Connect to LiveKit room
    # ========================================================

    await ctx.connect()


# ============================================================
# Run the application
# ============================================================

if __name__ == "__main__":
    cli.run_app(server)