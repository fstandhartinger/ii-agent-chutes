import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { message, modelId } = await request.json();

    if (!message) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    // Use CHUTES API to generate a short summary - using CHUTES_API_KEY to match backend convention
    const apiToken = process.env.CHUTES_API_KEY;
    
    if (!apiToken) {
      return NextResponse.json({ summary: "Task in progress" });
    }

    // Use the provided model ID or default to DeepSeek R1
    const model = modelId || 'deepseek-ai/DeepSeek-R1';

    const response = await fetch('https://llm.chutes.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model,
        messages: [
          {
            role: 'system',
            content: 'You are a helpful assistant that creates very short task summaries. You must respond with a JSON object containing a "summary" field with a concise summary of the user\'s request in 3-7 words maximum. Be precise and capture the main action or goal.'
          },
          {
            role: 'user',
            content: `Create a short summary for this task: ${message}`
          }
        ],
        max_tokens: 50,
        temperature: 0.1,
        response_format: { type: "json_object" }
      }),
    });

    if (response.ok) {
      const data = await response.json();
      const content = data.choices?.[0]?.message?.content?.trim();
      
      if (content) {
        try {
          // Parse the JSON response
          const jsonResponse = JSON.parse(content);
          const summary = jsonResponse.summary || "Task in progress";
          return NextResponse.json({ summary });
        } catch (parseError) {
          console.error('Error parsing JSON response:', parseError);
          // Fallback: try to extract summary from content
          const summary = content.length > 50 ? content.substring(0, 47) + "..." : content;
          return NextResponse.json({ summary });
        }
      } else {
        return NextResponse.json({ summary: "Task in progress" });
      }
    } else {
      console.error('Chutes API error:', response.status, response.statusText);
      return NextResponse.json({ summary: "Task in progress" });
    }
  } catch (error) {
    console.error('Error generating summary:', error);
    return NextResponse.json({ summary: "Task in progress" });
  }
} 