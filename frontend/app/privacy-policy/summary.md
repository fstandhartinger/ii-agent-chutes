# Frontend App Privacy Policy Page Directory Summary (`frontend/app/privacy-policy/`)

This directory contains the page component for the Privacy Policy of the fubea application.

## File Descriptions:

*   **`page.tsx`**: This is a React component that renders the static content for the `/privacy-policy` route.
    *   **Purpose**: Informs users about how their personal information and submitted data are collected, used, and protected when using the fubea service.
    *   **Content**:
        *   Sets specific metadata for the page (title and description).
        *   Includes a "Last updated" date, which is dynamically set to the current date.
        *   **Key Policy Points**:
            *   **Information Collected**: Research queries, uploaded files (processed temporarily, not stored), usage data, device/session information (local), and service metrics.
            *   **Data Usage**: Data is processed temporarily for analysis, not stored permanently, and deleted after processing. It's shared with third-party AI services (like those accessed via Chutes.ai and Render.com) as necessary.
            *   **Cookies**: Used for session management, preferences, and essential functionality.
            *   **Data Security**: Mentions security measures but advises against submitting sensitive information.
            *   **Third-Party Services**: Identifies Render.com for hosting and Chutes.ai for AI processing.
            *   **AI Processing Warning**: Explicitly states that data will be processed by third-party AI services and users uncomfortable with this should not use the application.
            *   **Disclaimer**: Standard liability disclaimer.
            *   **EU AI Act**: Commits to compliance with relevant AI regulations.
            *   **Policy Changes**: Reserves the right to update the policy.
            *   **Contact**: Provides an email for privacy inquiries.
    *   **Styling**: The page uses Tailwind CSS, featuring a dark theme, a "glassmorphism" effect for the content card, and Tailwind Typography (`prose prose-invert`) for clear presentation of the policy text.
    *   **Navigation**: A link is provided to navigate back to the fubea homepage.

## Role of the Directory:

The `frontend/app/privacy-policy/` directory and its `page.tsx` file are responsible for presenting the fubea website's privacy policy. This is crucial for transparency with users regarding data handling practices, especially given the nature of an AI research service that processes user-submitted data.
