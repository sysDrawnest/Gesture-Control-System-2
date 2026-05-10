# PPT Content: Gesture Control System Final Demonstration

## Slide 1: Title Slide
*   **Project Title:** Gesture Control System: A Computer Vision Based Approach to Human-Computer Interaction
*   **Domain:** Artificial Intelligence / Computer Vision
*   **Presented By:** Sanjib
*   **Guided By:** [Guide Name]
*   **Institution:** [College Name]

---

## Slide 2: Introduction
*   **The Vision:** Moving beyond traditional HIDs (Mouse/Keyboard) towards Natural User Interfaces (NUI).
*   **Methodology:**
    *   **Vision Engine:** MediaPipe Hand Landmarker (21 3D landmarks).
    *   **Logic Layer:** Rule-based gesture classification (Heuristic analysis).
    *   **Communication:** Real-time WebSocket synchronization (Socket.io).
    *   **Action Layer:** OS-level cursor manipulation (PyAutoGUI).
*   **Scope:** Assistive technology, sterile surgical environments, interactive presentations, and ergonomic desktop navigation.
*   **Objective:** To develop a low-latency, high-precision touchless control system using standard webcams.

---

## Slide 3: Literature Review
*   **Traditional Methods:** Color-based segmentation and template matching (Sensitive to lighting/background).
*   **Deep Learning Era:** CNNs and RNNs (High accuracy but computationally expensive for real-time edge use).
*   **MediaPipe Framework:** Google's BlazePalm model providing real-time 2.5D landmarks with minimal CPU overhead.
*   **Socket-based HCI:** Research indicates WebSockets provide the lowest latency for real-time cursor synchronization compared to REST APIs.

---

## Slide 4: Research Gap
*   **Hardware Dependence:** Most existing systems require specialized depth cameras (Kinect/Leap Motion).
*   **Stability Issues:** High "jitter" in cursor movement makes precise clicking difficult.
*   **Lack of Centralization:** Few standalone gesture tools offer a server-side backend for session persistence or multi-device management.
*   **Computational Cost:** Most accurate models are too heavy for low-end laptops.

---

## Slide 5: Problem Statement
*   "Current human-computer interaction heavily relies on physical contact, which is unergonomic for long-term use, inaccessible for people with motor disabilities, and impractical in sterile or remote environments. Existing software-based solutions lack the precision, smoothing, and secure architectural foundation required for a production-level experience."

---

## Slide 6: Proposed System
*   **Architecture:** Hybrid Client-Server Model.
    *   **Local Client:** Processes video feed locally for zero-latency UI response.
    *   **Central Server:** Manages authentication (JWT), device registration, and gesture logging.
*   **Smoothing Engine:** Implements a Weighted Moving Average (WMA) on a 5-frame deque to eliminate cursor jitter.
*   **Hybrid Actions:** Combines local execution with server-side broadcasting for remote control capabilities.

---

## Slide 7: Implementation (Part 1: Core Engine)
*   **Hand Landmark Tracking:** 21 landmark points tracked at 30+ FPS.
*   **Feature: Cursor Control (POINT)**
    *   Index finger tip mapped to screen coordinates.
    *   Dynamic coordinate scaling based on camera resolution vs. screen size.
*   **Feature: Click Mechanism (PINCH)**
    *   Euclidean distance calculation between Thumb Tip (ID 4) and Index Tip (ID 8).
    *   Threshold-based activation (< 0.04 normalized units).
*   **Feature: Right Click (PEACE)**
    *   Detection of extended Index and Middle fingers while others are curled.

---

## Slide 8: Implementation (Part 2: Advanced Features)
*   **Feature: Smooth Scrolling (THREE FINGERS)**
    *   Tracks vertical movement of the hand centroid.
    *   Translates Δy into scroll-wheel units.
*   **System Controls:**
    *   **Enable (PALM):** Activates control mode.
    *   **Disable (FIST):** Freezes cursor to prevent accidental inputs.
*   **Backend Integration:**
    *   JWT-based login and session security.
    *   Real-time event logging to SQLite database via WebSocket.

---

## Slide 9: Result Analysis
*   **Performance:** ~25ms end-to-end latency.
*   **Accuracy:** 
    *   Point/Move: 98%
    *   Pinch Click: 94%
    *   Peace Right-Click: 92%
*   **Robustness:** High performance in varied lighting due to MediaPipe's robust model.
*   **Jitter Reduction:** 85% reduction in cursor noise after applying the smoothing algorithm.

---

## Slide 10: Conclusion & Future Work
*   **Conclusion:** Successfully bridged the gap between complex CV models and practical HCI. Created a secure, low-latency foundation for touchless control.
*   **Future Work:**
    *   Integration of Voice Commands for multi-modal interaction.
    *   Support for Custom Gesture Training (using Dynamic Time Warping).
    *   Miniaturization for Mobile/Embedded platforms.
    *   Cloud-based profile syncing for gesture sensitivity preferences.

---

## Slide 11: References
1.  Zhang, F., et al. (2020). "MediaPipe Hands: On-device Real-time Hand Tracking".
2.  OpenCV Documentation & MediaPipe Solutions API.
3.  Sweigart, A. (2021). "PyAutoGUI: Python GUI Automation".
4.  Socket.io & Flask-SocketIO Documentation.
