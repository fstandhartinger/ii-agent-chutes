import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { message, modelId } = await request.json();

    if (!message || !modelId) {
      return NextResponse.json(
        { error: 'Message and modelId are required' },
        { status: 400 }
      );
    }

    const apiKey = process.env.CHUTES_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: 'CHUTES_API_KEY not configured' },
        { status: 500 }
      );
    }

    // Call Chutes API with the selected model
    const response = await fetch(`https://api.chutes.ai/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: modelId,
        messages: [
          {
            role: 'system',
            content: 'You are a helpful assistant that creates very short, concise summaries of user tasks. Your summaries should be 3-7 words maximum, capturing the essence of what the user wants to do. Be specific but brief.'
          },
          {
            role: 'user',
            content: `Create a very short summary (3-7 words) of this task: "${message}"`
          }
        ],
        response_format: { type: 'json_object' },
        temperature: 0.3,
        max_tokens: 50,
      }),
    });

    if (!response.ok) {
      const errorData = await response.text();
      console.error('Chutes API error:', errorData);
      return NextResponse.json(
        { error: 'Failed to generate summary' },
        { status: response.status }
      );
    }

    const data = await response.json();
    const content = data.choices[0]?.message?.content;
    
    let summary = 'Task in progress';
    try {
      const parsed = JSON.parse(content);
      summary = parsed.summary || 'Task in progress';
    } catch (e) {
      console.error('Failed to parse JSON response:', e);
    }

    return NextResponse.json({ summary });
  } catch (error) {
    console.error('Error generating summary:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
} 