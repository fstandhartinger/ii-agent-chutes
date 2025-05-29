# Frontend App Terms of Service Page Directory Summary (`frontend/app/terms/`)

This directory contains the page component for the Terms of Service of the fubea application.

## File Descriptions:

*   **`page.tsx`**: This is a React component that renders the static content for the `/terms` route.
    *   **Purpose**: Outlines the legal terms and conditions that users must agree to when accessing or using the fubea service.
    *   **Content**:
        *   Sets specific metadata for the page (title and description).
        *   Includes a "Last updated" date, dynamically set to the current date.
        *   **Key Terms**:
            *   **Acceptance**: Use of the service implies acceptance of these terms, the Privacy Policy, and the terms of third-party providers (Render.com, Chutes.ai).
            *   **Service Description & Data Processing**: Describes fubea as an AI research platform. Critically, it includes a notice that user data will be transmitted to and processed by third-party AI services, and users must consent to this.
            *   **User Obligations**: Users must use the service at their own risk, avoid misuse, not submit sensitive information, and comply with laws.
            *   **Intellectual Property**: Rights to the service remain with the operating company.
            *   **Disclaimers**: The service is provided "as is" with no warranties. Liability is limited for damages, data loss, and service interruptions.
            *   **Indemnification**: Users must indemnify fubea.
            *   **Service Modifications**: fubea reserves the right to change the service or terms. No uptime is guaranteed.
            *   **AI Regulation**: States commitment to comply with AI regulations like the EU AI Act.
            *   **Governing Law**: German law applies.
            *   **Contact**: Provides an email for inquiries.
    *   **Styling**: The page is styled using Tailwind CSS, featuring a dark theme, a "glassmorphism" effect for the content card, and Tailwind Typography (`prose prose-invert`) for readability.
    *   **Navigation**: A link is provided to navigate back to the fubea homepage.

## Role of the Directory:

The `frontend/app/terms/` directory and its `page.tsx` file are responsible for presenting the legal agreement governing the use of the fubea website and its services. It is essential for setting expectations, defining responsibilities, and outlining the legal framework for both the users and the service provider.
