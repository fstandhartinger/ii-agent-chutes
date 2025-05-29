# Frontend App Imprint Page Directory Summary (`frontend/app/imprint/`)

This directory contains the page component for the Legal Notice (Imprint) of the fubea application.

## File Descriptions:

*   **`page.tsx`**: This is a React component that renders the static content for the `/imprint` route.
    *   **Purpose**: Displays legally required information about the website operator, in accordance with German law (§ 5 TMG - Telemediengesetz).
    *   **Content**:
        *   Sets specific metadata for the page (title and description).
        *   Provides details of the company: "productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG," including its address in Passau, Germany.
        *   Names Florian Standhartinger as the representative.
        *   Lists contact information: phone, fax, and an email address (florian.standhartinger@gmail.com).
        *   Includes Commercial Register details (Amtsgericht Passau, HRB 8453).
        *   States the VAT identification number (DE296812612).
        *   Contains a copyright notice.
    *   **Styling**: The page is styled using Tailwind CSS, featuring a dark theme, a "glassmorphism" effect for the content card, and uses Tailwind Typography (`prose prose-invert`) for readable text formatting.
    *   **Navigation**: A link is provided to navigate back to the fubea homepage.

## Role of the Directory:

The `frontend/app/imprint/` directory and its `page.tsx` file are responsible for presenting the legal notice/imprint of the fubea website. This is a standard requirement for websites, particularly those operated by entities in Germany, to ensure transparency and provide contact and registration details of the responsible party.
