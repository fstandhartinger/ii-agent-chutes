import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();

    if (!message) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    // Use CHUTES API to generate a short summary - using CHUTES_API_KEY to match backend convention
    const apiToken = process.env.CHUTES_API_KEY;
    
    if (!apiToken) {
      return NextResponse.json({ summary: "Task in progress" });
    }

    const response = await fetch('https://chutes-gpt-4o-mini.chutes.ai/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'You are a helpful assistant that creates very short task summaries. Create a summary of the user\'s request in maximum 5 words. Be concise and capture the main action or goal.'
          },
          {
            role: 'user',
            content: `Summarize this task in maximum 5 words: ${message}`
          }
        ],
        max_tokens: 20,
        temperature: 0.3,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      const summary = data.choices?.[0]?.message?.content?.trim() || "Task in progress";
      return NextResponse.json({ summary });
    } else {
      return NextResponse.json({ summary: "Task in progress" });
    }
  } catch (error) {
    console.error('Error generating summary:', error);
    return NextResponse.json({ summary: "Task in progress" });
  }
} 