// // import { useState } from 'react'
// // import heroImg from './assets/hero.png'
// // import reactLogo from './assets/react.svg'
// // import viteLogo from './assets/vite.svg'
// // import './App.css'

// // function App() {
// //   const [count, setCount] = useState(0)

// //   return (
// //     <>
// //       <section id="center">
// //         <div className="hero">
// //           <img src={heroImg} className="base" width="170" height="179" alt="" />
// //           <img src={reactLogo} className="framework" alt="React logo" />
// //           <img src={viteLogo} className="vite" alt="Vite logo" />
// //         </div>
// //         <div>
// //           <h1>Get started</h1>
// //           <p>
// //             Edit <code>src/App.tsx</code> and save to test <code>HMR</code>
// //           </p>
// //         </div>
// //         <button
// //           type="button"
// //           className="counter"
// //           onClick={() => setCount((count) => count + 1)}
// //         >
// //           Count is {count}
// //         </button>
// //       </section>

// //       <div className="ticks"></div>

// //       <section id="next-steps">
// //         <div id="docs">
// //           <svg className="icon" role="presentation" aria-hidden="true">
// //             <use href="/icons.svg#documentation-icon"></use>
// //           </svg>
// //           <h2>Documentation</h2>
// //           <p>Your questions, answered</p>
// //           <ul>
// //             <li>
// //               <a href="https://vite.dev/" target="_blank">
// //                 <img className="logo" src={viteLogo} alt="" />
// //                 Explore Vite
// //               </a>
// //             </li>
// //             <li>
// //               <a href="https://react.dev/" target="_blank">
// //                 <img className="button-icon" src={reactLogo} alt="" />
// //                 Learn more
// //               </a>
// //             </li>
// //           </ul>
// //         </div>
// //         <div id="social">
// //           <svg className="icon" role="presentation" aria-hidden="true">
// //             <use href="/icons.svg#social-icon"></use>
// //           </svg>
// //           <h2>Connect with us</h2>
// //           <p>Join the Vite community</p>
// //           <ul>
// //             <li>
// //               <a href="https://github.com/vitejs/vite" target="_blank">
// //                 <svg
// //                   className="button-icon"
// //                   role="presentation"
// //                   aria-hidden="true"
// //                 >
// //                   <use href="/icons.svg#github-icon"></use>
// //                 </svg>
// //                 GitHub
// //               </a>
// //             </li>
// //             <li>
// //               <a href="https://chat.vite.dev/" target="_blank">
// //                 <svg
// //                   className="button-icon"
// //                   role="presentation"
// //                   aria-hidden="true"
// //                 >
// //                   <use href="/icons.svg#discord-icon"></use>
// //                 </svg>
// //                 Discord
// //               </a>
// //             </li>
// //             <li>
// //               <a href="https://x.com/vite_js" target="_blank">
// //                 <svg
// //                   className="button-icon"
// //                   role="presentation"
// //                   aria-hidden="true"
// //                 >
// //                   <use href="/icons.svg#x-icon"></use>
// //                 </svg>
// //                 X.com
// //               </a>
// //             </li>
// //             <li>
// //               <a href="https://bsky.app/profile/vite.dev" target="_blank">
// //                 <svg
// //                   className="button-icon"
// //                   role="presentation"
// //                   aria-hidden="true"
// //                 >
// //                   <use href="/icons.svg#bluesky-icon"></use>
// //                 </svg>
// //                 Bluesky
// //               </a>
// //             </li>
// //           </ul>
// //         </div>
// //       </section>

// //       <div className="ticks"></div>
// //       <section id="spacer"></section>
// //     </>
// //   )
// // }

// // export default App




// import { useState } from "react";
// import {
//   LiveKitRoom,
//   RoomAudioRenderer,
//   ControlBar,
// } from "@livekit/components-react";
// import "@livekit/components-styles";
// import "./App.css";

// function App() {
//   const [roomName, setRoomName] = useState("citycare-test");
//   const [token, setToken] = useState<string | null>(null);
//   const [serverUrl, setServerUrl] = useState<string | null>(null);
//   const [error, setError] = useState("");
//   const [loading, setLoading] = useState(false);

//   const backendUrl =
//     import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

//   async function joinRoom() {
//     if (!roomName.trim()) {
//       setError("Please enter a room name.");
//       return;
//     }

//     try {
//       setLoading(true);
//       setError("");

//       const response = await fetch(
//         `${backendUrl}/token?room=${encodeURIComponent(roomName.trim())}`
//       );

//       const data = await response.json();

//       if (!response.ok) {
//         throw new Error(data.detail || "Failed to get LiveKit token.");
//       }

//       setToken(data.token);
//       setServerUrl(data.url);
//     } catch (err) {
//       setError(
//         err instanceof Error
//           ? err.message
//           : "Unable to connect to the backend."
//       );
//     } finally {
//       setLoading(false);
//     }
//   }

//   function leaveRoom() {
//     setToken(null);
//     setServerUrl(null);
//     setError("");
//   }

//   if (token && serverUrl) {
//     return (
//       <main className="citycare-container">
//         <h1>CityCare Voice Assistant</h1>
//         <p>
//           Room: <strong>{roomName}</strong>
//         </p>

//         <LiveKitRoom
//           serverUrl={serverUrl}
//           token={token}
//           connect={true}
//           audio={true}
//           video={false}
//           onDisconnected={leaveRoom}
//         >
//           <div className="voice-panel">
//             <h2>You're connected</h2>
//             <p>
//               Your microphone is enabled. You can speak when the CityCare
//               agent is available in this room.
//             </p>

//             <RoomAudioRenderer />
//             <ControlBar />

//             <button
//               type="button"
//               className="leave-button"
//               onClick={leaveRoom}
//             >
//               Leave Room
//             </button>
//           </div>
//         </LiveKitRoom>
//       </main>
//     );
//   }

//   return (
//     <main className="citycare-container">
//       <h1>CityCare Voice Assistant</h1>
//       <p>Connect to the clinic voice assistant using LiveKit.</p>

//       <form
//         onSubmit={(event) => {
//           event.preventDefault();
//           void joinRoom();
//         }}
//       >
//         <label htmlFor="roomName">Room Name</label>

//         <input
//           id="roomName"
//           type="text"
//           value={roomName}
//           onChange={(event) => setRoomName(event.target.value)}
//           placeholder="Enter room name"
//         />

//         <button type="submit" disabled={loading || !roomName.trim()}>
//           {loading ? "Connecting..." : "Join Room"}
//         </button>
//       </form>

//       {error && <p className="error-message">{error}</p>}
//     </main>
//   );
// }

// export default App;



import { useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  ControlBar,
  useTranscriptions,
} from "@livekit/components-react";
import "@livekit/components-styles";
import "./App.css";

function TranscriptPanel() {
  const transcriptions = useTranscriptions();

  return (
    <section className="transcript-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">CONVERSATION</span>
          <h2>Live transcript</h2>
        </div>
        <span className="live-indicator">LIVE</span>
      </div>

      <div className="transcript-content" aria-live="polite">
        {transcriptions.length === 0 ? (
          <div className="empty-transcript">
            <div className="transcript-icon">✦</div>
            <h3>Your conversation will appear here</h3>
            <p>
              Once the agent and transcription service are active,
              your conversation will show up in real time.
            </p>
          </div>
        ) : (
          transcriptions.map((item, index) => (
            <div className="transcript-message" key={index}>
              <span className="message-dot" />
              <p>{item.text}</p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function App() {
  const [roomName, setRoomName] = useState("citycare-test");
  const [token, setToken] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const backendUrl =
    import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

  async function joinRoom() {
    if (!roomName.trim()) {
      setError("Please enter a room name.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${backendUrl}/token?room=${encodeURIComponent(roomName.trim())}`
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not get a LiveKit token.");
      }

      setToken(data.token);
      setServerUrl(data.url);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to the backend."
      );
    } finally {
      setLoading(false);
    }
  }

  function leaveRoom() {
    setToken(null);
    setServerUrl(null);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">+</span>
          <span>CityCare <strong>Clinic</strong></span>
        </a>
        <span className="topbar-label">VOICE ASSISTANT</span>
      </header>

      <main className="main-content">
        <div className="welcome">
          <span className="eyebrow">YOUR HEALTH, OUR PRIORITY</span>
          <h1>How can we help <span>you today?</span></h1>
          <p>
            Talk to the CityCare virtual assistant for help with
            clinic services and appointments.
          </p>
        </div>

        {!token || !serverUrl ? (
          <section className="connect-card">
            <div className="assistant-avatar">✚</div>
            <h2>Start a conversation</h2>
            <p>Connect securely to begin your voice session.</p>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void joinRoom();
              }}
            >
              <label htmlFor="roomName">Room name</label>
              <input
                id="roomName"
                value={roomName}
                onChange={(event) => setRoomName(event.target.value)}
                placeholder="Enter room name"
              />

              <button
                className="primary-button"
                type="submit"
                disabled={loading || !roomName.trim()}
              >
                {loading ? "Connecting..." : "Connect to assistant"}
                {!loading && <span aria-hidden="true"> →</span>}
              </button>
            </form>

            {error && <p className="error-message">{error}</p>}

            <div className="privacy-note">
              <span>●</span> Your session connects through LiveKit
            </div>
          </section>
        ) : (
          <LiveKitRoom
            serverUrl={serverUrl}
            token={token}
            connect={true}
            audio={true}
            video={false}
            onDisconnected={leaveRoom}
            onError={(err) => setError(err.message)}
          >
            <div className="session-layout">
              <section className="call-card">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">VOICE SESSION</span>
                    <h2>CityCare Assistant</h2>
                  </div>
                  <span className="connected-badge">Connected</span>
                </div>

                <div className="assistant-visual">
                  <div className="avatar-halo">
                    <div className="assistant-avatar large">✚</div>
                  </div>
                  <h3>I'm here to help</h3>
                  <p>Use your microphone to speak with the assistant.</p>
                </div>

                <div className="controls">
                  <ControlBar
                    controls={{
                      microphone: true,
                      camera: false,
                      screenShare: false,
                      chat: false,
                    }}
                  />
                </div>

                <RoomAudioRenderer />

                <button
                  className="leave-button"
                  type="button"
                  onClick={leaveRoom}
                >
                  Leave conversation
                </button>
                {error && <p className="error-message">{error}</p>}
              </section>

              <TranscriptPanel />
            </div>
          </LiveKitRoom>
        )}

        <div className="feature-row">
          <div className="feature">
            <span className="feature-icon">♡</span>
            <div><strong>Patient-focused</strong><p>Designed around your needs</p></div>
          </div>
          <div className="feature">
            <span className="feature-icon">◷</span>
            <div><strong>Available by voice</strong><p>Speak naturally</p></div>
          </div>
          <div className="feature">
            <span className="feature-icon">⌑</span>
            <div><strong>Secure connection</strong><p>Server-issued access token</p></div>
          </div>
        </div>
      </main>

      <footer className="footer">
        CityCare Clinic · Virtual assistant demo
      </footer>
    </div>
  );
}

export default App;
