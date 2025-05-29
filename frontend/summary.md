# Frontend Directory Summary

This directory contains the root files for the II Agent Frontend application.

## File Descriptions:

*   **`package.json`**: Defines the project's metadata, scripts (e.g., `dev`, `build`, `start`, `lint`), and its dependencies (e.g., Next.js, React, Tailwind CSS, Monaco Editor, Xterm.js) and development dependencies (e.g., ESLint, TypeScript). It's the entry point for managing project packages and running common development and build tasks.
*   **`next.config.ts`**: Configures Next.js specific settings. In this case, it's set to `output: "standalone"`, which prepares the application for deployment as a standalone server, minimizing dependencies on the build environment.
*   **`postcss.config.mjs`**: Configures PostCSS, a tool for transforming CSS with JavaScript plugins. Here, it's set up to use the `@tailwindcss/postcss` plugin, enabling Tailwind CSS processing.
*   **`tsconfig.json`**: The TypeScript configuration file. It specifies compiler options for the project, such as the target ECMAScript version, JavaScript library files to include, module system, strictness, path aliases (like `@/*` pointing to the root), and which files TypeScript should include or exclude during compilation.
*   **`eslint.config.mjs`**: Configures ESLint, a static code analysis tool for identifying problematic patterns found in JavaScript/TypeScript code. It extends Next.js's core web vitals and TypeScript linting rules and includes custom rule configurations, such as warning on unused variables and allowing `ts-comment`.
*   **`components.json`**: Configuration file for `shadcn/ui`, a UI component library. It defines the visual style (`new-york`), whether React Server Components (RSC) are used, Tailwind CSS integration details (like the path to `globals.css` and base color), path aliases for project directories (e.g., `@/components`, `@/lib/utils`), and the icon library used (Lucide).
*   **`Dockerfile`**: Defines the instructions for building a Docker image for the frontend application. It uses a multi-stage build process:
    *   A `base` stage with Node.js 18 on Alpine Linux.
    *   A `deps` stage to install dependencies.
    *   A `builder` stage to build the Next.js application.
    *   A `runner` stage for the production environment, copying only necessary built artifacts and running the Next.js standalone server. This optimizes the final image size and security.
*   **`index.html`**: A standalone HTML page that implements a WebSocket client interface, likely for testing or direct interaction with the "fubea" WebSocket backend. It includes HTML structure, embedded CSS for styling, and JavaScript for managing the WebSocket connection, sending/receiving messages, and updating the UI. This file appears to be separate from the main Next.js application.
*   **`README.md`**: Provides comprehensive documentation for the II Agent Frontend. It covers an introduction to the project, prerequisites, installation instructions, development and production workflows, project structure, key components, technologies used, and details about WebSocket integration for real-time communication with the backend.

## Role of the Directory:

The `frontend/` directory serves as the root of the user-facing part of the II Agent application. It contains all necessary configuration files for building, linting, and running the Next.js web application, as well as documentation and a Dockerfile for containerization. The `index.html` file provides an auxiliary WebSocket testing interface.
