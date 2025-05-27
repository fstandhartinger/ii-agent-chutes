# fubea - Free AI Agent with Enhanced UI

fubea is an advanced AI agent based on the powerful [ii-agent](https://github.com/Intelligent-Internet/ii-agent) framework. It leverages free LLM inference from [Chutes.ai](https://chutes.ai) to provide a sophisticated AI assistant with improved functionality and user interface.

## Features

- **Free LLM Inference**: Powered by Chutes.ai's free API, providing access to state-of-the-art language models
- **Enhanced User Interface**: Modern, responsive design with improved user experience
- **Deep Research Capabilities**: Advanced research mode for comprehensive analysis
- **Multi-Modal Support**: Handle text, code, images, and more
- **Real-Time Interaction**: WebSocket-based communication for instant responses
- **Tool Integration**: Built-in browser, code editor, terminal, and more

## Based on ii-agent

fubea builds upon the excellent [ii-agent](https://github.com/Intelligent-Internet/ii-agent) project, which achieved leading performance on the GAIA benchmark. We are grateful for their open-source contribution and have enhanced it with:

- Integration with Chutes.ai for free LLM access
- Improved user interface and experience
- Additional features and optimizations

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/fstandhartinger/ii-agent-chutes.git
cd ii-agent-chutes
```

2. Install Python dependencies:
```bash
pip install -e .
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
```

4. Set up environment variables:
```bash
cp env.example .env
# Edit .env and add your CHUTES_API_KEY
```

### Running fubea

1. Start the backend server:
```bash
python ws_server.py
```

2. In a new terminal, start the frontend:
```bash
cd frontend
npm run dev
```

3. Open your browser and navigate to `http://localhost:3000`

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ii-agent](https://github.com/Intelligent-Internet/ii-agent) - The foundation of this project
- [Chutes.ai](https://chutes.ai) - For providing free LLM inference
- All contributors and users of fubea

