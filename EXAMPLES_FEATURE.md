# Examples Feature

## Overview

The Examples feature has been added to the start page to help users get started with fubea by providing pre-defined example prompts. This feature displays up to 3 randomly selected examples from a curated list, making it easy for users to explore the capabilities of the AI agent.

## Implementation

### Components

1. **Examples Component** (`frontend/components/examples.tsx`)
   - Displays 3 randomly selected examples from a predefined list
   - Shows truncated text with ellipsis for longer examples
   - Includes visual indicators for special features (Deep Research, File Attachments)
   - Handles click events to populate the prompt and trigger actions

2. **Home Component Integration** (`frontend/components/home.tsx`)
   - Added Examples component below the QuestionInput on the start page
   - Implemented `handleExampleClick` function to process example selections
   - Handles automatic file downloading and uploading for examples with file attachments

### Features

#### Example Selection
- Randomly selects 3 examples from the predefined list on each page load
- Ensures variety and discovery of different use cases

#### Text Processing
- Automatically detects and processes special suffixes:
  - `(Deep Research)` - Enables deep research mode
  - `(file: URL)` - Downloads and attaches files from the specified URL
- Cleans the text by removing these suffixes before setting the prompt

#### Visual Indicators
- **Deep Research Badge**: Blue gradient badge indicating deep research capability
- **File Attached Badge**: Green badge indicating file attachment
- **Hover Effects**: Smooth animations and scaling on hover
- **Truncation**: Long examples are truncated with ellipsis for better UI

#### Click Functionality
When an example is clicked:
1. The prompt text is populated in the input field
2. Deep Research mode is enabled if the example includes `(Deep Research)`
3. Files are automatically downloaded and uploaded if the example includes `(file: URL)`
4. The prompt is automatically submitted after processing

### Example List

The current examples include:

1. **Research Examples**
   - Chutes AI pricing research (Deep Research)
   - Siamese cats research (Deep Research)
   - Fusion reactor research

2. **Creative Examples**
   - Presentation creation
   - 3D tic-tac-toe game development
   - Thank you letter writing

3. **Practical Examples**
   - Calendar app design with file attachment
   - Travel planning with interactive map

4. **Complex Examples**
   - Multi-modal outputs with reports and interactive elements

### Styling

The Examples component follows the existing design system:
- Glass morphism effects with backdrop blur
- Gradient borders and hover effects
- Consistent spacing and typography
- Responsive grid layout (1 column on mobile, 3 columns on desktop)
- Smooth animations using Framer Motion

### Technical Details

#### File Handling
- Automatically downloads files from URLs specified in examples
- Creates File objects and simulates file upload events
- Integrates with existing file upload infrastructure
- Handles errors gracefully with toast notifications

#### State Management
- Uses React hooks for local state management
- Integrates with existing Home component state
- Maintains consistency with current question and deep research settings

#### Performance
- Lightweight component with minimal re-renders
- Efficient random selection algorithm
- Lazy loading of file downloads only when needed

## Usage

Users can:
1. View 3 random examples on the start page
2. Click any example to automatically populate and submit the prompt
3. See visual indicators for special features
4. Experience automatic file attachment for relevant examples

The feature enhances user onboarding and discovery by providing concrete examples of the AI agent's capabilities. 