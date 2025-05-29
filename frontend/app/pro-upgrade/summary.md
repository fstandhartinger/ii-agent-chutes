# Frontend App Pro Upgrade Page Directory Summary (`frontend/app/pro-upgrade/`)

This directory contains the page component for users to upgrade to a "Pro" subscription plan for the fubea application.

## File Descriptions:

*   **`page.tsx`**: This is a client-side React component (`"use client"`) that renders the `/pro-upgrade` route.
    *   **Purpose**: To present the benefits of a Pro subscription, primarily access to the Claude Sonnet 4 AI model, and to facilitate the upgrade process through a Stripe payment link.
    *   **Key Features**:
        *   **Visual Appeal**: Uses a dark, gradient background with animated decorative blurs and `framer-motion` for smooth animations on UI elements.
        *   **Hero Section**: Prominently displays "Upgrade to Pro" with icons (Crown, Sparkles) and highlights access to "Claude Sonnet 4".
        *   **Benefits of Claude Sonnet 4**: Lists advantages such as being "Lightning Fast," having "Superior Intelligence," and "Enhanced Performance," each with an associated icon.
        *   **Pricing Display**: Clearly shows the subscription cost as "$20/month".
        *   **Call to Action**: A "Subscribe Now" button initiates the upgrade process.
        *   **Stripe Integration**: Clicking the subscribe button opens a predefined Stripe payment link (`https://buy.stripe.com/5kQ00ibzwencbx09wk1Jm00`) in a new browser tab.
        *   **Informational Modal**: After initiating the payment, a modal window appears.
            *   It confirms that the payment process has started via Stripe.
            *   Informs the user that they will receive an email with an access link for Pro mode.
            *   Humorously notes that the email delivery might be delayed as it's a manual process by the founder, Florian, at the moment.
        *   **"Why Upgrade?" Section**: Provides a rationale for the Pro plan, emphasizing the advanced capabilities and higher costs associated with Claude Sonnet 4.
        *   **Navigation**: Includes a "Back" button to return to the previous page.
    *   **Styling**: Uses Tailwind CSS for styling, with custom "glass" effects and gradient backgrounds.

## Role of the Directory:

The `frontend/app/pro-upgrade/` directory and its `page.tsx` file serve as a dedicated sales and upgrade page. It aims to convert free users to paying Pro subscribers by showcasing the premium features offered and providing a clear path to subscription via Stripe.
