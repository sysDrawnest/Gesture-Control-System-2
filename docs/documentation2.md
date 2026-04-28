# GESTURE CONTROL SYSTEM - PROJECT REPORT

---

## 1. PRELIMINARY PAGES

### 1.1 TITLE PAGE

**PROJECT TITLE:** GESTURE CONTROL SYSTEM: A COMPUTER VISION BASED APPROACH TO HUMAN-COMPUTER INTERACTION

**DOMAIN:** Artificial Intelligence / Computer Vision / Machine Learning

**DEVELOPED BY:** Sanjib

**UNDER THE GUIDANCE OF:** [Internal Guide Name Placeholder]

**INSTITUTION:** [University/College Name Placeholder]

**SESSION:** 2023 - 2026

**A Project Report submitted in partial fulfillment of the requirements for the degree of Bachelor of Computer Applications (BCA) / Master of Computer Applications (MCA).**

---

### 1.2 DECLARATION

I, **Sanjib**, hereby declare that the project titled **"Gesture Control System"** is a record of the original work done by me under the guidance of **[Guide Name]**, Department of Information Technology, **[Institution Name]**. This report has not been submitted elsewhere for the award of any other degree or diploma.

**Date:** April 28, 2026  
**Place:** [Place]  
**Signature of Candidate:** ______________

---

### 1.3 ACKNOWLEDGEMENT

I would like to express my deepest gratitude to my project guide, **[Guide Name]**, for their constant guidance, encouragement, and invaluable suggestions throughout the development of this project. Their insights into Computer Vision and Software Engineering have been instrumental in the successful completion of this work.

I am also thankful to **[HOD Name]**, Head of the Department, for providing the necessary facilities and a conducive environment for research and development.

Finally, I would like to thank my peers and family for their unwavering support and motivation during the challenging phases of this project.

**Sanjib**

---

### 1.4 CERTIFICATE

This is to certify that the project entitled **"Gesture Control System"** is a bonafide work carried out by **Sanjib** in partial fulfillment of the requirements for the award of the degree of [Degree Name] by [University Name].

The results embodied in this report have been verified and found to be satisfactory.

**Internal Guide** | **External Examiner** | **Head of Department**

---

### 1.5 ABSTRACT

The **Gesture Control System** is an advanced Human-Computer Interaction (HCI) platform designed to eliminate the reliance on physical hardware peripherals such as the mouse and keyboard for basic navigation. Utilizing state-of-the-art Computer Vision algorithms provided by **MediaPipe** and **OpenCV**, the system captures real-time video feed via a standard webcam to detect and interpret hand landmarks.

The project implements a cross-platform client-server architecture. The **Client** utilizes the MediaPipe Hand Landmarker task to track 21 specific 3D landmarks on the human hand with high precision. These landmarks are then translated into specific system-level actions, including cursor movement (POINT gesture), left-clicking (PINCH gesture), right-clicking (PEACE gesture), and scrolling (THREE-FINGERS gesture).

Integration with a **Flask-based Server** allows for centralized session management, JWT-based authentication, and real-time data logging via WebSockets. This architectural choice enhances the system's scalability, allowing it to be used in remote control scenarios or as an assistive technology for individuals with motor impairments.

The system demonstrates significant improvements in interaction speed and user experience over traditional gesture recognition attempts by employing a sophisticated cursor smoothing algorithm (Weighted Moving Average) that reduces jitter and enhances precision. The final outcome is a robust, low-latency, and intuitive interface that paves the way for the next generation of touchless computing.

---

## 2. INDEX

1. **Chapter 1: Introduction** ...................................................... Page 5
   1.1 Introduction
   1.2 Aim
   1.3 Objectives
   1.4 Goal
2. **Chapter 2: Existing System & Limitations** ...................................... Page 12
   2.1 Existing System Review
   2.2 Problem Statement
3. **Chapter 3: Proposed System Analysis** ............................................ Page 18
   3.1 Key Features
   3.2 Proposed Methodology
4. **Chapter 4: System Design** ....................................................... Page 25
   4.1 Architecture Overview
   4.2 Key Workflows
   4.3 Database Schema
   4.4 UML Diagrams Description
   4.5 User Journey
   4.6 Schema Design
5. **Chapter 5: Implementation** ..................................................... Page 38
   5.1 Development Approach
   5.2 Technologies Used
   5.3 Deployment
6. **Chapter 6: Testing** ............................................................ Page 45
   6.1 Testing Strategy
   6.2 Types of Tests
   6.3 Example Test Cases
7. **Chapter 7: Screenshots Description** ............................................ Page 52
8. **Chapter 8: Conclusion** ......................................................... Page 58
   8.1 Summary
   8.2 Future Scope
9. **Bibliography** ................................................................. Page 62

---

## 3. CHAPTER 1: INTRODUCTION

### 3.1 INTRODUCTION

In the contemporary digital era, the interaction between humans and computers has undergone a paradigm shift. From the early days of punch cards and command-line interfaces to the revolutionary mouse-driven graphical user interface (GUI) of the 1980s, the goal has always been to make machines more accessible. However, despite the ubiquity of touchscreens, the primary mode of interaction with desktop environments remains the physical mouse—a device that has changed little in over three decades.

The **Gesture Control System** represents a leap toward "Natural User Interfaces" (NUI). By leveraging the innate human ability to communicate through hand gestures, this project seeks to bridge the physical-digital gap. It is inspired by the vision of "Ubiquitous Computing," where the environment itself responds to human presence and intent without the need for cumbersome handheld gear.

The importance of this system is particularly evident in three contexts:
1. **Ergonomics**: Reducing Repetitive Strain Injury (RSI) caused by prolonged mouse usage.
2. **Hygiene**: Providing touchless interaction in sterile environments like hospitals and laboratories.
3. **Accessibility**: Enabling individuals with limited manual dexterity or physical disabilities to navigate computing environments with ease.

### 3.2 AIM

The primary aim of this project is to develop a high-performance, real-time gesture recognition system that can accurately map complex hand movements to system-level commands, thereby providing a seamless touchless computing experience using standard consumer-grade hardware.

### 3.3 OBJECTIVES

To achieve the stated aim, the following objectives have been identified:
- **Hand Tracking Core**: Implementation of a robust landmark detection system capable of tracking 21 key points on the hand in real-time.
- **Gesture Mapping**: Developing a logic layer that classifies specific landmark configurations into actionable commands (Point, Click, Scroll, Zoom).
- **Network Synchronization**: Creating a secure WebSocket-based communication channel between the client and a centralized server for device registration and logging.
- **Precision Engineering**: Implementing advanced signal processing techniques (Moving Averages) to translate raw pixel data into smooth, jitter-free cursor movements.
- **Security & Analytics**: Integrating JWT-based authentication for secure access and a database backend to track gesture efficiency and system usage.

### 3.4 GOAL

The final goal is the delivery of a production-ready software suite comprising a Python-based desktop client and a Flask-based web server. The system should allow any user with a standard webcam to control their computer with an accuracy of over 95% in stable lighting conditions, with a latency of less than 30ms, facilitating an intuitive "Minority Report" style interaction.

---
