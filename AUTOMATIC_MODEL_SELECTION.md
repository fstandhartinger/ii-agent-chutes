# Automatic Model Selection

This document describes the automatic model selection feature that intelligently chooses the optimal Chutes model based on the content of your conversation.

## Overview

The system automatically switches between text-optimized and vision-capable models based on whether images are present in the conversation context. This ensures optimal performance and cost-efficiency while providing the best user experience.

## Model Categories

### Text Models (No Images)
When no images are detected in the conversation, the system uses text-optimized models:

- **Primary**: DeepSeek R1 - Reasoning-optimized model for complex text tasks
- **Fallback**: Qwen3 235B - Large-scale reasoning model

### Vision Models (Images Present)
When images are detected (uploaded files or pasted images), the system automatically switches to vision-capable models:

- **Primary**: DeepSeek V3 0324 - Advanced reasoning model with vision capabilities
- **Fallback**: Llama Maverick 4 - Efficient instruction-following model with vision

## Image Detection

The system detects images in the following scenarios:

1. **File Uploads**: When you upload files with image extensions (jpg, jpeg, png, gif, webp, bmp, heic, svg)
2. **Clipboard Paste**: When you paste images directly into the chat (Ctrl+V)
3. **Message History**: Checks recent messages for image attachments

## How It Works

### Frontend Detection
- Monitors uploaded files and message history for image content
- Calculates optimal model based on current context
- Updates WebSocket connection with appropriate model selection
- Provides visual indicators showing which model is being used

### Backend Processing
- Chutes client automatically handles vision model capabilities
- Converts image blocks to OpenAI vision format for compatible models
- Falls back gracefully for non-vision models

## Visual Indicators

### Model Selector (Home Page)
Shows the automatic model selection with two categories:
- **Text Tasks**: Blue icon with text models listed
- **Vision Tasks**: Purple icon with vision models listed

### Question Input (Chat Interface)
Displays current model selection at the bottom of the input box:
- **Blue icon + model name**: Text model active (no images)
- **Purple icon + model name**: Vision model active (images detected)

## Technical Implementation

### Frontend Components
- `providers/chutes-provider.tsx`: Model configuration and selection logic
- `components/home.tsx`: Image detection and WebSocket connection
- `components/model-selector.tsx`: Visual model display
- `components/question-input.tsx`: Real-time model indicator

### Backend Components
- `src/ii_agent/llm/chutes_openai.py`: Vision model support and image handling
- `ws_server.py`: Model parameter processing from WebSocket connection

## Configuration

### Model Definitions
```typescript
// Text-only models
export const TEXT_MODELS: LLMModel[] = [
  {
    id: "deepseek-ai/DeepSeek-R1",
    name: "DeepSeek R1",
    provider: "chutes",
    description: "Reasoning-optimized model",
    supportsVision: false
  },
  // ...
];

// Vision-capable models
export const VISION_MODELS: LLMModel[] = [
  {
    id: "deepseek-ai/DeepSeek-V3-0324",
    name: "DeepSeek V3 0324",
    provider: "chutes",
    description: "Advanced reasoning model with vision",
    supportsVision: true
  },
  // ...
];
```

### Automatic Selection Logic
```typescript
const getOptimalModel = (hasImages: boolean): LLMModel => {
  if (hasImages) {
    return VISION_MODELS[0]; // DeepSeek V3 0324 as primary
  } else {
    return TEXT_MODELS[0]; // DeepSeek R1 as primary
  }
};
```

## Benefits

1. **Optimal Performance**: Uses the best model for each task type
2. **Cost Efficiency**: Avoids using expensive vision models for text-only tasks
3. **Seamless Experience**: Automatic switching without user intervention
4. **Visual Feedback**: Clear indicators of which model is being used
5. **Fallback Support**: Graceful degradation if primary models are unavailable

## Usage Examples

### Text-Only Conversation
```
User: "Explain quantum computing"
System: Uses DeepSeek R1 (text model)
```

### Image Analysis
```
User: [uploads image] "What's in this picture?"
System: Automatically switches to DeepSeek V3 0324 (vision model)
```

### Mixed Conversation
```
User: "Analyze this chart" [uploads image]
System: Uses DeepSeek V3 0324 (vision model)
User: "Now explain the implications"
System: Continues with DeepSeek V3 0324 (maintains vision context)
```

## Troubleshooting

### Model Not Switching
- Check that images are properly uploaded/pasted
- Verify file extensions are supported
- Look for console logs showing model selection

### Vision Model Issues
- Ensure CHUTES_API_KEY is properly configured
- Check that vision models are available in your Chutes account
- Review backend logs for vision model initialization

### Performance Issues
- Monitor token usage between text and vision models
- Consider conversation length and image count
- Check fallback model availability

## Future Enhancements

- Dynamic model selection based on task complexity
- User preferences for model selection
- Cost optimization based on usage patterns
- Support for additional vision model providers 